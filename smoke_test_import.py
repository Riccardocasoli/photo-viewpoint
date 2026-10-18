"""Run inside QGIS console: import prese_fotografiche.smoke_test_import as t; t.run()."""
from .schema import field_name
from qgis.PyQt.QtCore import QVariant
from qgis.core import QgsVectorLayer,QgsField,QgsGeometry,QgsPointXY
from .plugin import FIELDS
from .import_photos import import_records


def run():
    layer=QgsVectorLayer('Point?crs=EPSG:32632','Photo import test','memory')
    layer.dataProvider().addAttributes([QgsField(n,t) for n,t in FIELDS.items()]);layer.updateFields()
    gps={'gps_x':500000.,'gps_y':5000000.,'gps_lat':45.,'gps_lon':9.,'gps_alt':100.,'gps_dir':90.,'gps_dref':'T','exif_stat':'ok'}
    records=[{'path':'/test/photo.jpg','metadata':gps,'azimuth':90.},
        {'path':'/test/noGPS.jpg','metadata':{'gps_x':None,'gps_y':None,'exif_stat':'no_gps'},'azimuth':None}]
    assert import_records(layer,records,{'azimuth':0.,'fov':40.,'distance':20.})==(2,1)
    features=list(layer.getFeatures())
    a=next(f for f in features if f[field_name(f, 'code')]=='photo')
    b=next(f for f in features if f[field_name(f, 'code')]=='noGPS')
    assert a['distGPS']==0 and b.geometry().isEmpty() and b['vp_status']=='needs_pos'
    layer.beginEditCommand('Test movement')
    assert layer.changeGeometry(a.id(),QgsGeometry.fromPointXY(QgsPointXY(500003,5000004)))
    layer.endEditCommand()
    moved=layer.getFeature(a.id())
    assert abs(moved['distGPS']-5)<1e-6
    for n in gps:assert moved[n]==a[n]
    layer.undoStack().undo()
    assert abs(layer.getFeature(a.id())['distGPS'])<1e-6
    assert layer.changeGeometry(b.id(),QgsGeometry.fromPointXY(QgsPointXY(500010,5000010)))
    placed=layer.getFeature(b.id())
    assert placed['vp_status']=='positioned'
    from qgis.core import NULL
    assert placed['distGPS']==NULL
    layer.rollBack()
    print('Photo import / distGPS smoke test: OK')
