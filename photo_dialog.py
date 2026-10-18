"""Dialogo dati della presa; non altera layer o geometrie."""
from .i18n import tr
from qgis.PyQt.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget,
)


class PhotoDialog(QDialog):
    def __init__(self, parent, proposal, used_codes):
        super().__init__(parent)
        self.used_codes = used_codes
        self.setWindowTitle(tr('Dati della presa fotografica'))
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.code_edit = QLineEdit(proposal, self)
        self.photo_edit = QLineEdit(self)
        self.photo_edit.setPlaceholderText(tr('Percorso del JPG o URL (facoltativo)'))
        self.photo_edit.setToolTip(tr('Il riferimento è memorizzato come testo; la fotografia non viene copiata.'))
        row = QWidget(self)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(self.photo_edit)
        browse = QPushButton(tr('Sfoglia…'), self)
        browse.setAutoDefault(False)
        browse.clicked.connect(self.browse)
        row_layout.addWidget(browse)
        form.addRow(tr('Codice / nome:'), self.code_edit)
        form.addRow(tr('Fotografia:'), row)
        layout.addLayout(form)
        self.error_label = QLabel(self)
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.button(QDialogButtonBox.Ok).setText('OK')
        buttons.button(QDialogButtonBox.Cancel).setText('Cancel')
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.code_edit.selectAll()
        self.code_edit.setFocus()

    def browse(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, tr('Seleziona la fotografia'), '',
            tr('Fotografie JPEG (*.jpg *.jpeg *.JPG *.JPEG);;Tutti i file (*)'))
        if filename:
            self.photo_edit.setText(filename)

    def values(self):
        return self.code_edit.text().strip(), self.photo_edit.text().strip()

    def accept(self):
        code, _ = self.values()
        if not code or code in self.used_codes:
            self.error_label.setText(tr('Inserisci un codice non vuoto e diverso da quelli già presenti.'))
            self.code_edit.setFocus()
            return
        super().accept()
