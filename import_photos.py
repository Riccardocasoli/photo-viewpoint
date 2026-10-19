"""Batch photo import and a persistent repair queue for geometryless records."""
import logging
from .schema import field_name
from pathlib import Path
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import (QDialog,QVBoxLayout,QLabel,QTableWidget,QTableWidgetItem,
 QDialogButtonBox,QDoubleSpinBox,QFormLayout,QPushButton,QDockWidget,QListWidget,QMessageBox)
from qgis.core import QgsFeature,QgsGeometry,QgsPointXY
from qgis.gui import QgsMapTool
from .i18n import tr
from .photo_metadata import add_metadata_fields,photo_metadata,grid_azimuth
from .import_utils import gps_position,gps_distance,unique_code


def import_records(layer,records,defaults):
    if layer.readOnly() or (not layer.isEditable() and not layer.startEditing()):
        raise ValueError(tr('The layer cannot be edited.'))
    used={str(f[field_name(f, 'code')]) for f in layer.getFeatures()}
    layer.beginEditCommand(tr('Import photos as viewpoints'))
    count,pending=0,0
    try:
        add_metadata_fields(layer)
        for record in records:
            feature=QgsFeature(layer.fields())
            metadata=record['metadata']
            position=gps_position(metadata)
            if position is not None:feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(*position)))
            else:pending+=1
            feature[field_name(feature, 'code')]=unique_code(record['path'],used)
            feature['photo']=record['path']
            feature['azimuth']=record['azimuth'] if record['azimuth'] is not None else defaults['azimuth']
            feature['fov']=defaults['fov'];feature['distance']=defaults['distance']
            for name,value in metadata.items():feature[name]=value
            feature['distGPS']=gps_distance(position,metadata)
            feature['vp_status']='positioned' if position is not None else 'needs_pos'
            if not layer.addFeature(feature):raise ValueError(tr('Photo import failed; the batch was rolled back.'))
            count+=1
        layer.endEditCommand()
    except Exception:
        layer.destroyEditCommand();raise
    layer.updateExtents();layer.triggerRepaint()
    return count,pending


class ImportPhotosDialog(QDialog):
    def __init__(self,plugin,layer,paths):
        super().__init__(plugin.iface.mainWindow())
        self.setWindowTitle(tr('Import photos as viewpoints'))
        self.resize(850,520)
        self.layer=layer;self.records=[]
        outer=QVBoxLayout(self)
        text=QLabel(tr('Checked images create one record each. Photos without usable GPS remain unpositioned until you place them on the map. Uncheck a row to exclude it.'),self)
        text.setWordWrap(True);outer.addWidget(text)
        self.table=QTableWidget(len(paths),4,self)
        self.table.setHorizontalHeaderLabels([tr('Import'),tr('Image'),tr('Position'),tr('Azimuth')])
        for row,path in enumerate(paths):
            metadata=photo_metadata(layer,path)
            position=gps_position(metadata)
            bearing=grid_azimuth(layer,metadata)
            self.records.append({'path':path,'metadata':metadata,'azimuth':bearing})
            check=QTableWidgetItem();check.setFlags(Qt.ItemIsEnabled|Qt.ItemIsUserCheckable);check.setCheckState(Qt.Checked)
            self.table.setItem(row,0,check)
            name=QTableWidgetItem(Path(path).name);name.setToolTip(path);name.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(row,1,name)
            status=QTableWidgetItem(tr('GPS available') if position else tr('Needs manual position')+' — '+str(metadata['exif_stat']))
            status.setFlags(Qt.ItemIsEnabled)
            if not position:status.setForeground(QColor('#bd3e23'))
            self.table.setItem(row,2,status)
            value=QTableWidgetItem('%.1f°'%bearing if bearing is not None else tr('Default'))
            value.setFlags(Qt.ItemIsEnabled);self.table.setItem(row,3,value)
        self.table.resizeColumnsToContents();self.table.horizontalHeader().setStretchLastSection(True)
        outer.addWidget(self.table)
        drop=QPushButton(tr('Exclude all images without GPS'),self);drop.clicked.connect(self.exclude_pending);outer.addWidget(drop)
        form=QFormLayout()
        self.azimuth=self.spin(0,0,359.999)
        self.fov=self.spin(40,1,179)
        self.distance=self.spin(20,0.01,1000000)
        form.addRow(tr('Default azimuth (degrees):'),self.azimuth)
        form.addRow(tr('Default FOV (degrees):'),self.fov)
        form.addRow(tr('Default graphic length (m):'),self.distance)
        outer.addLayout(form)
        note=QLabel(tr('Only true-north EXIF direction can be converted to the layer grid bearing. Magnetic or missing direction uses the default. FOV and graphic length use the defaults.'),self)
        note.setWordWrap(True);outer.addWidget(note)
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel,self)
        buttons.button(QDialogButtonBox.Ok).setText('OK')
        buttons.button(QDialogButtonBox.Cancel).setText('Cancel')
        buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);outer.addWidget(buttons)

    def spin(self,value,low,high):
        result=QDoubleSpinBox(self);result.setDecimals(3);result.setRange(low,high);result.setValue(value);return result

    def exclude_pending(self):
        for row,record in enumerate(self.records):
            if gps_position(record['metadata']) is None:self.table.item(row,0).setCheckState(Qt.Unchecked)

    def values(self):
        records=[r for row,r in enumerate(self.records) if self.table.item(row,0).checkState()==Qt.Checked]
        return records,{'azimuth':self.azimuth.value(),'fov':self.fov.value(),'distance':self.distance.value()}


