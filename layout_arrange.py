"""Initial placement and aspect-fit sizes. Other layout items are irrelevant."""
from .i18n import tr
import math


def fit_size(pixel_width, pixel_height, max_width, max_height):
    values = (pixel_width,pixel_height,max_width,max_height)
    if not all(math.isfinite(v) and v>0 for v in values):
        raise ValueError(tr('Dimensioni immagine non valide.'))
    factor = min(max_width/pixel_width,max_height/pixel_height)
    return pixel_width*factor,pixel_height*factor


def caption_text(code, filename, description=''):
    title = ' — '.join(part for part in (code.strip(),filename.strip()) if part)
    return title + ('\n'+description.strip() if description.strip() else '')


def arrange(records, page, map_box=None, width=38, height=26, margin=8, gap=4):
    # map_box is intentionally ignored: images may overlap any layout element.
    left,top,right,bottom = page
    if not all(math.isfinite(v) for v in (*page,width,height,margin,gap)):
        raise ValueError(tr('Dimensioni non valide.'))
    if min(width,height,gap)<=0 or margin<0 or right<=left or bottom<=top:
        raise ValueError(tr('Dimensioni non valide.'))
    available=right-left-2*margin
    usable_height=bottom-top-2*margin
    if available<=0 or usable_height<=0:
        raise ValueError(tr('Margini troppo ampi per la pagina.'))
    slot_width=max([width]+[r.get('size',(width,height))[0] for r in records])
    columns=max(1,int((available+gap)//(slot_width+gap)))
    result=[]
    x,y,row_height=left+margin,top+margin,0
    for i,record in enumerate(sorted(records,key=lambda r:(r['anchor'][1],r['fid']))):
        w,h=record.get('size',(width,height))
        if i and i%columns==0:
            x=left+margin
            y+=row_height+gap
            row_height=0
        result.append(dict(record,box=(x,y,w,h)))
        x+=slot_width+gap
        row_height=max(row_height,h+record.get('caption_height',12))
    return result
