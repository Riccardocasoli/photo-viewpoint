"""Generate ordinary layout items. No callbacks at export time, no layer edits."""
import logging
import json
from .schema import field_name, configure_table
from .i18n import tr
from pathlib import Path
import math
from .compat import FIELD_STRING, FIELD_DOUBLE, enum_value
from .compat import WKB_POINT
from .compat import LAYOUT_MM
from qgis.PyQt.QtCore import QPointF, Qt, QRectF
from qgis.PyQt.QtGui import QColor, QPolygonF, QImageReader, QImageIOHandler, QFontMetricsF
from qgis.PyQt.QtWidgets import (QDialog, QDialogButtonBox, QComboBox, QDoubleSpinBox,
    QFormLayout, QLabel, QMessageBox, QVBoxLayout, QPushButton)
from qgis.core import (QgsProject, QgsVectorLayer, QgsLayoutItemMap,
    QgsLayoutItem, QgsLayoutItemPage, QgsLayoutItemPicture, QgsLayoutItemPolyline,
    QgsLayoutItemLabel, QgsLayoutPoint, QgsLayoutSize,
    QgsCoordinateTransform, QgsLineSymbol, QgsField)
from .photo_paths import resolve_photo
from .layout_arrange import arrange, fit_size
from .layout_caption import CaptionControls, make_caption, apply_caption

TAG = 'prese_fotografiche/layout_map'
ROLE = 'prese_fotografiche/role'
FID = 'prese_fotografiche/fid'
LAYER = 'prese_fotografiche/layer'

LAYOUT_FIELDS = [('pf_x',FIELD_DOUBLE),('pf_y',FIELD_DOUBLE),
    ('pf_map',FIELD_STRING),('dimX',FIELD_DOUBLE),('dimY',FIELD_DOUBLE),
    ('caption',FIELD_STRING)]


def check_fields(layer):
    for requested,kind in LAYOUT_FIELDS:
        name=field_name(layer,requested)
        idx=layer.fields().indexFromName(name)
        if idx>=0 and layer.fields().field(idx).type()!=kind:
            raise ValueError(tr('Il campo %s esiste con tipo non compatibile.') % name)


def add_fields(layer):
    for requested,kind in LAYOUT_FIELDS:
        name=field_name(layer,requested)
        if layer.fields().indexFromName(name)<0:
            length=(254 if layer.source().split('|')[0].lower().endswith('.shp') else 2000) if requested=='caption' else 80
            field=QgsField(name,kind,len=length) if kind==FIELD_STRING else QgsField(name,kind,len=20,prec=3)
            if not layer.addAttribute(field):
                raise ValueError(tr('Impossibile aggiungere il campo ')+name)
    configure_table(layer)


def ensure_fields(layer):
    check_fields(layer)
    if all(layer.fields().indexFromName(field_name(layer,n))>=0 for n,k in LAYOUT_FIELDS):
        return
    if layer.readOnly() or (not layer.isEditable() and not layer.startEditing()):
        raise ValueError(tr('Abilita la scrittura del layer per aggiungere dimX, dimY e Didascalia.'))
    layer.beginEditCommand(tr('Campi per foto nel layout'))
    try:
        add_fields(layer)
        layer.endEditCommand()
    except Exception:
        layer.destroyEditCommand()
        raise


def caption_height(label,width):
    fmt=label.textFormat()
    font=fmt.font()
    font.setPixelSize(100)
    scale=fmt.size()*25.4/72/100
    rect=QFontMetricsF(font).boundingRect(QRectF(0,0,max(1,width/scale),1000000),
        enum_value(Qt.TextFlag.TextWordWrap | Qt.TextFlag.TextWrapAnywhere),label.text())
    return max(6,rect.height()*scale+2)


def connect_picture(map_item, layer, fid, picture, line, caption):
    if getattr(picture,'_pf_link_callback',None) is None:
        callback = lambda: update_link(map_item,layer,fid,picture,line,caption)
        picture._pf_link_callback = callback
        picture.sizePositionChanged.connect(callback)


