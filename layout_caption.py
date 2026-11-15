"""Caption contents and appearance for generated layout labels."""
from .i18n import tr
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor, QFont
from qgis.PyQt.QtWidgets import (QColorDialog, QComboBox, QDoubleSpinBox,
                                 QFontComboBox, QFormLayout, QListWidget,
                                 QListWidgetItem, QPushButton, QAbstractItemView,
                                 QGroupBox)
from qgis.core import QgsTextFormat, QgsVariantUtils

from .layout_arrange import caption_text
from .schema import field_name

FILENAME = '@filename'
ALIGN = {'left': Qt.AlignmentFlag.AlignLeft, 'center': Qt.AlignmentFlag.AlignHCenter,
         'right': Qt.AlignmentFlag.AlignRight}


def defaults(layer):
    return [field_name(layer, 'code'), FILENAME, field_name(layer, 'caption')]


def make_caption(feature, layer, filename, options):
    keys = options.get('fields', defaults(layer))
    parts = []
    for key in keys:
        if key == FILENAME:
            parts.append(filename)
        elif feature.fields().indexFromName(key) >= 0:
            value = feature[key]
            parts.append('' if QgsVariantUtils.isNull(value) else str(value).strip())
        else:
            parts.append('')
    if keys == defaults(layer):
        return caption_text(*parts)
    return ' — '.join(part for part in parts if part)


def apply_caption(label, options):
    fmt = QgsTextFormat()
    if options.get('font'):
        fmt.setFont(QFont(options['font']))
    fmt.setSize(options.get('size', 9))
    fmt.setColor(QColor(options.get('text', '#000000')))
    label.setTextFormat(fmt)
    label.setHAlign(ALIGN.get(options.get('align'), ALIGN['center']))
    label.setVAlign(Qt.AlignmentFlag.AlignVCenter)
    label.setMargin(0)
    background = QColor(options.get('background', '#00ffffff'))
    label.setBackgroundColor(background)
    label.setBackgroundEnabled(background.alpha() > 0)


class CaptionControls(QGroupBox):
    def __init__(self, parent):
        super().__init__(tr('Caption contents and appearance'), parent)
        form = QFormLayout(self)
        self.fields = QListWidget(self)
        self.fields.setMaximumHeight(120)
        self.fields.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        form.addRow(tr('Fields (check and drag to reorder):'), self.fields)
        self.font = QFontComboBox(self)
        form.addRow(tr('Font:'), self.font)
        self.size = QDoubleSpinBox(self)
        self.size.setRange(4, 72)
        self.size.setSuffix(' pt')
        form.addRow(tr('Font size:'), self.size)
        self.align = QComboBox(self)
        for value in ALIGN:
            self.align.addItem(tr(value.title()), value)
        form.addRow(tr('Alignment:'), self.align)
        self.colors = {}
        self.buttons = {}
        for key, title in [('text', tr('Text color:')), ('background', tr('Background color / opacity:'))]:
            button = QPushButton(self)
            button.clicked.connect(lambda checked=False, name=key: self.choose_color(name))
            self.buttons[key] = button
            form.addRow(title, button)

    def choose_color(self, key):
        color = QColorDialog.getColor(self.colors[key], self, tr('Caption color'),
                                      QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if color.isValid():
            self.set_color(key, color)

    def set_color(self, key, color):
        self.colors[key] = color
        self.buttons[key].setText(tr('{color} · {opacity}% opacity').format(color=color.name(), opacity=round(color.alphaF()*100)))

    def load(self, layer, options):
        self.fields.clear()
        chosen = options.get('fields', defaults(layer) if layer else [])
        available = {FILENAME: tr('Image filename (from photo)')}
        if layer:
            available.update({f.name(): tr(layer.attributeDisplayName(i)) if layer.attributeDisplayName(i) in ('Code', 'Caption') else layer.attributeDisplayName(i)
                              for i, f in enumerate(layer.fields())})
            missing_caption = field_name(layer, 'caption')
            if missing_caption not in available:
                available[missing_caption] = tr('Caption')
        for key in dict.fromkeys([*chosen, *available]):
            if key not in available:
                continue
            item = QListWidgetItem(available[key])
            item.setData(Qt.ItemDataRole.UserRole, key)
            item.setCheckState(Qt.CheckState.Checked if key in chosen else Qt.CheckState.Unchecked)
            self.fields.addItem(item)
        self.font.setCurrentFont(QFont(options.get('font') or QgsTextFormat().font().family()))
        self.size.setValue(options.get('size', 9))
        self.align.setCurrentIndex(max(0, self.align.findData(options.get('align', 'center'))))
        self.set_color('text', QColor(options.get('text', '#000000')))
        self.set_color('background', QColor(options.get('background', '#00ffffff')))

    def values(self):
        return dict(fields=[self.fields.item(i).data(Qt.ItemDataRole.UserRole)
                            for i in range(self.fields.count())
                            if self.fields.item(i).checkState() == Qt.CheckState.Checked],
                    font=self.font.currentFont().family(), size=self.size.value(),
                    align=self.align.currentData(),
                    **{key: value.name(QColor.NameFormat.HexArgb) for key, value in self.colors.items()})
