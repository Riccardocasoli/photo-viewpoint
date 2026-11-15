"""Optional metadata columns, all names compatible with Shapefile's limit."""
from .i18n import tr
from .compat import FIELD_STRING, FIELD_DOUBLE
from qgis.core import QgsField,QgsProject,QgsCoordinateReferenceSystem,QgsCoordinateTransform,QgsPointXY,QgsDefaultValue,QgsDistanceArea
import math
from .exif_reader import read_exif
from .photo_paths import resolve_photo
from .schema import configure_table

METADATA_FIELDS={'gps_lat':FIELD_DOUBLE,'gps_lon':FIELD_DOUBLE,'gps_alt':FIELD_DOUBLE,
 'gps_dir':FIELD_DOUBLE,'gps_x':FIELD_DOUBLE,'gps_y':FIELD_DOUBLE,
 'gps_dref':FIELD_STRING,'gps_datum':FIELD_STRING,'exif_date':FIELD_STRING,
 'exif_cam':FIELD_STRING,'exif_stat':FIELD_STRING}


def add_metadata_fields(layer):
    for name,kind in METADATA_FIELDS.items():
        idx=layer.fields().indexFromName(name)
        if idx>=0:
            if layer.fields().field(idx).type()!=kind:
                raise ValueError(tr('Metadata field has an incompatible type: ')+name)
        elif not layer.addAttribute(QgsField(name,kind,len=100) if kind==FIELD_STRING else QgsField(name,kind,len=24,prec=10)):
            raise ValueError(tr('Cannot add metadata field: ')+name)
    for name,kind in [('distGPS',FIELD_DOUBLE),('vp_status',FIELD_STRING)]:
        idx=layer.fields().indexFromName(name)
        if idx<0:
            if not layer.addAttribute(QgsField(name,kind,len=24,prec=3) if kind==FIELD_DOUBLE else QgsField(name,kind,len=24)):
                raise ValueError(tr('Cannot add metadata field: ')+name)
        elif layer.fields().field(idx).type()!=kind:
            raise ValueError(tr('Metadata field has an incompatible type: ')+name)
    configure_tracking(layer)
    configure_table(layer)


def configure_tracking(layer):
    if all(layer.fields().indexFromName(n)>=0 for n in ('distGPS','gps_x','gps_y')):
        expression='CASE WHEN $geometry IS NULL OR is_empty($geometry) OR "gps_x" IS NULL OR "gps_y" IS NULL THEN NULL ELSE distance($geometry, make_point("gps_x", "gps_y")) END'
        layer.setDefaultValueDefinition(layer.fields().indexFromName('distGPS'),QgsDefaultValue(expression,True))
    idx=layer.fields().indexFromName('vp_status')
    if idx>=0:
        layer.setDefaultValueDefinition(idx,QgsDefaultValue("CASE WHEN $geometry IS NULL OR is_empty($geometry) THEN 'needs_pos' ELSE 'positioned' END",True))


def grid_azimuth(layer,metadata):
    if metadata.get('gps_dref')!='T' or metadata.get('gps_dir') is None or metadata.get('gps_lat') is None or metadata.get('gps_lon') is None:
        return None
    if metadata.get('exif_stat') not in ('ok',):return None
    try:
        area=QgsDistanceArea();area.setEllipsoid('WGS84')
        origin=QgsPointXY(metadata['gps_lon'],metadata['gps_lat'])
        target=area.computeSpheroidProject(origin,100,math.radians(metadata['gps_dir']))
        tx=QgsCoordinateTransform(QgsCoordinateReferenceSystem('EPSG:4326'),layer.crs(),QgsProject.instance())
        a,b=tx.transform(origin),tx.transform(target)
        return math.degrees(math.atan2(b.x()-a.x(),b.y()-a.y()))%360
    except Exception:return None


def photo_metadata(layer,reference):
    result={name:None for name in METADATA_FIELDS}
    if not reference:
        result['exif_stat']='empty';return result
    try:
        path,remote=resolve_photo(reference,QgsProject.instance().fileName(),layer.source())
        result.update({'exif_stat':'remote'} if remote else read_exif(path))
        if result['gps_lat'] is not None and result['gps_lon'] is not None:
            datum=(result['gps_datum'] or 'WGS84').upper().replace('-','').replace(' ','')
            if datum in ('WGS84','WGS1984'):
                transform=QgsCoordinateTransform(QgsCoordinateReferenceSystem('EPSG:4326'),layer.crs(),QgsProject.instance())
                point=transform.transform(QgsPointXY(result['gps_lon'],result['gps_lat']))
                result['gps_x'],result['gps_y']=point.x(),point.y()
            else:result['exif_stat']='datum_unknown'
    except Exception:
        # Linking an image must remain possible even if its metadata is damaged.
        result['exif_stat']='unreadable'
    return result
