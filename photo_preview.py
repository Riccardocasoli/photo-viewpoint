import logging
from .schema import field_name
from .i18n import tr
from .compat import mouse_position
from qgis.PyQt.QtCore import Qt, QUrl, QSize, QTimer, QEvent, QObject
from qgis.PyQt.QtGui import QDesktopServices, QImageReader, QPixmap
from qgis.PyQt.QtWidgets import QDialog, QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QMessageBox, QSizePolicy, QFileDialog, QFrame
from qgis.core import QgsProject, QgsFeatureRequest, QgsRectangle
from qgis.gui import QgsMapTool
from .photo_paths import resolve_photo


class PreviewDialog(QDialog):
    def __init__(self, parent, code, reference, project_file, layer_source, change_callback=None):
        super().__init__(parent)
        self.setWindowTitle(tr('Foto — ') + code)
        self.resize(850, 650)
        self.pixmap = None
        self.path = None
        self.remote = None
        self.project_file, self.layer_source = project_file, layer_source
        self.change_callback = change_callback
        layout = QVBoxLayout(self)
        title = QLabel(code, self)
        title.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(title)
        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(200, 160)
        self.image_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.image_label.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.image_label, 1)
        self.path_label = QLabel(reference, self)
        self.path_label.setTextFormat(Qt.TextFormat.PlainText)
        self.path_label.setWordWrap(True)
        self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.path_label)
        row = QHBoxLayout()
        self.open_button = QPushButton(tr('Apri immagine'), self)
        self.folder_button = QPushButton(tr('Apri cartella'), self)
        self.change_button = QPushButton(tr('Cambia immagine'), self)
        self.change_button.setEnabled(change_callback is not None)
        close = QPushButton(tr('Chiudi'), self)
        self.open_button.clicked.connect(self.open_image)
        self.folder_button.clicked.connect(self.open_folder)
        self.change_button.clicked.connect(self.change_image)
        close.clicked.connect(self.accept)
        for button in (self.open_button, self.folder_button, self.change_button, close):
            button.setAutoDefault(False)
            row.addWidget(button)
        layout.addLayout(row)
        self.load_reference(reference)

    def load_reference(self, reference):
        self.pixmap, self.path, self.remote = None, None, None
        self.image_label.clear()
        self.path_label.setText(reference)
        self.open_button.setText(tr('Apri immagine'))
        self.open_button.setEnabled(False)
        self.folder_button.setEnabled(False)
        try:
            self.path, self.remote = resolve_photo(reference, self.project_file, self.layer_source)
            if self.remote:
                self.image_label.setText(tr('Riferimento web: premi Apri link per visualizzarlo nel browser.'))
                self.open_button.setText(tr('Apri link'))
                self.open_button.setEnabled(True)
                return
            self.folder_button.setEnabled(self.path.parent.is_dir())
            if not self.path.is_file():
                raise ValueError(tr('File non trovato:\n') + str(self.path))
            self.open_button.setEnabled(True)
            reader = QImageReader(str(self.path))
            reader.setAutoTransform(True)
            size = reader.size()
            if size.isValid() and (size.width() > 1600 or size.height() > 1600):
                reader.setScaledSize(size.scaled(QSize(1600, 1600), Qt.AspectRatioMode.KeepAspectRatio))
            image = reader.read()
            if image.isNull():
                raise ValueError(tr('Impossibile leggere l’immagine: ') + reader.errorString())
            self.pixmap = QPixmap.fromImage(image)
            self.fit_image()
        except (ValueError, OSError) as error:
            self.image_label.setText(str(error))

    def change_image(self):
        directory = str(self.path.parent) if self.path is not None else ''
        filename, _ = QFileDialog.getOpenFileName(self, tr('Cambia fotografia della presa'), directory,
            tr('Fotografie JPEG (*.jpg *.jpeg *.JPG *.JPEG);;Tutte le immagini (*)'))
        if not filename:
            return
        reader = QImageReader(filename)
        if not reader.canRead():
            QMessageBox.warning(self, tr('Prese fotografiche'), tr('Il file scelto non è un’immagine leggibile.'))
            return
        try:
            self.change_callback(filename)
        except (ValueError, RuntimeError) as error:
            QMessageBox.warning(self, tr('Prese fotografiche'), str(error))
            return
        self.load_reference(filename)

    def fit_image(self):
        if self.pixmap is not None:
            self.image_label.setPixmap(self.pixmap.scaled(
                self.image_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_image()

    def open_url(self, url):
        if not QDesktopServices.openUrl(url):
            QMessageBox.warning(self, tr('Prese fotografiche'), tr('Il sistema non è riuscito ad aprire il riferimento.'))

    def open_image(self):
        self.open_url(QUrl(self.remote) if self.remote else QUrl.fromLocalFile(str(self.path)))

    def open_folder(self):
        if self.path is not None:
            self.open_url(QUrl.fromLocalFile(str(self.path.parent)))


def feature_at(tool, layer, pos):
    transform = tool.canvas().getCoordinateTransform()
    corners = [tool.toLayerCoordinates(layer, transform.toMapCoordinates(x, y))
               for x, y in [(pos.x()-12, pos.y()-12), (pos.x()+12, pos.y()-12),
                            (pos.x()-12, pos.y()+12), (pos.x()+12, pos.y()+12)]]
    rect = QgsRectangle(min(p.x() for p in corners), min(p.y() for p in corners),
                        max(p.x() for p in corners), max(p.y() for p in corners))
    candidates = []
    for feature in layer.getFeatures(QgsFeatureRequest().setFilterRect(rect)):
        if feature.geometry().isEmpty():
            continue
        pixel = tool.toCanvasCoordinates(tool.toMapCoordinates(layer, feature.geometry().asPoint()))
        distance = ((pixel.x()-pos.x())**2 + (pixel.y()-pos.y())**2)**0.5
        if distance <= 12:
            candidates.append((distance, feature))
    return min(candidates, key=lambda item: item[0])[1] if candidates else None


class PhotoHover(QObject):
    """Watch the canvas without taking control from the current map tool."""
    def __init__(self, plugin):
        super().__init__(plugin.canvas)
        self.plugin = plugin
        self.hit_tool = QgsMapTool(plugin.canvas)
        self.layer = None
        self.suppressed_layer = None
        self.hover_timer = QTimer(self)
        self.hover_timer.setSingleShot(True)
        self.hover_timer.timeout.connect(self.show_photo_tip)
        self.hover_pos = None
        self.hover_fid = None
        self.tip = QFrame(self.plugin.canvas.viewport())
        self.tip.setObjectName('PhotoViewpointTip')
        self.tip.setStyleSheet('QFrame#PhotoViewpointTip { background: palette(base); border: 1px solid palette(mid); }')
        self.tip.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        contents = QVBoxLayout(self.tip)
        contents.setContentsMargins(6, 5, 6, 6)
        self.tip_title = QLabel(self.tip)
        self.tip_title.setTextFormat(Qt.TextFormat.PlainText)
        self.tip_image = QLabel(self.tip)
        contents.addWidget(self.tip_title)
        contents.addWidget(self.tip_image)
        self.tip.hide()
        self.plugin.canvas.extentsChanged.connect(self.clear_tip)

        self.plugin.canvas.viewport().installEventFilter(self)

    def clear_tip(self):
        self.hover_timer.stop()
        self.hover_pos = None
        self.hover_fid = None
        self.tip.hide()
        self.tip_image.clear()
        if self.suppressed_layer is not None:
            layer, self.suppressed_layer = self.suppressed_layer, None
            try:
                layer.setMapTipsEnabled(True)
            except RuntimeError:
                logging.getLogger(__name__).debug('Tip layer already removed')

    def eventFilter(self, watched, event):
        if watched is self.plugin.canvas.viewport():
            if event.type() in (QEvent.Type.Leave, QEvent.Type.MouseButtonPress, QEvent.Type.Wheel):
                self.clear_tip()
            elif event.type() == QEvent.Type.MouseMove:
                if event.buttons() == Qt.MouseButton.NoButton:
                    self.track(mouse_position(event))
                else:
                    self.clear_tip()
        return False

    def track(self, pos):
        layer = self.plugin.iface.activeLayer()
        if layer is not self.layer:
            self.clear_tip()
            self.layer = layer
        from .layout_photos import compatible
        if not compatible(layer) or layer not in self.plugin.canvas.layers():
            return
        try:
            feature = feature_at(self.hit_tool, self.layer, pos)
        except (ValueError, RuntimeError):
            self.clear_tip()
            return
        fid = feature.id() if feature is not None else None
        if fid == self.hover_fid:
            self.hover_pos = pos
            return
        self.clear_tip()
        if fid is not None:
            self.hover_pos = pos
            self.hover_fid = fid
            self.hover_timer.start(350)

    def show_photo_tip(self):
        if self.hover_pos is None or self.layer is not self.plugin.iface.activeLayer():
            return
        try:
            feature = feature_at(self.hit_tool, self.layer, self.hover_pos)
            if feature is None or feature.id() != self.hover_fid or not isinstance(feature['photo'], str):
                return
            path, remote = resolve_photo(feature['photo'], QgsProject.instance().fileName(), self.layer.source())
            if remote or not path.is_file():
                return
            reader = QImageReader(str(path))
            reader.setAutoTransform(True)
            size = reader.size()
            if not size.isValid():
                return
            if size.width() > 320 or size.height() > 240:
                reader.setScaledSize(size.scaled(QSize(320, 240), Qt.AspectRatioMode.KeepAspectRatio))
            image = reader.read()
            if image.isNull():
                return
            self.tip_title.setText(str(feature[field_name(feature, 'code')]))
            self.tip_image.setPixmap(QPixmap.fromImage(image))
            self.tip.adjustSize()
            viewport = self.plugin.canvas.viewport()
            x, y = self.hover_pos.x() + 16, self.hover_pos.y() + 16
            if x + self.tip.width() > viewport.width():
                x = self.hover_pos.x() - self.tip.width() - 16
            if y + self.tip.height() > viewport.height():
                y = self.hover_pos.y() - self.tip.height() - 16
            self.tip.move(max(0, x), max(0, y))
            self.tip.raise_()
            if hasattr(self.layer, 'mapTipsEnabled') and self.layer.mapTipsEnabled():
                self.suppressed_layer = self.layer
                self.layer.setMapTipsEnabled(False)
            self.tip.show()
        except (ValueError, RuntimeError, OSError):
            logging.getLogger(__name__).debug('Photo tooltip unavailable', exc_info=True)


    def dispose(self):
        self.clear_tip()
        self.plugin.canvas.viewport().removeEventFilter(self)
        self.plugin.canvas.extentsChanged.disconnect(self.clear_tip)
        self.tip.deleteLater()
        self.hit_tool.deleteLater()
        self.deleteLater()


class PreviewTool(QgsMapTool):
    """Click a viewpoint to open its full photo preview."""
    def __init__(self, plugin, layer):
        super().__init__(plugin.canvas)
        self.plugin, self.layer = plugin, layer
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        layer.willBeDeleted.connect(self.layer_deleted)

    def layer_deleted(self):
        self.plugin.stop()

    def canvasReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        feature = feature_at(self, self.layer, mouse_position(event))
        if feature is None:
            self.plugin.message(tr('Click near a viewpoint.'), True)
            return
        value = feature['photo']
        reference = value if isinstance(value, str) else ''
        dialog = PreviewDialog(self.plugin.iface.mainWindow(), str(feature[field_name(feature, 'code')]),
            reference, QgsProject.instance().fileName(), self.layer.source(),
            lambda filename: self.plugin.change_photo(self.layer, feature.id(), filename))
        dialog.exec()

    def deactivate(self):
        self.plugin.iface.statusBarIface().clearMessage()
        super().deactivate()

    def dispose(self):
        try:
            self.layer.willBeDeleted.disconnect(self.layer_deleted)
        except (TypeError, RuntimeError):
            logging.getLogger(__name__).debug('Preview layer already disconnected')
