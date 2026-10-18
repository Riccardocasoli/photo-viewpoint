"""Numerical helpers for photo import; no QGIS dependency."""
import math
from pathlib import Path


def gps_position(metadata):
    x,y=metadata.get('gps_x'),metadata.get('gps_y')
    if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (x,y)):
        return None
    return x,y


def gps_distance(position,metadata):
    gps=gps_position(metadata)
    if position is None or gps is None:return None
    return math.hypot(position[0]-gps[0],position[1]-gps[1])


def unique_code(path,used):
    base=Path(path).stem.strip() or 'Photo'
    base=base[:80]
    code=base;n=2
    while code in used:
        code=base+'_%d'%n;n+=1
    used.add(code)
    return code