def restore_links():
    project = QgsProject.instance()
    for layout in project.layoutManager().printLayouts():
        items = [i for i in layout.items() if isinstance(i,QgsLayoutItem)]
        maps = {i.uuid():i for i in items if isinstance(i,QgsLayoutItemMap)}
        for picture in items:
            if not isinstance(picture,QgsLayoutItemPicture) or not picture.customProperty(TAG,''):
                continue
            key = picture.customProperty(TAG)
            layer_id = picture.customProperty(LAYER,'')
            layer = project.mapLayer(layer_id)
            if key not in maps or layer is None:
                continue
            fid = int(picture.customProperty(FID))
            related = {i.customProperty(ROLE,''):i for i in items if i.customProperty(TAG,'')==key
                and i.customProperty(LAYER,'')==layer_id and int(i.customProperty(FID,-1))==fid}
            line=related.get('leader') or related.get('richiamo')
            label=related.get('caption') or related.get('code') or related.get('codice')
            if line is not None and label is not None:
                connect_picture(maps[key],layer,fid,picture,line,label)


def update_link(map_item, layer, fid, picture, line, caption):
    try:
        feature = layer.getFeature(fid)
        if not feature.isValid() or feature.geometry().isEmpty():
            return
        tx = QgsCoordinateTransform(layer.crs(), map_item.crs(), QgsProject.instance())
        point = tx.transform(feature.geometry().asPoint())
        anchor = map_item.mapToScene(map_item.mapToItemCoords(QPointF(point.x(),point.y())))
        box = picture.mapRectToScene(picture.rect())
        target = QPointF(box.left() if anchor.x()<box.center().x() else box.right(),box.center().y())
        line.setNodes(QPolygonF([line.mapFromScene(anchor),line.mapFromScene(target)]))
        caption.attemptMove(QgsLayoutPoint(box.left(),box.bottom()))
        caption.attemptResize(QgsLayoutSize(box.width(),caption_height(caption,box.width())))
    except RuntimeError:
        # A generated item may have been deleted by the user.
        return


def save_positions(layout, map_item, layer):
    if layout.units() != LAYOUT_MM:
        raise ValueError(tr('Imposta il layout in millimetri.'))
    page = layout.pageCollection().page(map_item.page())
    if page is None:
        raise ValueError(tr('Pagina della mappa non disponibile.'))
    pictures = [i for i in layout.items() if isinstance(i,QgsLayoutItemPicture)
        and i.customProperty(TAG,'')==map_item.uuid() and i.customProperty(LAYER,'')==layer.id()]
    if not pictures:
        raise ValueError(tr('Non ci sono foto generate per questa mappa e questo layer.'))
    entries = []
    for picture in pictures:
        fid = int(picture.customProperty(FID))
        if not layer.getFeature(fid).isValid():
            raise ValueError(tr('Una presa è stata eliminata: rigenera prima il layout.'))
        p = page.mapFromScene(picture.mapToScene(picture.rect().topLeft()))
        entries.append((fid,p.x(),p.y(),picture.rect().width(),picture.rect().height()))
    check_fields(layer)
    if layer.readOnly() or (not layer.isEditable() and not layer.startEditing()):
        raise ValueError(tr('Il layer non è modificabile.'))
    layer.beginEditCommand(tr('Salva posizioni foto nel layout'))
    try:
        add_fields(layer)
        for fid,x,y,w,h in entries:
            for name,value in [('pf_x',x),('pf_y',y),('pf_map',map_item.uuid()),('dimX',w),('dimY',h)]:
                if not layer.changeAttributeValue(fid,layer.fields().indexFromName(name),value):
                    raise ValueError(tr('Aggiornamento coordinate fallito.'))
        layer.endEditCommand()
    except Exception:
        layer.destroyEditCommand()
        raise
    return len(entries)


def compatible(layer):
    return (isinstance(layer, QgsVectorLayer) and layer.wkbType() == WKB_POINT
            and all(layer.fields().indexFromName(field_name(layer,n)) >= 0 for n in ('photo', 'code')))


