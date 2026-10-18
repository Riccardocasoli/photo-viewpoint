"""Layer creation with an explicit CRS and a new dataset or temporary storage."""
from .i18n import tr
from pathlib import Path
from qgis.PyQt.QtCore import QStandardPaths
from qgis.PyQt.QtWidgets import (QDialog,QVBoxLayout,QFormLayout,QComboBox,QLineEdit,
 QPushButton,QHBoxLayout,QWidget,QDialogButtonBox,QFileDialog,QMessageBox)
from qgis.core import QgsProject,QgsVectorFileWriter,QgsUnitTypes,QgsVectorLayer
from qgis.gui import QgsProjectionSelectionWidget

FORMATS=[('GeoPackage','GPKG','.gpkg'),('ESRI Shapefile','ESRI Shapefile','.shp'),
         ('SQLite','SQLite','.sqlite'),('FlatGeobuf','FlatGeobuf','.fgb')]


def available_drivers():
    return {entry.driverName for entry in QgsVectorFileWriter.supportedFiltersAndFormats()}


def write_dataset(source,name,driver,path):
    path=Path(path)
    if path.exists():raise ValueError(tr('A dataset with this name already exists. Choose a different name.'))
    options=QgsVectorFileWriter.SaveVectorOptions()
    options.driverName=driver
    options.fileEncoding='UTF-8'
    options.layerName=name
    options.actionOnExistingFile=QgsVectorFileWriter.CreateOrOverwriteFile
    result=QgsVectorFileWriter.writeAsVectorFormatV3(source,str(path),QgsProject.instance().transformContext(),options)
    if result[0]!=QgsVectorFileWriter.NoError:
        raise ValueError(str(result[1]))
    filename=result[2] or str(path)
    table=result[3] or name
    uri=filename+('|layername='+table if driver in ('GPKG','SQLite') else '')
    layer=QgsVectorLayer(uri,name,'ogr')
    if not layer.isValid():raise ValueError(tr('The new dataset could not be opened: ')+filename)
    missing=[field.name() for field in source.fields() if layer.fields().indexFromName(field.name())<0]
    if missing:raise ValueError('The output format did not preserve these fields: '+', '.join(missing))
    return layer


class CreateLayerDialog(QDialog):
    def __init__(self,parent):
        super().__init__(parent)
        self.setWindowTitle(tr('Create photo viewpoint layer'))
        self.resize(600,260)
        outer=QVBoxLayout(self);form=QFormLayout()
        self.name=QLineEdit(tr('Photo viewpoint'),self)
        self.format=QComboBox(self)
        self.format.addItem(tr('Temporary layer'),('memory',''))
        available=available_drivers()
        for title,driver,extension in FORMATS:
            if driver in available:self.format.addItem(title,(driver,extension))
        self.crs=QgsProjectionSelectionWidget(self)
        self.crs.setCrs(QgsProject.instance().crs())
        project=QgsProject.instance()
        default=str(Path(project.fileName()).parent) if project.fileName() else project.homePath()
        self.directory=QLineEdit(default or QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation),self)
        browse=QPushButton(tr('Browse…'),self)
        browse.clicked.connect(self.browse)
        row=QWidget(self);h=QHBoxLayout(row);h.setContentsMargins(0,0,0,0)
        h.addWidget(self.directory);h.addWidget(browse)
        self.path_row=row
        form.addRow(tr('Layer / file name:'),self.name)
        form.addRow(tr('Storage format:'),self.format)
        form.addRow(tr('Coordinate reference system (metres):'),self.crs)
        form.addRow(tr('Directory:'),row)
        outer.addLayout(form)
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel,self)
        buttons.button(QDialogButtonBox.Ok).setText('OK')
        buttons.button(QDialogButtonBox.Cancel).setText('Cancel')
        buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)
        self.format.currentIndexChanged.connect(self.update_storage)
        self.update_storage()

    def update_storage(self,*args):
        self.path_row.setEnabled(self.format.currentData()[0]!='memory')

    def browse(self):
        value=QFileDialog.getExistingDirectory(self,tr('Choose output directory'),self.directory.text())
        if value:self.directory.setText(value)

    def values(self):
        name=self.name.text().strip()
        driver,extension=self.format.currentData()
        path=Path(self.directory.text().strip())/(name+extension) if driver!='memory' else None
        return name,self.crs.crs(),driver,path

    def accept(self):
        name,crs,driver,path=self.values()
        if not name or any(c in name for c in '/\\:*?"<>|') or name in ('.','..'):
            QMessageBox.warning(self,tr('Photo viewpoint'),tr('Enter a valid layer and file name.'));return
        if not crs.isValid() or crs.isGeographic() or crs.mapUnits()!=QgsUnitTypes.DistanceMeters:
            QMessageBox.warning(self,tr('Photo viewpoint'),tr('Choose a projected CRS with metre units.'));return
        if path is not None:
            if not path.parent.is_dir():
                QMessageBox.warning(self,tr('Photo viewpoint'),tr('Choose an existing directory.'));return
            candidates=[path]+([path.with_suffix(s) for s in ('.dbf','.shx','.prj','.cpg')] if driver=='ESRI Shapefile' else [])
            if any(p.exists() for p in candidates):
                QMessageBox.warning(self,tr('Photo viewpoint'),tr('A dataset with this name already exists. Choose a different name.'));return
        super().accept()
