"""Generate ordinary layout items. No callbacks at export time, no layer edits."""
import logging
from .schema import field_name, configure_table
from .i18n import tr
from pathlib import Path
import math
from qgis.PyQt.QtCore import QPointF, Qt, QVariant, QRectF
from qgis.PyQt.QtGui import QColor, QPolygonF, QImageReader, QFontMetricsF
from qgis.PyQt.QtWidgets import (QDialog, QDialogButtonBox, QComboBox, QDoubleSpinBox,
    QFormLayout, QLabel, QMessageBox, QVBoxLayout, QPushButton)
from qgis.core import (QgsProject, QgsVectorLayer, QgsWkbTypes, QgsLayoutItemMap,
    QgsLayoutItem, QgsLayoutItemPage, QgsLayoutItemPicture, QgsLayoutItemPolyline,
    QgsLayoutItemLabel, QgsLayoutPoint, QgsLayoutSize, QgsUnitTypes,
    QgsCoordinateTransform, QgsLineSymbol, QgsTextFormat, QgsField)
from .photo_paths import resolve_photo
from .layout_arrange import arrange, fit_size, caption_text

TAG = 'prese_fotografiche/layout_map'
ROLE = 'prese_fotografiche/role'
FID = 'prese_fotografiche/fid'
LAYER = 'prese_fotografiche/layer'

LAYOUT_FIELDS = [('pf_x',QVariant.Double),('pf_y',QVariant.Double),
    ('pf_map',QVariant.String),('dimX',QVariant.Double),('dimY',QVariant.Double),
    ('caption',QVariant.String)]


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
            field=QgsField(name,kind,len=length) if kind==QVariant.String else QgsField(name,kind,len=20,prec=3)
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
        Qt.TextWordWrap | Qt.TextWrapAnywhere,label.text())
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
    if layout.units() != QgsUnitTypes.LayoutMillimeters:
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
    return (isinstance(layer, QgsVectorLayer) and layer.wkbType() == QgsWkbTypes.Point
            and all(layer.fields().indexFromName(field_name(layer,n)) >= 0 for n in ('photo', 'code')))


