from .schema import field_name
import ast,math,unittest
from pathlib import Path
from .import_utils import gps_position,gps_distance,unique_code


class ImportTests(unittest.TestCase):
    def test_coordinates_and_nulls(self):
        self.assertEqual(gps_position({'gps_x':0.,'gps_y':0.}),(0.,0.))
        for meta in [{},{'gps_x':None,'gps_y':2},{'gps_x':float('nan'),'gps_y':2}]:
            self.assertIsNone(gps_position(meta));self.assertIsNone(gps_distance((3,4),meta))
        self.assertEqual(gps_distance((13,24),{'gps_x':10.,'gps_y':20.}),5)
        self.assertIsNone(gps_distance(None,{'gps_x':10.,'gps_y':20.}))

    def test_duplicate_names(self):
        used=set()
        self.assertEqual(unique_code('/a/photo.jpg',used),'photo')
        self.assertEqual(unique_code('/b/photo.jpg',used),'photo_2')
        self.assertEqual(unique_code('/c/photo.jpg',used),'photo_3')

    def test_actual_batch_method_geometryless_default_and_rollback(self):
        tree=ast.parse((Path(__file__).parent/'import_photos.py').read_text())
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='import_records')
        class Feature(dict):
            def __init__(self,fields):super().__init__();self.geometry=None
            def setGeometry(self,g):self.geometry=g
        class Geometry:
            @staticmethod
            def fromPointXY(p):return p
        class Layer:
            def __init__(self,fail=False):self.features=[];self.fail=fail;self.ended=False;self.destroyed=False
            def readOnly(self):return False
            def isEditable(self):return True
            def fields(self):return []
            def getFeatures(self):return self.features
            def beginEditCommand(self,s):pass
            def addFeature(self,f):self.features.append(f);return not (self.fail and len(self.features)==2)
            def endEditCommand(self):self.ended=True
            def destroyEditCommand(self):self.destroyed=True;self.features=[]
            def updateExtents(self):pass
            def triggerRepaint(self):pass
        ns={'QgsFeature':Feature,'QgsGeometry':Geometry,'QgsPointXY':lambda *p:p,
            'add_metadata_fields':lambda l:None,'gps_position':gps_position,'gps_distance':gps_distance,
            'unique_code':unique_code,'tr':lambda s:s,'field_name':field_name}
        exec(compile(ast.Module(body=[node],type_ignores=[]),'batch-regression','exec'),ns)
        records=[{'path':'/a/photo.jpg','metadata':{'gps_x':10.,'gps_y':20.},'azimuth':90.},
            {'path':'/b/photo.jpg','metadata':{'gps_x':None,'gps_y':None},'azimuth':None}]
        defaults={'azimuth':0.,'fov':40.,'distance':20.}
        layer=Layer()
        self.assertEqual(ns['import_records'](layer,records,defaults),(2,1))
        a,b=layer.features
        self.assertEqual(a.geometry,(10.,20.));self.assertEqual(a['distGPS'],0.)
        self.assertIsNone(b.geometry);self.assertIsNone(b['distGPS'])
        self.assertEqual(a['azimuth'],90.);self.assertEqual(b['azimuth'],0.)
        self.assertEqual(b['fov'],40.);self.assertEqual(b['distance'],20.)
        self.assertEqual(b['vp_status'],'needs_pos');self.assertEqual(b[field_name(b, 'code')],'photo_2')
        layer=Layer(True)
        with self.assertRaises(ValueError):ns['import_records'](layer,records,defaults)
        self.assertTrue(layer.destroyed);self.assertFalse(layer.ended);self.assertFalse(layer.features)

if __name__=='__main__':unittest.main()
