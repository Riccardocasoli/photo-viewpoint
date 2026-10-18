"""Regression checks for documented native API return shapes and edit isolation.

These doubles do not replace the included real-QGIS storage smoke test.
"""
import ast,tempfile,unittest
from pathlib import Path

ROOT=Path(__file__).parent


def function(filename,name,namespace,cls=None):
    tree=ast.parse((ROOT/filename).read_text())
    nodes=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==cls).body if cls else tree.body
    node=next(n for n in nodes if isinstance(n,ast.FunctionDef) and n.name==name)
    exec(compile(ast.Module(body=[node],type_ignores=[]),'regression','exec'),namespace)
    return namespace[name]


class StorageContracts(unittest.TestCase):
    def test_driver_details_are_a_list_not_a_dictionary(self):
        class Detail:
            def __init__(self,name):self.driverName=name
        class Writer:
            @staticmethod
            def supportedFiltersAndFormats():return [Detail('GPKG'),Detail('ESRI Shapefile')]
        get=function('create_layer_dialog.py','available_drivers',{'QgsVectorFileWriter':Writer})
        self.assertEqual(get(),{'GPKG','ESRI Shapefile'})

    def test_writer_v3_outputs_and_provider_layer_name(self):
        class Field:
            def name(self):return 'code'
        class Fields:
            def indexFromName(self,name):return 0
        class Source:
            def fields(self):return [Field()]
        class Loaded:
            def __init__(self,uri,name,provider):self.uri=uri
            def isValid(self):return True
            def fields(self):return Fields()
        class Options:pass
        class Writer:
            SaveVectorOptions=Options;CreateOrOverwriteFile=0;NoError=0
            @staticmethod
            def writeAsVectorFormatV3(source,path,context,options):return 0,'',path,'laundered_name'
        class Project:
            @staticmethod
            def instance():return Project()
            def transformContext(self):return None
        save=function('create_layer_dialog.py','write_dataset',{'Path':Path,'QgsVectorFileWriter':Writer,'QgsProject':Project,'QgsVectorLayer':Loaded,'tr':lambda s:s})
        with tempfile.TemporaryDirectory() as folder:
            layer=save(Source(),'Photo viewpoint','SQLite',Path(folder)/'photo.sqlite')
            self.assertTrue(layer.uri.endswith('|layername=laundered_name'))
            existing=Path(folder)/'exists.gpkg';existing.write_bytes(b'data')
            with self.assertRaises(ValueError):save(Source(),'Photo viewpoint','GPKG',existing)
            self.assertEqual(existing.read_bytes(),b'data')

    def test_image_replacement_updates_only_photo_and_metadata(self):
        metadata={'gps_lat':45.5,'gps_lon':9.25,'exif_stat':'ok'}
        class Feature:
            def isValid(self):return True
        class Fields:
            names=['photo']+list(metadata)
            def indexFromName(self,name):return self.names.index(name)
        class Layer:
            def __init__(self,fail=False):self.changes={};self.fail=fail;self.done=False;self.rollback=False
            def getFeature(self,fid):return Feature()
            def readOnly(self):return False
            def isEditable(self):return True
            def fields(self):return Fields()
            def beginEditCommand(self,s):pass
            def changeAttributeValue(self,fid,index,value):self.changes[Fields.names[index]]=value;return not self.fail
            def endEditCommand(self):self.done=True
            def destroyEditCommand(self):self.rollback=True
            def triggerRepaint(self):pass
            def changeGeometry(self,*args):raise AssertionError('Geometry must never change')
        change=function('plugin.py','change_photo',{'photo_metadata':lambda layer,path:metadata,'add_metadata_fields':lambda layer:None,'tr':lambda s:s},'PhotoPlugin')
        layer=Layer();change(None,layer,1,'new.jpg')
        self.assertEqual(layer.changes,dict(metadata,photo='new.jpg'))
        self.assertTrue(layer.done)
        layer=Layer(True)
        with self.assertRaises(ValueError):change(None,layer,1,'new.jpg')
        self.assertTrue(layer.rollback);self.assertFalse(layer.done)

if __name__=='__main__':unittest.main()