def generate(layout, map_item, layer, width, height, margin, gap, caption_options=None):
    caption_options = caption_options or {}
    if layout.units() != LAYOUT_MM:
        raise ValueError(tr('Imposta le unità del layout in millimetri.'))
    if layout.atlas().enabled():
        raise ValueError(tr('Questa prima versione lavora su layout statici: disattiva l’atlante.'))
    if layer.id() not in [l.id() for l in map_item.layersToRender()]:
        raise ValueError(tr('Il layer scelto non è tra i layer visualizzati nella mappa del layout.'))
    if not layer.isInScaleRange(map_item.scale()):
        raise ValueError(tr('Il layer non è visibile alla scala della mappa.'))
    page_index = map_item.page()
    page_item = layout.pageCollection().page(page_index)
    if page_item is None:
        raise ValueError(tr('La mappa non appartiene a una pagina valida.'))
    check_fields(layer)
    page_rect = page_item.mapRectToScene(page_item.rect())
    map_rect = map_item.mapRectToScene(map_item.rect())
    tx = QgsCoordinateTransform(layer.crs(), map_item.crs(), QgsProject.instance())
    records, skipped = [], []
    key = map_item.uuid()
    old = [item for item in layout.items() if isinstance(item, QgsLayoutItem)
           and item.customProperty(TAG, '') == key
           and item.customProperty(LAYER, '') == layer.id()]
    existing = {}
    for item in old:
        if isinstance(item, QgsLayoutItemPicture):
            top_left = item.mapToScene(item.rect().topLeft())
            existing[int(item.customProperty(FID))] = (
                top_left.x(), top_left.y(), item.rect().width(), item.rect().height())
    for feature in layer.getFeatures():
        if feature.geometry().isEmpty():
            continue
        point = tx.transform(feature.geometry().asPoint())
        local = map_item.mapToItemCoords(QPointF(point.x(), point.y()))
        if not map_item.rect().contains(local):
            continue
        code = str(feature[field_name(feature, 'code')])
        value = feature['photo']
        try:
            path, remote = resolve_photo(value if isinstance(value, str) else '',
                QgsProject.instance().fileName(), layer.source())
            if remote or not path.is_file():
                raise ValueError(tr('foto locale non disponibile o illeggibile'))
            reader=QImageReader(str(path))
            reader.setAutoTransform(True)
            if not reader.canRead():
                raise ValueError(tr('foto locale non disponibile o illeggibile'))
            size=reader.size()
            pixel_width,pixel_height=size.width(),size.height()
            if reader.transformation() & QImageIOHandler.Transformation.TransformationRotate90:  # Qt: EXIF transformation swaps X/Y.
                pixel_width,pixel_height=pixel_height,pixel_width
            image_size=fit_size(pixel_width,pixel_height,width,height)
        except (ValueError, OSError) as error:
            skipped.append('%s: %s' % (code, error))
            continue
        scene = map_item.mapToScene(local)
        owner = feature['pf_map'] if layer.fields().indexFromName('pf_map')>=0 else ''
        matches = not isinstance(owner,str) or owner in ('',key)
        text = make_caption(feature, layer, Path(path).name, caption_options)
        record = {'fid': feature.id(), 'code': code, 'path': str(path),
                  'anchor': (scene.x(), scene.y()), 'size': image_size, 'caption': text}
        # Live layout items take precedence over the optional layer backup.
        if feature.id() in existing:
            record['box'] = existing[feature.id()]
        elif matches:
            fields = layer.fields()
            if all(fields.indexFromName(n) >= 0 for n in ('dimX', 'dimY')):
                try:
                    w, h = float(feature['dimX']), float(feature['dimY'])
                    if math.isfinite(w) and math.isfinite(h) and w > 0 and h > 0:
                        record['size'] = (w, h)
                except (TypeError, ValueError):
                    logging.getLogger(__name__).debug('No saved photo dimensions')
            if all(fields.indexFromName(n) >= 0 for n in ('pf_x', 'pf_y')):
                try:
                    x, y = float(feature['pf_x']), float(feature['pf_y'])
                    if math.isfinite(x) and math.isfinite(y):
                        pos = page_item.mapToScene(QPointF(x, y))
                        record['box'] = (pos.x(), pos.y(), *record['size'])
                except (TypeError, ValueError):
                    logging.getLogger(__name__).debug('No saved photo position')
        records.append(record)
    if not records:
        raise ValueError(tr('Nessuna presa con immagine locale disponibile nell’inquadratura.\n') + '\n'.join(skipped[:8]))
    def rect_tuple(rect):
        return rect.left(), rect.top(), rect.right(), rect.bottom()
    fixed = [r for r in records if 'box' in r]
    automatic = [r for r in records if 'box' not in r]
    positions = fixed + (arrange(automatic, rect_tuple(page_rect), rect_tuple(map_rect), width, height, margin, gap) if automatic else [])
    # Overlap is explicitly allowed with maps, graphics and other photos.
    ensure_fields(layer)
    base_z=max([i.zValue() for i in layout.items() if isinstance(i,QgsLayoutItem)
        and not isinstance(i,QgsLayoutItemPage) and i not in old]+[map_item.zValue()])
    created = []
    undo = layout.undoStack()
    undo.beginMacro(tr('Foto a bordo pagina'))
    try:
        for record in positions:
            x,y,w,h = record['box']
            anchor = QPointF(*record['anchor'])
            target = QPointF(x if anchor.x()<x+w/2 else x+w,y+h/2)
            line = QgsLayoutItemPolyline(QPolygonF([anchor, target]), layout)
            line.setSymbol(QgsLineSymbol.createSimple({'line_color':'70,85,95','line_width':'0.25'}))
            picture = QgsLayoutItemPicture(layout)
            caption = QgsLayoutItemLabel(layout)
            for item, suffix in [(line,'leader'), (picture,'photo'), (caption,'caption')]:
                layout.addLayoutItem(item)
                created.append(item)
                item.setCustomProperty(TAG,key)
                item.setCustomProperty(ROLE,suffix)
                item.setCustomProperty(FID,record['fid'])
                item.setCustomProperty(LAYER,layer.id())
                item.setId('PF %s %s' % (record[field_name(record, 'code')], suffix))
            line.setZValue(base_z+1)
            picture.setPicturePath(record['path'])
            picture.setResizeMode(QgsLayoutItemPicture.ResizeMode.Zoom)
            picture.attemptMove(QgsLayoutPoint(x,y))
            picture.attemptResize(QgsLayoutSize(w,h))
            picture.setFrameEnabled(True)
            picture.setBackgroundEnabled(True)
            picture.setBackgroundColor(QColor('white'))
            picture.setZValue(base_z+3)
            caption.setText(record[field_name(record, 'caption')].replace('[%', '[ %'))
            apply_caption(caption, caption_options)
            caption.setVisibility(bool(caption.text()))
            caption.attemptMove(QgsLayoutPoint(x,y+h))
            caption.attemptResize(QgsLayoutSize(w,caption_height(caption,w)))
            caption.setZValue(base_z+3)
            connect_picture(map_item,layer,record['fid'],picture,line,caption)
            update_link(map_item,layer,record['fid'],picture,line,caption)
        # The old generation remains intact until all new items have been built.
        for item in old:
            layout.removeLayoutItem(item)
    except Exception:
        for item in reversed(created):
            layout.removeLayoutItem(item)
        raise
    finally:
        undo.endMacro()
    layout.refresh()
    return len(positions), skipped


