"""Bounded JPEG/TIFF EXIF reader using only Python's standard library.

No MakerNote/XMP parsing, remote requests or writes to original images.
"""
import math
import struct
from pathlib import Path

MAX_TIFF = 8*1024*1024


def tiff_payload(path):
    with open(path,'rb') as stream:
        head=stream.read(4)
        if head[:2] in (b'II',b'MM'):
            stream.seek(0)
            return stream.read(MAX_TIFF)
        if head[:2]!=b'\xff\xd8':
            return None
        stream.seek(2)
        scanned=2
        while scanned<MAX_TIFF:
            marker=stream.read(1);scanned+=1
            if not marker:break
            if marker!=b'\xff':return None
            while marker==b'\xff':
                marker=stream.read(1);scanned+=1
            if not marker or marker in (b'\xda',b'\xd9'):break
            if marker==b'\x01' or 0xd0<=marker[0]<=0xd7:continue
            raw=stream.read(2)
            if len(raw)!=2:return None
            length=struct.unpack('>H',raw)[0]
            if length<2:return None
            segment=stream.read(length-2);scanned+=length
            if len(segment)!=length-2:return None
            if marker==b'\xe1' and segment.startswith(b'Exif\0\0'):
                return segment[6:]
    return None


class Tiff:
    def __init__(self,data):
        self.data=data
        self.order='<' if data[:2]==b'II' else '>' if data[:2]==b'MM' else None
        if self.order is None or self.unpack('H',2)!=42:raise ValueError('Invalid TIFF')

    def unpack(self,fmt,offset):
        size=struct.calcsize(self.order+fmt)
        if offset<0 or offset+size>len(self.data):raise ValueError('TIFF offset outside payload')
        return struct.unpack_from(self.order+fmt,self.data,offset)[0]

    def ifd(self,offset):
        if not offset:return {}
        count=self.unpack('H',offset)
        if count>1024 or offset+2+12*count>len(self.data):raise ValueError('Invalid TIFF IFD')
        result={}
        sizes={1:1,2:1,3:2,4:4,5:8,7:1,9:4,10:8}
        for i in range(count):
            pos=offset+2+12*i
            tag=self.unpack('H',pos);kind=self.unpack('H',pos+2);n=self.unpack('I',pos+4)
            if kind not in sizes or n>65536:continue
            length=n*sizes[kind]
            start=pos+8 if length<=4 else self.unpack('I',pos+8)
            if start<0 or start+length>len(self.data):continue
            raw=self.data[start:start+length]
            if kind==2:value=raw.rstrip(b'\0').decode('utf-8','replace').strip()
            elif kind in (1,7):value=raw[0] if n==1 else tuple(raw)
            elif kind in (3,4,9):
                fmt={3:'H',4:'I',9:'i'}[kind]
                vals=[self.unpack(fmt,start+j*sizes[kind]) for j in range(n)]
                value=vals[0] if len(vals)==1 else tuple(vals)
            else:
                fmt='I' if kind==5 else 'i';vals=[]
                for j in range(n):
                    num=self.unpack(fmt,start+j*8);den=self.unpack(fmt,start+j*8+4)
                    vals.append(num/den if den else None)
                value=vals[0] if len(vals)==1 else tuple(vals)
            result[tag]=value
        return result


def dms(value,ref,positive,negative,limit):
    if not isinstance(value,tuple) or len(value)!=3 or ref not in (positive,negative):return None
    if not all(isinstance(v,(int,float)) and math.isfinite(v) and v>=0 for v in value):return None
    if value[1]>=60 or value[2]>=60:return None
    result=value[0]+value[1]/60+value[2]/3600
    if result>limit:return None
    return -result if ref==negative else result


def parse_exif(data):
    tiff=Tiff(data)
    main=tiff.ifd(tiff.unpack('I',4))
    exif=tiff.ifd(main.get(0x8769,0))
    gps=tiff.ifd(main.get(0x8825,0))
    out={'exif_stat':'no_gps'}
    out['exif_date']=exif.get(0x9003) or main.get(0x132)
    out['exif_cam']=' '.join(str(v) for v in [main.get(0x10f),main.get(0x110)] if v) or None
    out['gps_lat']=dms(gps.get(2),gps.get(1),'N','S',90)
    out['gps_lon']=dms(gps.get(4),gps.get(3),'E','W',180)
    altitude=gps.get(6)
    if isinstance(altitude,(int,float)) and math.isfinite(altitude) and gps.get(5) in (0,1):
        out['gps_alt']=-altitude if gps.get(5)==1 else altitude
    direction=gps.get(17)
    if isinstance(direction,(int,float)) and math.isfinite(direction) and 0<=direction<=360:
        out['gps_dir']=direction%360
        out['gps_dref']=gps.get(16)
    out['gps_datum']=gps.get(18)
    if out['gps_lat'] is not None and out['gps_lon'] is not None:out['exif_stat']='ok'
    return out


def read_exif(path):
    try:
        if not Path(path).is_file():return {'exif_stat':'unreadable'}
        data=tiff_payload(path)
        if data is None:return {'exif_stat':'no_exif'}
        return parse_exif(data)
    except (OSError,ValueError,TypeError,IndexError,struct.error,OverflowError):
        return {'exif_stat':'unreadable'}
