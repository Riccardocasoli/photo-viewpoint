"""Inside QGIS: import prese_fotografiche.smoke_test_storage as t; t.run(iface)."""
from .schema import field_name
import tempfile
from pathlib import Path
from qgis.PyQt.QtCore import QVariant
from qgis.core import QgsVectorLayer,QgsField,QgsFeature,QgsGeometry,QgsPointXY
from .create_layer_dialog import write_dataset,available_drivers,FORMATS
from .plugin import PhotoPlugin,FIELDS
from .test_exif_reader import fixture
from .photo_metadata import METADATA_FIELDS


def run(iface):
    source=QgsVectorLayer('Point?crs=EPSG:32632','Photo viewpoint','memory')
    source.dataProvider().addAttributes([QgsField(n,t,len=254) if t==QVariant.String else QgsField(n,t,len=24,prec=10)
        for n,t in dict(FIELDS,**METADATA_FIELDS).items()])
    source.updateFields()
    with tempfile.TemporaryDirectory() as directory:
        exif=Path(directory)/'test.tif';exif.write_bytes(fixture())
        for title,driver,extension in FORMATS:
            if driver not in available_drivers():continue
            output=write_dataset(source,'Photo viewpoint',driver,Path(directory)/('test'+extension))
            assert output.isValid() and output.startEditing(),driver
            f=QgsFeature(output.fields())
            f[field_name(f, 'code')]='TEST';f['azimuth']=123.;f['fov']=60.;f['distance']=25.
            f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(500000,5000000)))
            assert output.addFeature(f)
            saved=next(output.getFeatures())
            before=saved.geometry().asWkt()
            PhotoPlugin(iface).change_photo(output,saved.id(),str(exif))
            saved=output.getFeature(saved.id())
            assert saved.geometry().asWkt()==before and saved['azimuth']==123.
            assert abs(saved['gps_lat']-45.5)<1e-8 and saved['gps_dir']==270
            assert output.commitChanges(),output.commitErrors()
            output=None
    print('Storage and metadata smoke test: OK')
