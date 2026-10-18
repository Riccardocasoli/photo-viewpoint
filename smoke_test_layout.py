"""Run in QGIS console: import prese_fotografiche.smoke_test_layout as t; t.run()."""
from .schema import field_name
import tempfile
from pathlib import Path
from qgis.PyQt.QtCore import QVariant, QPointF
from qgis.PyQt.QtGui import QImage
from qgis.core import (QgsProject, QgsPrintLayout, QgsLayoutItemMap, QgsLayoutItemPage,
    QgsLayoutPoint, QgsLayoutSize, QgsVectorLayer, QgsField, QgsFeature,
    QgsGeometry, QgsPointXY, QgsRectangle, QgsLayoutItemPicture)
from .layout_photos import generate,save_positions,TAG,ROLE,update_link


def run():
    project = QgsProject.instance()
    layer = QgsVectorLayer('Point?crs=EPSG:32632','TEST layout foto','memory')
    layer.dataProvider().addAttributes([QgsField('code',QVariant.String),QgsField('photo',QVariant.String)])
    layer.updateFields()
    project.addMapLayer(layer,False)
    try:
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory)/'test.jpg')
            image = QImage(100,60,QImage.Format_RGB32)
            image.fill(0xffccaa)
            assert image.save(path,'JPG')
            feature = QgsFeature(layer.fields())
            feature[field_name(feature, 'code')]='TEST';feature['photo']=path
            feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(50,50)))
            assert layer.dataProvider().addFeatures([feature])[0]
            layer.updateExtents()
            layout = QgsPrintLayout(project)
            layout.initializeDefaults()
            layout.pageCollection().page(0).setPageSize('A4',QgsLayoutItemPage.Landscape)
            m = QgsLayoutItemMap(layout)
            layout.addLayoutItem(m)
            m.attemptMove(QgsLayoutPoint(60,20))
            m.attemptResize(QgsLayoutSize(175,170))
            m.setCrs(layer.crs());m.setLayers([layer]);m.setKeepLayerSet(True)
            m.zoomToExtent(QgsRectangle(0,0,100,100))
            for angle in (0,25):
                m.setMapRotation(angle)
                count,skipped=generate(layout,m,layer,38,26,8,4)
                assert count==1 and not skipped
                generated=[i for i in layout.items() if hasattr(i,'customProperty') and i.customProperty(TAG,'')==m.uuid()]
                assert len(generated)==3
                line=next(i for i in generated if i.customProperty(ROLE,'')=='leader')
                expected=m.mapToScene(m.mapToItemCoords(QPointF(50,50)))
                actual=line.nodePosition(0)
                assert abs(actual.x()-expected.x())<0.1 and abs(actual.y()-expected.y())<0.1
            picture=next(i for i in generated if isinstance(i,QgsLayoutItemPicture))
            assert abs(picture.rect().width()/picture.rect().height()-100/60)<0.01
            assert layer.fields().indexFromName('caption')>=0
            assert layer.fields().indexFromName('dimX')>=0
            assert layer.fields().indexFromName('dimY')>=0
            picture.attemptResize(QgsLayoutSize(30,18))
            picture.attemptMove(QgsLayoutPoint(8,50))
            assert save_positions(layout,m,layer)==1
            saved=next(layer.getFeatures())
            assert abs(float(saved['pf_x'])-8)<0.2 and abs(float(saved['pf_y'])-50)<0.2
            assert saved['pf_map']==m.uuid()
            assert abs(float(saved['dimX'])-30)<0.2 and abs(float(saved['dimY'])-18)<0.2
            assert layer.changeAttributeValue(saved.id(),layer.fields().indexFromName('caption'),'Didascalia di prova')
            # Full-page map and an overlapping user item must not block generation.
            m.attemptMove(QgsLayoutPoint(0,0))
            m.attemptResize(QgsLayoutSize(297,210))
            assert generate(layout,m,layer,38,26,8,4)[0]==1
            picture=next(i for i in layout.items() if isinstance(i,QgsLayoutItemPicture))
            assert abs(picture.pos().y()-50)<0.2
            assert abs(picture.rect().width()-30)<0.2 and abs(picture.rect().height()-18)<0.2
            caption=next(i for i in layout.items() if hasattr(i,'customProperty') and i.customProperty(ROLE,'')=='caption')
            assert 'test.jpg' in caption.text() and 'Didascalia di prova' in caption.text()
            layer.rollBack()
        print('Smoke test layout: OK')
    finally:
        project.removeMapLayer(layer.id())
