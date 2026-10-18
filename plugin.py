from .schema import field_name
from .schema import configure_table, caption_length
from .i18n import tr
import math
from pathlib import Path
from qgis.PyQt.QtCore import Qt, QVariant
from qgis.PyQt.QtGui import QColor, QIcon
from qgis.PyQt.QtWidgets import QAction, QDialog, QFileDialog, QMessageBox
from qgis.core import (
    Qgis, QgsProject, QgsVectorLayer, QgsField, QgsFeature, QgsGeometry,
    QgsPointXY, QgsWkbTypes, QgsUnitTypes, QgsMarkerSymbol, QgsLineSymbol,
    QgsGeometryGeneratorSymbolLayer, QgsSingleSymbolRenderer,
    QgsPalLayerSettings, QgsTextFormat, QgsTextBufferSettings,
    QgsVectorLayerSimpleLabeling, QgsFeatureRequest, QgsRectangle, QgsVectorFileWriter,
)
from qgis.gui import QgsMapTool, QgsRubberBand, QgsVertexMarker, QgsProjectionSelectionDialog
from .geometry_utils import direction, aperture, endpoint, valid_fov
from .photo_dialog import PhotoDialog
from .photo_preview import PreviewTool
from .create_layer_dialog import CreateLayerDialog, write_dataset
from .photo_metadata import METADATA_FIELDS, add_metadata_fields, photo_metadata, configure_tracking
from .import_utils import gps_distance


FIELDS = {'code': QVariant.String, 'azimuth': QVariant.Double,
          'fov': QVariant.Double, 'distance': QVariant.Double,
          'photo': QVariant.String, 'note': QVariant.String}
EXPRESSION = '''collect_geometries(
 make_line($geometry, project($geometry, "distance", radians("azimuth"-"fov"/2.0))),
 make_line($geometry, project($geometry, "distance", radians("azimuth"+"fov"/2.0))))'''


class PhotoPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.tool = None
        self.actions = []
        self.pending_dock = None

    def initGui(self):
        self.toolbar = self.iface.addToolBar(tr('Prese fotografiche'))
        self.toolbar.setObjectName('PreseFotograficheToolbar')
        self.toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)
        for text, icon, callback in [
            (tr('Crea layer foto'), 'layer.svg', self.create_layer),
            (tr('Create viewpoint then link photo'), 'point_to_photo.svg', lambda: self.activate(False)),
            (tr('Create viewpoints from photos'), 'photo_to_point.svg', self.import_photos),
            (tr('Photos to position'), 'pending.svg', self.show_pending),
            (tr('Modifica presa'), 'edit.svg', lambda: self.activate(True)),
            (tr('Visualizza foto'), 'preview.svg', self.activate_preview),
            ('Apply viewpoint style', 'style.svg', self.apply_style),
            (tr('Foto nel layout'), 'layout.svg', self.layout_photos),
            (tr('Read photo metadata'), 'metadata.svg', self.read_metadata),
        ]:
            action = QAction(QIcon(str(Path(__file__).parent / 'icons' / icon)), text, self.iface.mainWindow())
            action.setToolTip(text)
            action.setStatusTip(text)
            action.triggered.connect(callback)
            self.toolbar.addAction(action)
            self.iface.addPluginToMenu(tr('Prese fotografiche'), action)
            self.actions.append(action)
        QgsProject.instance().readProject.connect(self.restore_layout_links)
        self.restore_layout_links()

    def unload(self):
        self.stop()
        if self.pending_dock is not None:
            self.iface.removeDockWidget(self.pending_dock)
            self.pending_dock.deleteLater()
            self.pending_dock=None
        QgsProject.instance().readProject.disconnect(self.restore_layout_links)
        for action in self.actions:
            self.iface.removePluginMenu(tr('Prese fotografiche'), action)
        self.toolbar.deleteLater()

    def layout_photos(self):
        from .layout_photos import LayoutPhotosDialog
        LayoutPhotosDialog(self).exec()

    def restore_layout_links(self, *args):
        from .layout_photos import restore_links
        restore_links()
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer,QgsVectorLayer) and all(layer.fields().indexFromName(field_name(layer,n))>=0 for n in ('code','photo','azimuth','gps_x','gps_y')):
                configure_tracking(layer)
                configure_table(layer)

    def show_pending(self):
        try:
            layer=self.layer()
            if self.pending_dock is None:
                from .import_photos import PendingPhotosDock
                self.pending_dock=PendingPhotosDock(self)
                self.iface.addDockWidget(Qt.RightDockWidgetArea,self.pending_dock)
            self.pending_dock.bind(layer)
        except ValueError as error:self.message(str(error),True)

    def import_photos(self):
        try:
            layer=self.layer()
            self.stop()
            paths,_=QFileDialog.getOpenFileNames(self.iface.mainWindow(),tr('Select photos to import'),QgsProject.instance().homePath(),
                tr('Images (*.jpg *.jpeg *.JPG *.JPEG *.tif *.tiff *.TIF *.TIFF *.png *.PNG);;All files (*)'))
            if not paths:return
            from .import_photos import ImportPhotosDialog,import_records
            dialog=ImportPhotosDialog(self,layer,list(dict.fromkeys(paths)))
            if dialog.exec()!=QDialog.Accepted:return
            records,defaults=dialog.values()
            if not records:return
            count,pending=import_records(layer,records,defaults)
            self.message(tr('%d records created; %d need a manual position. Save layer edits.')%(count,pending))
            if pending:self.show_pending()
        except Exception as error:self.message(str(error),True)

    def message(self, text, warning=False):
        self.iface.messageBar().pushMessage(tr('Prese fotografiche'), text,
            level=Qgis.Warning if warning else Qgis.Info, duration=6)

    def stop(self):
        if self.tool:
            self.canvas.unsetMapTool(self.tool)
            self.tool.dispose()
            self.tool = None

    def layer(self):
        layer = self.iface.activeLayer()
        if not isinstance(layer, QgsVectorLayer) or layer.wkbType() != QgsWkbTypes.Point:
            raise ValueError(tr('Seleziona un layer Point semplice (senza Z/M).'))
        crs = layer.crs()
        if not crs.isValid() or crs.isGeographic() or crs.mapUnits() != QgsUnitTypes.DistanceMeters:
            raise ValueError(tr('Il layer deve avere un CRS proiettato con unità in metri.'))
        missing = [name for name in FIELDS if layer.fields().indexFromName(field_name(layer,name)) < 0]
        if missing:
            raise ValueError(tr('Campi mancanti: ') + ', '.join(missing) + tr('. Usa Crea layer foto.'))
        if layer.fields().field(field_name(layer,'code')).type() != QVariant.String:
            raise ValueError(tr('Il campo codice deve essere di tipo Testo.'))
        for name in ('azimuth', 'fov', 'distance'):
            if layer.fields().field(name).type() != QVariant.Double:
                raise ValueError(tr('Il campo ') + name + tr(' deve essere di tipo Decimale/Double.'))
        return layer

    def create_layer(self):
        dialog = CreateLayerDialog(self.iface.mainWindow())
        if dialog.exec()!=QDialog.Accepted:
            return
        name,crs,driver,path=dialog.values()
        layer = QgsVectorLayer('Point', name, 'memory')
        layer.setCrs(crs)
        all_fields={'code':QVariant.String,'caption':QVariant.String,'distGPS':QVariant.Double,
            **{n:k for n,k in FIELDS.items() if n!='code'},**METADATA_FIELDS,'vp_status':QVariant.String}
        fields=[]
        for field_name,kind in all_fields.items():
            length=caption_length(driver) if field_name=='caption' else 254
            fields.append(QgsField(field_name,kind,len=length) if kind==QVariant.String else QgsField(field_name,kind,len=24,prec=10))
        if not layer.dataProvider().addAttributes(fields):
            self.message(tr('Cannot create layer fields.'),True);return
        layer.updateFields()
        if driver!='memory':
            try:
                layer=write_dataset(layer,name,driver,path)
            except Exception as error:
                self.message(str(error),True);return
        self.stop()
        configure_tracking(layer)
        self.style(layer)
        QgsProject.instance().addMapLayer(layer)
        self.iface.setActiveLayer(layer)
        status=tr('Temporary layer created. Export its data before closing QGIS.') if driver=='memory' else tr('File layer created. Save the project to preserve its style; save edits as usual.')
        if driver!='memory':
            try:
                from .viewpoint_styles import save_portable_style
                self.message(status+' | '+' | '.join(save_portable_style(layer)))
            except Exception as error:self.message(status+' Style save failed: '+str(error),True)
        else:self.message(status)

    def style(self, layer):
        from .viewpoint_styles import apply_style
        apply_style(layer,'classic',2.5,True)

    def apply_style(self):
        try:
            layer=self.layer()
            from .viewpoint_styles import StyleDialog,apply_style,save_portable_style
            dialog=StyleDialog(self.iface.mainWindow(),layer,lambda:self.english_copy(layer))
            if dialog.exec()!=QDialog.Accepted:return
            apply_style(layer,dialog.preset.currentData(),dialog.size.value(),dialog.labels.isChecked())
            if dialog.persist.isChecked():self.message(' | '.join(save_portable_style(layer)))
        except Exception as error:
            self.message(str(error), True)

    def english_copy(self,layer):
        filename,_=QFileDialog.getSaveFileName(self.iface.mainWindow(),'Create English-field GeoPackage copy',QgsProject.instance().homePath(),'GeoPackage (*.gpkg)')
        if not filename:return
        if not filename.lower().endswith('.gpkg'):filename+='.gpkg'
        try:
            from .english_copy import make_english_copy
            from .viewpoint_styles import apply_style,save_portable_style
            copy=make_english_copy(layer,filename)
            apply_style(copy,layer.customProperty('photo_viewpoint/preset','classic'),float(layer.customProperty('photo_viewpoint/size',4)),layer.labelsEnabled())
            QgsProject.instance().addMapLayer(copy)
            save_portable_style(copy)
            QMessageBox.information(self.iface.mainWindow(),'English-field copy','Copy created. The original layer is unchanged. Select the copy to use it; regenerate layout photo links for the new layer.')
        except Exception as error:self.message(str(error),True)

    def activate(self, editing):
        try:
            layer = self.layer()
            if layer.readOnly() or (not layer.isEditable() and not layer.startEditing()):
                raise ValueError(tr('Impossibile attivare la modifica del layer.'))
            self.stop()
            self.tool = PhotoTool(self, layer, editing)
            self.canvas.setMapTool(self.tool)
            self.tool.hint()
        except ValueError as error:
            self.message(str(error), True)

    def activate_preview(self):
        try:
            layer = self.layer()
            self.stop()
            self.tool = PreviewTool(self, layer)
            self.canvas.setMapTool(self.tool)
            self.iface.statusBarIface().showMessage(tr('Visualizza foto: clicca sul punto di presa.'))
        except ValueError as error:
            self.message(str(error), True)

    def ask_details(self, layer):
        used = {str(f[field_name(f, 'code')]) for f in layer.getFeatures() if f[field_name(f, 'code')] is not None}
        n = 1
        while 'F%03d' % n in used:
            n += 1
        dialog = PhotoDialog(self.iface.mainWindow(), 'F%03d' % n, used)
        if dialog.exec() != QDialog.Accepted:
            return None
        return dialog.values()

    def change_photo(self, layer, fid, reference):
        if not layer.getFeature(fid).isValid():
            raise ValueError(tr('La presa non esiste più nel layer.'))
        if layer.readOnly() or (not layer.isEditable() and not layer.startEditing()):
            raise ValueError(tr('Impossibile attivare la modifica del layer.'))
        index = layer.fields().indexFromName('photo')
        if index < 0:
            raise ValueError(tr('Il campo photo non è presente nel layer.'))
        metadata=photo_metadata(layer,reference)
        layer.beginEditCommand(tr('Cambia immagine della presa'))
        try:
            add_metadata_fields(layer)
            for name,value in dict(metadata,photo=reference).items():
                if not layer.changeAttributeValue(fid,layer.fields().indexFromName(name),value):
                    raise ValueError(tr('Image reference or metadata update failed.'))
            layer.endEditCommand()
        except Exception:
            layer.destroyEditCommand()
            raise
        layer.triggerRepaint()

    def read_metadata(self):
        try:
            layer=self.layer()
            if layer.readOnly() or (not layer.isEditable() and not layer.startEditing()):
                raise ValueError(tr('The layer cannot be edited.'))
            features=list(layer.getSelectedFeatures() if layer.selectedFeatureCount() else layer.getFeatures())
            layer.beginEditCommand(tr('Read photo metadata'))
            try:
                add_metadata_fields(layer)
                for feature in features:
                    reference=feature['photo'] if isinstance(feature['photo'],str) else ''
                    for name,value in photo_metadata(layer,reference).items():
                        if not layer.changeAttributeValue(feature.id(),layer.fields().indexFromName(name),value):
                            raise ValueError(tr('Metadata update failed.'))
                layer.endEditCommand()
            except Exception:
                layer.destroyEditCommand();raise
            self.message(tr('Metadata processed for %d photo(s). Check exif_stat and save layer edits.') % len(features))
        except Exception as error:
            self.message(str(error),True)