def generate(layout, map_item, layer, width, height, margin, gap):
    if layout.units() != QgsUnitTypes.LayoutMillimeters:
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
            if int(reader.transformation()) & 4:  # Qt: EXIF transformation swaps X/Y.
                pixel_width,pixel_height=pixel_height,pixel_width
            image_size=fit_size(pixel_width,pixel_height,width,height)
        except (ValueError, OSError) as error:
            skipped.append('%s: %s' % (code, error))
            continue
        scene = map_item.mapToScene(local)
        owner = feature['pf_map'] if layer.fields().indexFromName('pf_map')>=0 else ''
        matches = not isinstance(owner,str) or owner in ('',key)
        if matches and all(layer.fields().indexFromName(n)>=0 for n in ('dimX','dimY')):
            try:
                saved_w,saved_h=float(feature['dimX']),float(feature['dimY'])
                image_size=fit_size(pixel_width,pixel_height,saved_w,saved_h)
            except (ValueError,TypeError):
                logging.getLogger(__name__).debug('Optional operation could not complete', exc_info=True)
        description=feature[field_name(feature, 'caption')] if layer.fields().indexFromName(field_name(layer,'caption'))>=0 else ''
        text=caption_text(code,Path(path).name,description if isinstance(description,str) else '')
        record = {'fid': feature.id(), 'code': code, 'path': str(path),
                        'anchor': (scene.x(), scene.y()), 'size':image_size,'caption':text}
        if all(layer.fields().indexFromName(n)>=0 for n in ('pf_x','pf_y')):
            try:
                x,y = float(feature['pf_x']),float(feature['pf_y'])
                if math.isfinite(x) and math.isfinite(y) and matches:
                    pos = page_item.mapToScene(QPointF(x,y))
                    record['box'] = (pos.x(),pos.y(),*image_size)
            except (TypeError,ValueError):
                logging.getLogger(__name__).debug('Optional operation could not complete', exc_info=True)
        records.append(record)
    if not records:
        raise ValueError(tr('Nessuna presa con immagine locale disponibile nell’inquadratura.\n') + '\n'.join(skipped[:8]))
    def rect_tuple(rect):
        return rect.left(), rect.top(), rect.right(), rect.bottom()
    fixed = [r for r in records if 'box' in r]
    automatic = [r for r in records if 'box' not in r]
    positions = fixed + (arrange(automatic, rect_tuple(page_rect), rect_tuple(map_rect), width, height, margin, gap) if automatic else [])
    # Never replace arbitrary user items: only our own items for this map.
    old = [i for i in layout.items() if isinstance(i, QgsLayoutItem) and i.customProperty(TAG, '') == key]
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
            picture.setResizeMode(QgsLayoutItemPicture.ZoomResizeFrame)
            picture.attemptMove(QgsLayoutPoint(x,y))
            picture.attemptResize(QgsLayoutSize(w,h))
            picture.setFrameEnabled(True)
            picture.setBackgroundEnabled(True)
            picture.setBackgroundColor(QColor('white'))
            picture.setZValue(base_z+3)
            caption.setText(record[field_name(record, 'caption')].replace('[%', '[ %'))
            fmt = QgsTextFormat()
            fmt.setSize(9)
            caption.setTextFormat(fmt)
            caption.setHAlign(Qt.AlignHCenter)
            caption.setVAlign(Qt.AlignVCenter)
            caption.setMargin(0)
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
    def __init__(self, plugin):
        super().__init__(plugin.iface.mainWindow())
        self.plugin = plugin
        self.setWindowTitle(tr('Foto nel layout — genera / aggiorna'))
        self.resize(610, 400)
        outer = QVBoxLayout(self)
        notice = QLabel(tr('Le dimensioni massime rispettano le proporzioni di ciascuna foto.\n'
            'Genera immagini locali, codici e linee per i punti nell’inquadratura.\n'
            'Sposta e ridimensiona le foto liberamente, anche sopra altri elementi.\n'
            'Salva posizione e dimensioni nel layer; compila Didascalia in tabella.\n'
            'Dopo modifiche a mappa, punti o foto, esegui nuovamente il comando.'), self)
        notice.setWordWrap(True)
        outer.addWidget(notice)
        form = QFormLayout()
        self.layouts = QComboBox(self)
        self.maps = QComboBox(self)
        self.layers = QComboBox(self)
        self.layout_objects = QgsProject.instance().layoutManager().printLayouts()
        for layout in self.layout_objects:
            self.layouts.addItem(layout.name())
        for layer in QgsProject.instance().mapLayers().values():
            if compatible(layer):
                self.layers.addItem(layer.name(),layer.id())
                if layer is plugin.iface.activeLayer():
                    self.layers.setCurrentIndex(self.layers.count()-1)
        form.addRow('Layout:',self.layouts)
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
        save = QPushButton(tr('Salva posizioni e dimensioni (pf_x, pf_y, dimX, dimY)'),self)
        save.clicked.connect(self.save_current_positions)
        outer.addWidget(save)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel,self)
        buttons.button(QDialogButtonBox.Ok).setText('OK')
        buttons.button(QDialogButtonBox.Cancel).setText('Cancel')
        buttons.button(QDialogButtonBox.Ok).setText(tr('Genera / aggiorna'))
        buttons.accepted.connect(self.build)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)
        self.layouts.currentIndexChanged.connect(self.populate_maps)
        self.populate_maps()

    def spin(self,value,minimum,maximum):
        spin = QDoubleSpinBox(self)
        spin.setRange(minimum,maximum)
        spin.setValue(value)
        return spin

    def populate_maps(self, *args):
        self.maps.clear()
        self.map_objects = []
        index = self.layouts.currentIndex()
        if index < 0:
            return
        layout = self.layout_objects[index]
        self.map_objects = sorted([i for i in layout.items() if isinstance(i,QgsLayoutItemMap)],key=lambda i:i.id())
        for i,item in enumerate(self.map_objects):
            self.maps.addItem(tr('%s — pagina %d') % (item.id() or tr('Mappa %d') % (i+1),item.page()+1))

    def build(self):
        if self.layouts.currentIndex()<0 or self.maps.currentIndex()<0 or self.layers.currentIndex()<0:
            QMessageBox.warning(self,tr('Foto nel layout'),tr('Crea prima un layout con una mappa e un layer prese con campi codice e photo.'))
            return
        layout = self.layout_objects[self.layouts.currentIndex()]
        map_item = self.map_objects[self.maps.currentIndex()]
        layer = QgsProject.instance().mapLayer(self.layers.currentData())
        try:
            count,skipped = generate(layout,map_item,layer,self.width.value(),self.height.value(),self.margin.value(),self.gap.value())
        except Exception as error:
            QMessageBox.warning(self,tr('Foto nel layout'),tr('Generazione non completata:\n')+str(error))
            return
        self.plugin.iface.openLayoutDesigner(layout)
        text = tr('%d foto generate. Salva il progetto.\nRiesegui il comando dopo modifiche alla mappa.') % count
        page=layout.pageCollection().page(map_item.page())
        page_rect=page.mapRectToScene(page.rect())
        if any(not page_rect.contains(i.mapRectToScene(i.rect())) for i in layout.items()
            if isinstance(i,QgsLayoutItemPicture) and i.customProperty(TAG,'')==map_item.uuid()):
            text+=tr('\nAlcune foto sono oltre i bordi della pagina: riposizionale prima di esportare.')
        if skipped:
            text += tr('\n\nPrese escluse (%d):\n%s') % (len(skipped),'\n'.join(skipped[:12]))
        QMessageBox.information(self,tr('Foto nel layout'),text)
        self.accept()

    def save_current_positions(self):
        if self.layouts.currentIndex()<0 or self.maps.currentIndex()<0 or self.layers.currentIndex()<0:
            return
        layout = self.layout_objects[self.layouts.currentIndex()]
        map_item = self.map_objects[self.maps.currentIndex()]
        layer = QgsProject.instance().mapLayer(self.layers.currentData())
        try:
            count = save_positions(layout,map_item,layer)
        except Exception as error:
            QMessageBox.warning(self,tr('Posizioni foto'),str(error))
            return
        QMessageBox.information(self,tr('Posizioni e dimensioni'),tr('%d foto: posizioni e dimensioni salvate nel buffer di modifica. Salva le modifiche del layer per conservarle.') % count)