class PendingPhotosDock(QDockWidget):
    def __init__(self,plugin):
        super().__init__(tr('Photos to position'),plugin.iface.mainWindow())
        self.setObjectName('PhotoViewpointPendingPhotos')
        self.plugin=plugin;self.layer=None
        from qgis.PyQt.QtWidgets import QWidget
        widget=QWidget(self);outer=QVBoxLayout(widget)
        label=QLabel(tr('These records have no geometry. Select an image, then Place on map and click its position. No artificial coordinates are assigned.'),widget)
        label.setWordWrap(True);outer.addWidget(label)
        self.list=QListWidget(widget);outer.addWidget(self.list)
        for title,callback in [('Place on map',self.place),('Delete selected record',self.delete),('Refresh list',self.refresh)]:
            button=QPushButton(tr(title),widget);button.clicked.connect(callback);outer.addWidget(button)
        self.setWidget(widget)

    def bind(self,layer):
        self.layer=layer;self.refresh();self.show();self.raise_()

    def refresh(self):
        self.list.clear()
        if self.layer is None:return
        try:
            from qgis.PyQt.QtWidgets import QListWidgetItem
            for feature in self.layer.getFeatures():
                if feature.geometry().isEmpty():
                    item=QListWidgetItem(str(feature[field_name(feature, 'code')])+' — '+Path(str(feature['photo'])).name)
                    item.setData(Qt.UserRole,feature.id());item.setToolTip(str(feature['photo']));self.list.addItem(item)
        except RuntimeError:self.layer=None

    def selected_fid(self):
        item=self.list.currentItem()
        return item.data(Qt.UserRole) if item else None

    def place(self):
        fid=self.selected_fid()
        if fid is None:return
        try:
            if not self.layer.getFeature(fid).isValid():self.refresh();return
            self.plugin.stop()
            self.plugin.tool=PlacePendingTool(self.plugin,self.layer,fid,self)
            self.plugin.canvas.setMapTool(self.plugin.tool)
            self.plugin.iface.statusBarIface().showMessage(tr('Click the photo viewpoint position on the map. Esc cancels.'))
        except RuntimeError:self.refresh()

    def delete(self):
        fid=self.selected_fid()
        if fid is None:return
        if QMessageBox.question(self,tr('Photos to position'),tr('Delete this layer record? The image file will not be deleted.'),QMessageBox.Yes|QMessageBox.No)!=QMessageBox.Yes:return
        try:
            layer=self.layer
            if layer.readOnly() or (not layer.isEditable() and not layer.startEditing()):raise ValueError(tr('The layer cannot be edited.'))
            layer.beginEditCommand(tr('Delete unpositioned photo'))
            if not layer.deleteFeature(fid):
                layer.destroyEditCommand();raise ValueError(tr('Record deletion failed.'))
            layer.endEditCommand();self.refresh()
        except (ValueError,RuntimeError) as error:self.plugin.message(str(error),True)


class PlacePendingTool(QgsMapTool):
    def __init__(self,plugin,layer,fid,dock):
        super().__init__(plugin.canvas)
        self.plugin,self.layer,self.fid,self.dock=plugin,layer,fid,dock
        self.setCursor(Qt.CrossCursor)
        layer.willBeDeleted.connect(self.deleted)

    def deleted(self):self.plugin.stop()

    def canvasReleaseEvent(self,event):
        if event.button()!=Qt.LeftButton:return
        try:
            feature=self.layer.getFeature(self.fid)
            if not feature.isValid() or not feature.geometry().isEmpty():
                raise ValueError(tr('This record was deleted or is already positioned. Refresh the list.'))
            if self.layer.readOnly() or (not self.layer.isEditable() and not self.layer.startEditing()):
                raise ValueError(tr('The layer cannot be edited.'))
            point=self.toLayerCoordinates(self.layer,event.mapPoint())
            self.layer.beginEditCommand(tr('Position imported photo'))
            if not self.layer.changeGeometry(self.fid,QgsGeometry.fromPointXY(point)):
                self.layer.destroyEditCommand();raise ValueError(tr('Position update failed.'))
            self.layer.endEditCommand();self.layer.triggerRepaint()
            self.dock.refresh();self.plugin.stop()
        except (ValueError,RuntimeError) as error:self.plugin.message(str(error),True)

    def keyPressEvent(self,event):
        if event.key()==Qt.Key_Escape:self.plugin.stop()

    def deactivate(self):
        self.plugin.iface.statusBarIface().clearMessage();super().deactivate()

    def dispose(self):
        try:self.layer.willBeDeleted.disconnect(self.deleted)
        except (RuntimeError,TypeError):logging.getLogger(__name__).debug('Signal already disconnected', exc_info=True)