class PhotoTool(QgsMapTool):
    def __init__(self, plugin, layer, editing):
        super().__init__(plugin.canvas)
        self.plugin, self.layer, self.editing = plugin, layer, editing
        self.state = None
        self.stage = 0
        self.fid = None
        self.drag = None
        self.backup = None
        self.markers = []
        self.rubber = QgsRubberBand(self.canvas(), QgsWkbTypes.LineGeometry)
        self.rubber.setColor(QColor(35, 125, 210))
        self.rubber.setWidth(2)
        self.setCursor(Qt.CrossCursor)
        layer.willBeDeleted.connect(self.layer_deleted)
        layer.editingStopped.connect(self.editing_stopped)
        self.canvas().destinationCrsChanged.connect(self.refresh)

    def layer_deleted(self):
        self.plugin.stop()

    def editing_stopped(self):
        self.plugin.stop()

    def refresh(self):
        if self.state:
            self.draw()

    def hint(self):
        if self.editing:
            text = tr('Clic sul punto; trascina posizione, asse o bordo. Esc annulla il trascinamento.')
        else:
            text = [tr('1/3: punto di presa'), tr('2/3: direzione e lunghezza'),
                    tr('3/3: bordo del campo visivo; poi assegna il codice')][self.stage]
        self.plugin.iface.statusBarIface().showMessage(text)

    def point(self, event):
        p = self.toLayerCoordinates(self.layer, event.mapPoint())
        return p.x(), p.y()

    def map_point(self, p):
        return self.toMapCoordinates(self.layer, QgsPointXY(*p))

    def screen_distance(self, event, p):
        pixel = self.toCanvasCoordinates(self.map_point(p))
        return math.hypot(pixel.x() - event.pos().x(), pixel.y() - event.pos().y())

    def handles(self):
        s = self.state
        return [s['origin'], endpoint(s['origin'], s['azimuth'], s['distance']),
                endpoint(s['origin'], s['azimuth'] + s['fov']/2, s['distance'])]

    def clear_markers(self):
        for marker in self.markers:
            self.canvas().scene().removeItem(marker)
        self.markers = []

    def draw(self):
        self.clear_markers()
        self.rubber.reset(QgsWkbTypes.LineGeometry)
        if not self.state:
            return
        s = self.state
        center = QgsPointXY(*s['origin'])
        angles = [s['azimuth']] if self.stage == 1 and not self.editing else [
            s['azimuth']-s['fov']/2, s['azimuth'], s['azimuth']+s['fov']/2]
        lines = [[center, QgsPointXY(*endpoint(s['origin'], angle, s['distance']))] for angle in angles]
        self.rubber.setToGeometry(QgsGeometry.fromMultiPolylineXY(lines), self.layer)
        points = self.handles() if self.editing else [s['origin']]
        for i, p in enumerate(points):
            marker = QgsVertexMarker(self.canvas())
            marker.setCenter(self.map_point(p))
            marker.setIconType(QgsVertexMarker.ICON_BOX if i else QgsVertexMarker.ICON_CIRCLE)
            marker.setIconSize(10)
            marker.setColor(QColor('blue'))
            marker.setPenWidth(2)
            self.markers.append(marker)
        self.plugin.iface.statusBarIface().showMessage(
            tr('Azimut %.1f° | Apertura %.1f° | Lunghezza %.2f m%s') % (
                s['azimuth'], s['fov'], s['distance'],
                '' if valid_fov(s['fov']) else tr(' | Apertura ammessa: 1–179°')))

    def reset(self):
        self.state, self.fid, self.drag, self.backup = None, None, None, None
        self.stage = 0
        self.draw()
        self.hint()

    def canvasPressEvent(self, event):
        if not self.editing or event.button() != Qt.LeftButton:
            return
        if self.state:
            distances = [self.screen_distance(event, p) for p in self.handles()]
            index = min(range(3), key=lambda i: distances[i])
            if distances[index] <= 12:
                self.drag = index
                self.backup = dict(self.state)
                return
        self.pick(event)

    def pick(self, event):
        # Filter in layer coordinates, then choose within 12 screen pixels.
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
            p = feature.geometry().asPoint()
            d = self.screen_distance(event, (p.x(), p.y()))
            if d <= 12:
                candidates.append((d, feature))
        if not candidates:
            self.layer.removeSelection()
            self.reset()
            return
        feature = min(candidates, key=lambda item: item[0])[1]
        try:
            az, fov, length = [float(feature[name]) for name in ('azimuth', 'fov', 'distance')]
            if not all(math.isfinite(v) for v in (az, fov, length)) or length <= 0 or not valid_fov(fov):
                raise ValueError()
        except (TypeError, ValueError):
            self.plugin.message(tr('La feature ha parametri mancanti o non validi.'), True)
            return
        p = feature.geometry().asPoint()
        self.fid = feature.id()
        self.state = {'origin': (p.x(), p.y()), 'azimuth': az % 360, 'fov': fov, 'distance': length}
        self.layer.selectByIds([self.fid])
        self.draw()

    def canvasMoveEvent(self, event):
        if not self.state or (self.editing and self.drag is None):
            return
        try:
            p = self.point(event)
            s = self.state
            if self.editing and self.drag == 0:
                s['origin'] = p
            elif (not self.editing and self.stage == 1) or self.drag == 1:
                s['azimuth'], s['distance'] = direction(s['origin'], p)
            else:
                edge, _ = direction(s['origin'], p)
                s['fov'] = aperture(s['azimuth'], edge)
            self.draw()
        except ValueError:
            pass

    def canvasReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        if self.editing:
            if self.drag is not None:
                self.canvasMoveEvent(event)
                if valid_fov(self.state['fov']):
                    self.save_edit()
                else:
                    self.state = self.backup
                    self.plugin.message(tr('Apertura ammessa: 1–179°. Modifica annullata.'), True)
                self.drag, self.backup = None, None
                self.draw()
            return
        try:
            p = self.point(event)
            if self.stage == 0:
                self.state = {'origin': p, 'azimuth': 0.0, 'distance': 1.0, 'fov': 60.0}
                self.stage = 1
            elif self.stage == 1:
                self.state['azimuth'], self.state['distance'] = direction(self.state['origin'], p)
                self.stage = 2
            else:
                edge, _ = direction(self.state['origin'], p)
                self.state['fov'] = aperture(self.state['azimuth'], edge)
                if not valid_fov(self.state['fov']):
                    raise ValueError(tr('Apertura ammessa: 1–179°. Scegli un bordo davanti alla presa.'))
                details = self.plugin.ask_details(self.layer)
                if details is None:
                    self.reset()
                    return
                self.save_new(*details)
                self.reset()
                return
            self.draw()
            self.hint()
        except ValueError as error:
            self.plugin.message(str(error), True)

    def save_new(self, code, photo=''):
        metadata=photo_metadata(self.layer,photo)
        self.layer.beginEditCommand(tr('Nuova presa fotografica ') + code)
        try:
            add_metadata_fields(self.layer)
            self._insert_feature(code,photo,metadata)
            self.layer.endEditCommand()
        except Exception:
            self.layer.destroyEditCommand()
            raise
        self.layer.triggerRepaint()

    def _insert_feature(self,code,photo,metadata):
        feature = QgsFeature(self.layer.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(*self.state['origin'])))
        for name in ('azimuth', 'fov', 'distance'):
            feature[name] = self.state[name]
        feature[field_name(feature, 'code')] = code
        feature['photo'] = photo
        for name,value in metadata.items():
            feature[name]=value
        feature['distGPS']=gps_distance(self.state['origin'],metadata)
        feature['vp_status']='positioned'
        if not self.layer.addFeature(feature):
            raise ValueError(tr('Inserimento fallito. Nessuna presa aggiunta.'))

    def save_edit(self):
        # The feature may have been deleted or changed in an attribute table.
        if not self.layer.getFeature(self.fid).isValid():
            self.plugin.message(tr('La feature è stata rimossa.'), True)
            self.state = self.backup
            return
        self.layer.beginEditCommand(tr('Modifica presa fotografica'))
        success = self.layer.changeGeometry(self.fid, QgsGeometry.fromPointXY(QgsPointXY(*self.state['origin'])))
        for name in ('azimuth', 'fov', 'distance'):
            success = self.layer.changeAttributeValue(self.fid, self.layer.fields().indexFromName(name), self.state[name]) and success
        if success:
            self.layer.endEditCommand()
        else:
            self.layer.destroyEditCommand()
            self.state = self.backup
            self.plugin.message(tr('Modifica fallita e annullata.'), True)
        self.layer.triggerRepaint()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            if self.drag is not None:
                self.state = self.backup
                self.drag, self.backup = None, None
                self.draw()
            else:
                self.reset()
        elif event.key() == Qt.Key_Backspace and not self.editing and self.stage:
            self.stage -= 1
            if self.stage == 0:
                self.reset()
            else:
                self.draw()
                self.hint()

    def deactivate(self):
        self.reset()
        self.plugin.iface.statusBarIface().clearMessage()
        super().deactivate()

    def dispose(self):
        self.clear_markers()
        self.canvas().scene().removeItem(self.rubber)
        for signal, slot in [(self.layer.willBeDeleted, self.layer_deleted),
                             (self.layer.editingStopped, self.editing_stopped),
                             (self.canvas().destinationCrsChanged, self.refresh)]:
            try:
                signal.disconnect(slot)
            except (TypeError, RuntimeError):
                pass
