"""Portable native-QGIS styles. SVG artwork is embedded in QML as base64."""
import base64,re
from pathlib import Path
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import (QDialog,QVBoxLayout,QFormLayout,QComboBox,QDoubleSpinBox,
 QDialogButtonBox,QLabel,QCheckBox,QPushButton,QFileDialog)
from qgis.core import (QgsMarkerSymbol,QgsSvgMarkerSymbolLayer,QgsProperty,
 QgsGeometryGeneratorSymbolLayer,QgsLineSymbol,QgsFillSymbol,QgsUnitTypes,
 QgsSingleSymbolRenderer,QgsPalLayerSettings,Qgis,QgsTextFormat,QgsTextBufferSettings,
 QgsVectorLayerSimpleLabeling,QgsProviderRegistry)
from .schema import field_name,configure_table

CAMERA='''<svg xmlns="http://www.w3.org/2000/svg" viewBox="-20 -20 40 40"><rect x="-14" y="7" width="28" height="11" rx="3" fill="#354c5a" stroke="#152e3b" stroke-width="1.2"/><rect x="-6" y="0" width="12" height="9" rx="1" fill="#8bbbd2" stroke="#152e3b" stroke-width="1.2"/><path d="M-6 1H6M-6 4H6" stroke="#e7f6fc" stroke-width="1.4"/><rect x="8" y="5" width="5" height="3" fill="#d75c3a"/></svg>'''
ARROW='''<svg xmlns="http://www.w3.org/2000/svg" viewBox="-20 -20 40 40"><circle r="11" fill="#eef8fb" stroke="#226f97" stroke-width="2"/><path d="M0-19 9-5H3V9H-3V-5H-9Z" fill="#226f97"/></svg>'''
PRESETS=[('classic','Classic point and rays'),('camera','Top-view camera and dashed blue rays'),
         ('arrow','Circle and bearing arrow (no FOV)'),('sector','Point and translucent field of view')]
RAYS='''collect_geometries(make_line($geometry,project($geometry,"distance",radians("azimuth"-"fov"/2.0))),make_line($geometry,project($geometry,"distance",radians("azimuth"+"fov"/2.0))))'''


def apply_style(layer,preset='classic',size=4,labels=True):
    if preset not in dict(PRESETS):preset='classic'
    if preset in ('camera','arrow'):
        artwork=CAMERA if preset=='camera' else ARROW
        path='base64:'+base64.b64encode(artwork.encode()).decode()
        marker=QgsMarkerSymbol([QgsSvgMarkerSymbolLayer(path,size)])
        marker.setDataDefinedAngle(QgsProperty.fromField('azimuth'))
    else:
        marker=QgsMarkerSymbol.createSimple({'name':'circle','color':'220,75,35','size':str(size)})
    if preset!='arrow':
        if preset=='sector':
            gen=QgsGeometryGeneratorSymbolLayer.create({'geometryModifier':'wedge_buffer($geometry,"azimuth","fov","distance")','SymbolType':'Fill'})
            gen.setSubSymbol(QgsFillSymbol.createSimple({'color':'50,135,205,45','outline_style':'no'}))
        else:
            gen=QgsGeometryGeneratorSymbolLayer.create({'geometryModifier':RAYS,'SymbolType':'Line'})
            gen.setSubSymbol(QgsLineSymbol.createSimple({'line_color':'60,155,210' if preset=='camera' else '220,75,35',
                'line_width':'0.22' if preset=='camera' else '0.35','line_style':'dash' if preset=='camera' else 'solid'}))
        gen.setUnits(QgsUnitTypes.RenderMapUnits)
        marker.insertSymbolLayer(0,gen)
    layer.setRenderer(QgsSingleSymbolRenderer(marker))
    settings=QgsPalLayerSettings();settings.fieldName=field_name(layer,'code')
    settings.placement=Qgis.LabelPlacement.OrderedPositionsAroundPoint;settings.dist=2
    fmt=QgsTextFormat();fmt.setSize(10);fmt.setColor(QColor('black'))
    buffer=QgsTextBufferSettings();buffer.setEnabled(True);buffer.setSize(.8);buffer.setColor(QColor('white'))
    fmt.setBuffer(buffer);settings.setFormat(fmt)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(settings));layer.setLabelsEnabled(labels)
    layer.setCustomProperty('photo_viewpoint/preset',preset)
    layer.setCustomProperty('photo_viewpoint/size',size)
    configure_table(layer);layer.triggerRepaint()


def style_paths(path,table=''):
    path=Path(path)
    if path.suffix.lower() in ('.gpkg','.sqlite'):
        suffix=re.sub(r'[^\w-]+','_',table or 'viewpoints')
        return path.with_name(path.stem+'__'+suffix+'.qml')
    return path.with_suffix('.qml')


def save_portable_style(layer):
    if layer.providerType()=='memory':return ['Temporary layer: save the project or export a dataset before saving a sidecar style.']
    info=QgsProviderRegistry.instance().decodeUri(layer.providerType(),layer.source())
    path=info.get('path')
    if not path or not Path(path).is_file():return ['No local dataset path was found. Use Save QML to choose a location.']
    target=style_paths(path,info.get('layerName') or info.get('layername') or layer.name())
    message,ok=layer.saveNamedStyle(str(target))
    if not ok:raise ValueError('Could not save QML style: '+str(message))
    result=['QML saved: '+str(target)]
    if Path(path).suffix.lower() in ('.gpkg','.sqlite'):
        try:
            error=layer.saveStyleToDatabase('Photo viewpoint','Portable viewpoint style and field configuration',True,'')
            if error:result.append('Database default style was not saved: '+str(error)+'. Load the QML sidecar manually.')
            else:result.append('Default style saved inside the dataset.')
        except Exception as error:result.append('Database style unavailable: '+str(error)+'. Load the QML sidecar manually.')
    return result


class StyleDialog(QDialog):
    def __init__(self,parent,layer,copy_callback):
        super().__init__(parent)
        self.setWindowTitle('Apply viewpoint style');self.resize(570,300)
        outer=QVBoxLayout(self);form=QFormLayout()
        self.preset=QComboBox(self)
        for key,title in PRESETS:self.preset.addItem(title,key)
        index=self.preset.findData(layer.customProperty('photo_viewpoint/preset','classic'))
        self.preset.setCurrentIndex(max(0,index))
        self.size=QDoubleSpinBox(self);self.size.setRange(.5,30);self.size.setSuffix(' mm')
        self.size.setValue(float(layer.customProperty('photo_viewpoint/size',4)))
        form.addRow('Symbol:',self.preset);form.addRow('Symbol size:',self.size);outer.addLayout(form)
        self.labels=QCheckBox('Show code labels',self);self.labels.setChecked(layer.labelsEnabled());outer.addWidget(self.labels)
        self.persist=QCheckBox('Save a reusable QML / database default style',self);self.persist.setChecked(True);outer.addWidget(self.persist)
        note=QLabel('The arrow preset uses azimuth only. Other presets use FOV and graphic length.\nStyles contain native QGIS expressions and embedded SVG artwork.\nSave layer edits before saving a database default style.\nExisting datasets keep their physical field names; use an English-schema copy to convert them.',self)
        note.setWordWrap(True);outer.addWidget(note)
        copy=QPushButton('Create English-field GeoPackage copy…',self);copy.clicked.connect(copy_callback);outer.addWidget(copy)
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel,self)
        buttons.button(QDialogButtonBox.Ok).setText('OK')
        buttons.button(QDialogButtonBox.Cancel).setText('Cancel')
        buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);outer.addWidget(buttons)
