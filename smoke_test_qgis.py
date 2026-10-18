"""Run inside the QGIS Python console: run(iface)."""
from .schema import field_name
from qgis.core import (QgsVectorLayer, QgsField, QgsFeature, QgsGeometry,
                      QgsPointXY, QgsExpression, QgsExpressionContext,
                      QgsExpressionContextUtils)
from .plugin import PhotoPlugin, PhotoTool, FIELDS, EXPRESSION
from .photo_dialog import PhotoDialog
from qgis.PyQt.QtWidgets import QDialog
from .photo_preview import PreviewDialog
from qgis.PyQt.QtGui import QImage
from pathlib import Path
import tempfile


def run(iface):
    with tempfile.TemporaryDirectory() as directory:
        image_path = Path(directory) / 'immagine con spazi.jpg'
        image = QImage(80, 40, QImage.Format_RGB32)
        image.fill(0xffffff)
        assert image.save(str(image_path), 'JPG')
        preview = PreviewDialog(iface.mainWindow(), 'TEST', str(image_path), '', '')
        assert preview.pixmap is not None
        assert preview.open_button.isEnabled() and preview.folder_button.isEnabled()
        preview.close()
        missing = PreviewDialog(iface.mainWindow(), 'TEST', str(Path(directory)/'manca.jpg'), '', '')
        assert missing.pixmap is None and not missing.open_button.isEnabled()
        assert missing.folder_button.isEnabled()
        missing.close()
    dialog = PhotoDialog(iface.mainWindow(), 'F002', {'F001'})
    dialog.code_edit.setText('F001')
    dialog.photo_edit.setText('/tmp/foto con spazi.jpg')
    dialog.accept()
    assert dialog.result() != QDialog.Accepted
    assert dialog.photo_edit.text() == '/tmp/foto con spazi.jpg'
    dialog.code_edit.setText(' F002 ')
    dialog.accept()
    assert dialog.result() == QDialog.Accepted
    assert dialog.values() == ('F002', '/tmp/foto con spazi.jpg')
    layer = QgsVectorLayer('Point?crs=EPSG:32632', 'test non persistente', 'memory')
    assert layer.isValid()
    assert not layer.readOnly()
    assert layer.dataProvider().addAttributes([QgsField(n, t) for n, t in FIELDS.items()])
    layer.updateFields()
    PhotoPlugin(iface).style(layer)
    assert layer.labelsEnabled()
    assert layer.labeling().settings().fieldName == 'code'
    assert layer.renderer().symbol().symbolLayerCount() == 2
    f = QgsFeature(layer.fields())
    f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(500000, 5000000)))
    for name, value in [('code', 'F001'), ('azimuth', 90.0), ('fov', 60.0), ('distance', 25.0)]:
        f[name] = value
    assert layer.startEditing()
    tool = PhotoTool(PhotoPlugin(iface), layer, False)
    try:
        tool.hint()
        tool.state = {'origin': (500000, 5000000), 'azimuth': 90.0, 'fov': 60.0, 'distance': 25.0}
        tool.save_new('FOTO_TEST', '/tmp/foto con spazi.jpg')
        saved = next(f for f in layer.getFeatures() if f[field_name(f, 'code')] == 'FOTO_TEST')
        assert saved['photo'] == '/tmp/foto con spazi.jpg'
        layer.undoStack().undo()
        assert layer.featureCount() == 1
    finally:
        tool.dispose()
        iface.statusBarIface().clearMessage()
    layer.beginEditCommand('Test inserimento')
    assert layer.addFeature(f)
    layer.endEditCommand()
    assert layer.featureCount() == 1
    context = QgsExpressionContext()
    context.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(layer))
    context.setFeature(next(layer.getFeatures()))
    expression = QgsExpression(EXPRESSION)
    assert not expression.hasParserError(), expression.parserErrorString()
    result = expression.evaluate(context)
    assert not expression.hasEvalError(), expression.evalErrorString()
    assert isinstance(result, QgsGeometry) and not result.isEmpty()
    assert len(result.asMultiPolyline()) == 2
    assert abs(result.length() - 50.0) < 1e-6
    layer.undoStack().undo()
    assert layer.featureCount() == 0
    layer.undoStack().redo()
    assert layer.featureCount() == 1
    assert layer.rollBack()
    print('Smoke test QGIS: OK')
