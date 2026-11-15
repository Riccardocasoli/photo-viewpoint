"""Run in QGIS console: import prese_fotografiche.smoke_test_styles as t; t.run()."""
import tempfile
from pathlib import Path
from .compat import FIELD_STRING, FIELD_DOUBLE
from qgis.core import QgsVectorLayer,QgsField,QgsFeature,QgsGeometry,QgsPointXY,QgsExpression
from .plugin import FIELDS
from .schema import preferred_names
from .viewpoint_styles import apply_style,save_portable_style,PRESETS
from .create_layer_dialog import write_dataset,available_drivers
from .english_copy import make_english_copy


def run():
    layer=QgsVectorLayer('Point?crs=EPSG:32632','Styles test','memory')
    definitions={'code':FIELD_STRING,'caption':FIELD_STRING,'distGPS':FIELD_DOUBLE,**{k:v for k,v in FIELDS.items() if k!='code'}}
    layer.dataProvider().addAttributes([QgsField(n,k,len=2000) if n=='caption' else QgsField(n,k) for n,k in definitions.items()]);layer.updateFields()
    assert [f.name() for f in layer.fields()][:3]==['code','caption','distGPS']
    for preset,title in PRESETS:
        apply_style(layer,preset,6,True)
        assert layer.renderer().symbol().symbolLayerCount()==(1 if preset=='arrow' else 2)
        assert layer.labeling().settings().fieldName=='code'
        if preset!='arrow':
            expr=QgsExpression(layer.renderer().symbol().symbolLayer(0).geometryExpression())
            assert not expr.hasParserError(),expr.parserErrorString()
    with tempfile.TemporaryDirectory() as directory:
        for driver,extension in [('GPKG','.gpkg'),('ESRI Shapefile','.shp')]:
            if driver not in available_drivers():continue
            # A Shapefile cannot promise a 2000-character string; test safe field lengths.
            source=layer
            if driver=='ESRI Shapefile':
                source=QgsVectorLayer('Point?crs=EPSG:32632','Shapefile test','memory')
                source.dataProvider().addAttributes([QgsField(n,k,len=254) if k==FIELD_STRING else QgsField(n,k) for n,k in definitions.items()]);source.updateFields()
            path=Path(directory)/('styles'+extension)
            output=write_dataset(source,'styles',driver,path)
            apply_style(output,'camera',6,True)
            report=save_portable_style(output)
            assert any('QML saved:' in s for s in report)
            if driver=='ESRI Shapefile':assert path.with_suffix('.qml').is_file()
            loaded=QgsVectorLayer(output.source(),'Reloaded style','ogr')
            assert loaded.isValid()
            assert loaded.renderer().symbol().symbolLayerCount()==2
            assert loaded.labeling().settings().fieldName=='code'
            output=None;loaded=None
        old=QgsVectorLayer('Point?crs=EPSG:32632','Legacy','memory')
        old.dataProvider().addAttributes([QgsField('codice',FIELD_STRING),QgsField('Didascalia',FIELD_STRING,len=254),QgsField('azimuth',FIELD_DOUBLE),QgsField('fov',FIELD_DOUBLE),QgsField('distance',FIELD_DOUBLE),QgsField('photo',FIELD_STRING),QgsField('note',FIELD_STRING)])
        old.updateFields();f=QgsFeature(old.fields());f['codice']='A';f['Didascalia']='Original text';f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(500000,5000000)))
        assert old.dataProvider().addFeatures([f])[0]
        copied=make_english_copy(old,Path(directory)/'english.gpkg')
        assert [f.name() for f in copied.fields() if f.name()!='fid'][:3]==['code','caption','distGPS']
        assert copied.fields().indexFromName('codice')<0 and old.fields().indexFromName('codice')>=0
        assert next(copied.getFeatures())['caption']=='Original text'
        copied=None
    print('Style persistence and English-schema copy smoke test: OK')
