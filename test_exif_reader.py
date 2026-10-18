import math,struct,tempfile,unittest
from pathlib import Path
from .exif_reader import parse_exif,read_exif
from .i18n import translate


def fixture(order='<',latitude='N',longitude='E',zero_denominator=False):
    data=bytearray((b'II' if order=='<' else b'MM')+struct.pack(order+'HI',42,0))
    def ifd(entries):
        offset=len(data)
        data.extend(struct.pack(order+'H',len(entries))+b'\0'*(12*len(entries)+4))
        for i,(tag,kind,value) in enumerate(entries):
            if kind==2:raw=value.encode()+b'\0';count=len(raw)
            elif kind==1:raw=bytes([value]);count=1
            elif kind==4:raw=struct.pack(order+'I',value);count=1
            elif kind==5:
                raw=b''.join(struct.pack(order+'II',*v) for v in value);count=len(value)
            position=offset+2+12*i
            struct.pack_into(order+'HHI',data,position,tag,kind,count)
            if len(raw)<=4:data[position+8:position+12]=raw.ljust(4,b'\0')
            else:
                struct.pack_into(order+'I',data,position+8,len(data));data.extend(raw)
        return offset
    gps=ifd([(1,2,latitude),(2,5,[(45,1),(30,1),(0,1)]),
             (3,2,longitude),(4,5,[(9,1),(15,1),(0,1)]),(5,1,1),
             (6,5,[(125,0 if zero_denominator else 1)]),(16,2,'T'),(17,5,[(270,1)]),(18,2,'WGS-84')])
    exif=ifd([(0x9003,2,'2026:10:17 10:30:00')])
    main=ifd([(0x10f,2,'Test make'),(0x110,2,'Test camera'),(0x8825,4,gps),(0x8769,4,exif)])
    struct.pack_into(order+'I',data,4,main)
    return bytes(data)


class ExifTests(unittest.TestCase):
    def test_endianness_gps_altitude_heading(self):
        for order in ('<','>'):
            result=parse_exif(fixture(order))
            self.assertEqual(result['exif_stat'],'ok')
            self.assertEqual(result['gps_lat'],45.5)
            self.assertEqual(result['gps_lon'],9.25)
            self.assertEqual(result['gps_alt'],-125)
            self.assertEqual(result['gps_dir'],270)
            self.assertEqual(result['gps_dref'],'T')
            self.assertEqual(result['exif_date'],'2026:10:17 10:30:00')
            self.assertIn('Test camera',result['exif_cam'])

    def test_south_west_and_unknown_ref(self):
        result=parse_exif(fixture(latitude='S',longitude='W'))
        self.assertEqual(result['gps_lat'],-45.5);self.assertEqual(result['gps_lon'],-9.25)
        self.assertIsNone(parse_exif(fixture(latitude='?'))['gps_lat'])

    def test_zero_rational_is_not_fabricated(self):
        self.assertNotIn('gps_alt',parse_exif(fixture(zero_denominator=True)))

    def test_jpeg_tiff_missing_and_corrupt(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'test.jpg'
            payload=b'Exif\0\0'+fixture()
            p.write_bytes(b'\xff\xd8\xff\xe1'+struct.pack('>H',len(payload)+2)+payload+b'\xff\xd9')
            self.assertEqual(read_exif(p)['gps_lat'],45.5)
            p.write_bytes(fixture('>'))
            self.assertEqual(read_exif(p)['gps_dir'],270)
            p.write_bytes(b'\xff\xd8\xff\xd9')
            self.assertEqual(read_exif(p)['exif_stat'],'no_exif')
            p.write_bytes(b'II*\0\xff\xff\xff\x7f')
            self.assertEqual(read_exif(p)['exif_stat'],'unreadable')
            self.assertEqual(read_exif(Path(directory)/'missing.jpg')['exif_stat'],'unreadable')

    def test_translation_and_stable_brand(self):
        self.assertEqual(translate('Crea layer foto','en'),'Create photo layer')
        self.assertEqual(translate('Create photo viewpoint layer','it'),'Crea layer punti di presa fotografica')
        self.assertEqual(translate('Prese fotografiche','it'),'Photo viewpoint')
        self.assertEqual(translate('Nuova presa','fr'),'New viewpoint')

if __name__=='__main__':unittest.main()
