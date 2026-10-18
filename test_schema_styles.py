import ast,re,unittest,xml.etree.ElementTree as ET
from pathlib import Path
from .schema import field_name,preferred_names,caption_length
from .i18n import tr


class SchemaTests(unittest.TestCase):
    def test_legacy_and_new_field_resolution(self):
        self.assertEqual(field_name({'codice':'a'},'code'),'codice')
        self.assertEqual(field_name({'code':'a'},'code'),'code')
        self.assertEqual(field_name({'Didascalia':'a'},'caption'),'Didascalia')
        self.assertEqual(field_name({'caption':'a','Didascalia':'b'},'caption'),'caption')
        self.assertEqual(field_name({},'code'),'code')

    def test_field_order_and_long_text_policy(self):
        self.assertEqual(preferred_names(['azimuth','photo','caption','distGPS','code']),['code','caption','distGPS','azimuth','photo'])
        self.assertEqual(preferred_names(['azimuth','Didascalia','distGPS','codice']),['codice','Didascalia','distGPS','azimuth'])
        self.assertGreaterEqual(caption_length('GPKG'),255)
        self.assertEqual(caption_length('ESRI Shapefile'),254)

    def test_ui_is_english(self):
        self.assertEqual(tr('Applica stile foto'),'Apply viewpoint style')
        self.assertEqual(tr('Crea layer foto'),'Create photo layer')

    def test_embedded_artwork_and_style_paths(self):
        tree=ast.parse((Path(__file__).parent/'viewpoint_styles.py').read_text())
        values={n.targets[0].id:ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('CAMERA','ARROW','PRESETS')}
        ET.fromstring(values['CAMERA']);ET.fromstring(values['ARROW'])
        self.assertEqual(len(values['PRESETS']),4)
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='style_paths')
        ns={'Path':Path,'re':re};exec(compile(ast.Module(body=[node],type_ignores=[]),'style-path-test','exec'),ns)
        self.assertEqual(str(ns['style_paths']('/tmp/photos.shp')),'/tmp/photos.qml')
        self.assertEqual(str(ns['style_paths']('/tmp/photos.gpkg','Camera layer')),'/tmp/photos__Camera_layer.qml')

if __name__=='__main__':unittest.main()