class LayoutPhotosDialog(QDialog):
    def __init__(self, plugin, layout, parent):
        super().__init__(parent)
        self.plugin = plugin
        self.setWindowTitle(tr('Foto nel layout — genera / aggiorna'))
        self.resize(610, 400)
        outer = QVBoxLayout(self)
        notice = QLabel(tr('Generate / Update refreshes photos, captions and leaders while keeping existing frames.\n'
                        'Size and spacing below apply to new frames without a saved position.\n'
                        'Save frame positions to layer creates a backup for rebuilding missing frames.'), self)
        notice.setWordWrap(True)
        outer.addWidget(notice)
        form = QFormLayout()
        self.maps = QComboBox(self)
        self.layers = QComboBox(self)
        self.layout = layout
        for layer in QgsProject.instance().mapLayers().values():
            if compatible(layer):
                self.layers.addItem(layer.name(),layer.id())
                if layer is plugin.iface.activeLayer():
                    self.layers.setCurrentIndex(self.layers.count()-1)
        form.addRow(tr('Layout:'), QLabel(layout.name(), self))
        form.addRow(tr('Mappa:'),self.maps)
        form.addRow(tr('Layer prese:'),self.layers)
        self.width = self.spin(38,1,1000)
        self.height = self.spin(26,1,1000)
        self.margin = self.spin(8,2,40)
        self.gap = self.spin(4,1,20)
        for name,widget in [(tr('Larghezza massima (mm):'),self.width),(tr('Altezza massima (mm):'),self.height),
                            (tr('Margine iniziale pagina (mm):'),self.margin),(tr('Distanza iniziale fra foto (mm):'),self.gap)]:
            form.addRow(name,widget)
        outer.addLayout(form)
        self.caption_controls = CaptionControls(self)
        outer.addWidget(self.caption_controls)
        save = QPushButton(tr('Save frame positions and sizes to layer'),self)
        save.clicked.connect(self.save_current_positions)
        outer.addWidget(save)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,self)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(tr('OK'))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr('Cancel'))
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(tr('Genera / aggiorna'))
        buttons.accepted.connect(self.build)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)
        self.maps.currentIndexChanged.connect(self.load_caption_options)
        self.layers.currentIndexChanged.connect(self.load_caption_options)
        self.populate_maps()
        self.load_caption_options()

    def load_caption_options(self, *args):
        layer = QgsProject.instance().mapLayer(self.layers.currentData() or '')
        options = {}
        index = self.maps.currentIndex()
        if layer and index >= 0:
            key = 'prese_fotografiche/caption_options/' + layer.id()
            raw = self.map_objects[index].customProperty(key, '{}')
            try:
                options = json.loads(raw)
            except (TypeError, ValueError):
                options = {}
        self.caption_controls.load(layer, options if isinstance(options, dict) else {})

    def spin(self,value,minimum,maximum):
        spin = QDoubleSpinBox(self)
        spin.setRange(minimum,maximum)
        spin.setValue(value)
        return spin

    def populate_maps(self, *args):
        self.maps.clear()
        self.map_objects = []
        self.map_objects = sorted([i for i in self.layout.items() if isinstance(i,QgsLayoutItemMap)],key=lambda i:i.id())
        for i,item in enumerate(self.map_objects):
            self.maps.addItem(tr('%s — pagina %d') % (item.id() or tr('Mappa %d') % (i+1),item.page()+1))

    def build(self):
        if self.maps.currentIndex()<0 or self.layers.currentIndex()<0:
            QMessageBox.warning(self,tr('Foto nel layout'),tr('Crea prima un layout con una mappa e un layer prese con campi codice e photo.'))
            return
        layout = self.layout
        map_item = self.map_objects[self.maps.currentIndex()]
        layer = QgsProject.instance().mapLayer(self.layers.currentData())
        options = self.caption_controls.values()
        try:
            count,skipped = generate(layout,map_item,layer,self.width.value(),self.height.value(),self.margin.value(),self.gap.value(),options)
            map_item.setCustomProperty('prese_fotografiche/caption_options/' + layer.id(), json.dumps(options))
        except Exception as error:
            QMessageBox.warning(self,tr('Foto nel layout'),tr('Generazione non completata:\n')+str(error))
            return
        text = tr('%d foto generate. Salva il progetto.\nRiesegui il comando dopo modifiche alla mappa.') % count
        page=layout.pageCollection().page(map_item.page())
        page_rect=page.mapRectToScene(page.rect())
        if any(not page_rect.contains(i.mapRectToScene(i.rect())) for i in layout.items()
            if isinstance(i,QgsLayoutItemPicture) and i.customProperty(TAG,'')==map_item.uuid() and i.customProperty(LAYER,'')==layer.id()):
            text+=tr('\nAlcune foto sono oltre i bordi della pagina: riposizionale prima di esportare.')
        if skipped:
            text += tr('\n\nPrese escluse (%d):\n%s') % (len(skipped),'\n'.join(skipped[:12]))
        QMessageBox.information(self,tr('Foto nel layout'),text)
        self.accept()

    def save_current_positions(self):
        if self.maps.currentIndex()<0 or self.layers.currentIndex()<0:
            return
        layout = self.layout
        map_item = self.map_objects[self.maps.currentIndex()]
        layer = QgsProject.instance().mapLayer(self.layers.currentData())
        try:
            count = save_positions(layout,map_item,layer)
        except Exception as error:
            QMessageBox.warning(self,tr('Posizioni foto'),str(error))
            return
        QMessageBox.information(self,tr('Posizioni e dimensioni'),tr('%d foto: posizioni e dimensioni salvate nel buffer di modifica. Salva le modifiche del layer per conservarle.') % count)
