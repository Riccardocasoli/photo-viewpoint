from .schema import field_name
from .i18n import tr
from qgis.PyQt.QtCore import Qt, QUrl, QSize
from qgis.PyQt.QtGui import QDesktopServices, QImageReader, QPixmap
from qgis.PyQt.QtWidgets import QDialog, QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QMessageBox, QSizePolicy, QFileDialog
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
        title.setTextFormat(Qt.PlainText)
        layout.addWidget(title)
        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(200, 160)
        self.image_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.image_label.setTextFormat(Qt.PlainText)
        layout.addWidget(self.image_label, 1)
        self.path_label = QLabel(reference, self)
        self.path_label.setTextFormat(Qt.PlainText)
        self.path_label.setWordWrap(True)
        self.path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
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
                reader.setScaledSize(size.scaled(QSize(1600, 1600), Qt.KeepAspectRatio))
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
                self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

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


class PreviewTool(QgsMapTool):
    """Viewing does not edit; explicit image replacement updates only photo."""
    def __init__(self, plugin, layer):
        super().__init__(plugin.canvas)
        self.plugin, self.layer = plugin, layer
        self.setCursor(Qt.PointingHandCursor)
        layer.willBeDeleted.connect(self.layer_deleted)

    def layer_deleted(self):
        self.plugin.stop()

    def canvasReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        pos = event.pos()
        transform = self.canvas().getCoordinateTransform()
        corners = [self.toLayerCoordinates(self.layer, transform.toMapCoordinates(x, y))
                   for x, y in [(pos.x()-12, pos.y()-12), (pos.x()+12, pos.y()-12),
                                (pos.x()-12, pos.y()+12), (pos.x()+12, pos.y()+12)]]
        rect = QgsRectangle(min(p.x() for p in corners), min(p.y() for p in corners),
                            max(p.x() for p in corners), max(p.y() for p in corners))
        candidates = []
        for feature in self.layer.getFeatures(QgsFeatureRequest().setFilterRect(rect)):
            if feature.geometry().isEmpty():
                continue
            pixel = self.toCanvasCoordinates(self.toMapCoordinates(self.layer, feature.geometry().asPoint()))
            distance = ((pixel.x()-pos.x())**2 + (pixel.y()-pos.y())**2)**0.5
            if distance <= 12:
                candidates.append((distance, feature))
        if not candidates:
            self.plugin.message('Clicca vicino al punto di presa.', True)
            return
        feature = min(candidates, key=lambda item: item[0])[1]
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
            pass
