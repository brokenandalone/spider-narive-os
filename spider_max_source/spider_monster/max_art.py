"""Art Lab: read-only painting/wallpaper indexing and duplicate studies."""
from __future__ import annotations
from collections import Counter,defaultdict
from .max_core import *
EXT={'.png','.jpg','.jpeg','.bmp','.gif','.webp'}

def _dimensions(p):
    try:
        from PIL import Image
        with Image.open(p) as im:return im.size,im.mode
    except (OSError,ImportError,ValueError):return (None,None)

def run(action,root,query=''):
    root=selected(root);files=discover(root,EXT,450);data={}
    if action in ('gallery','wallpaper-readiness','portrait-review','resolution-groups','thumbnail-plan'):
        items=[]
        for p in files:
            dimensions,mode=_dimensions(p)
            x,y=dimensions or (0,0)
            items.append({'file':rel(root,p),'width':x or None,'height':y or None,'orientation':'landscape' if x>y else 'portrait' if y>x else 'square','mode':mode})
        if action=='wallpaper-readiness':data={'landscape_16_9':[i['file'] for i in items if i['width'] and i['height'] and abs(i['width']/i['height']-16/9)<.025],'undersized':[i['file'] for i in items if i['width'] and i['width']<1280]}
        elif action=='portrait-review':data={'portraits':[i for i in items if i['orientation']=='portrait']}
        elif action=='resolution-groups':data={'sizes':dict(Counter(f"{i['width']}x{i['height']}" for i in items))}
        elif action=='thumbnail-plan':data={'suggested':[{'file':i['file'],'max_output':(600,600)} for i in items[:100]],'no_files_written':True}
        else:data={'images':items}
    elif action=='name-review':
        data={'generic_names':[rel(root,p) for p in files if re.match(r'(?i)(?:image|img|pic|untitled|screenshot|download|dsc)[_ -]?\d*',p.stem)][:180]}
    elif action=='exact-duplicates':
        hits=defaultdict(list)
        for p in files:
            h=digest_file(p)
            if h:hits[h].append(rel(root,p))
        data={'groups':[{'sha256':h,'files':v} for h,v in hits.items() if len(v)>1]}
    elif action=='asset-inventory':
        data={'count':len(files),'formats':dict(Counter(p.suffix.lower() for p in files)),'total_bytes':sum(p.stat().st_size for p in files)}
    elif action=='broken-city-names':
        expected=['Shayna','Kayla','His Honor','Mercy Man','Shepherd','Hollow Man','Unbroken','Daniel','Eli']
        data={'named':{n:[rel(root,p) for p in files if n.replace(' ','').lower() in re.sub('[^a-z]','',p.stem.lower())][:40] for n in expected},'note':'Name detection by filename only. Approval needed for actual character labels.'}
    else:raise ValueError('Unsupported Art operation')
    return standard_result('Art Lab',action,root,data)
ACTIONS=('gallery','wallpaper-readiness','portrait-review','resolution-groups','thumbnail-plan','name-review','exact-duplicates','asset-inventory','broken-city-names')
