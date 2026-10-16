"""Spider Art Lab's versioned, private, non-destructive drawing project model.

A .spiderart project stores editable brush strokes and optional reference PNG
layers. PNG export happens separately in the Qt rendering layer. Everything
is local, with bounded parser allocations and create-new-only saves.
"""
from __future__ import annotations
import base64
import copy
import json
import math
import os
from pathlib import Path
import tempfile

VERSION = 1
MAX_SIDE = 4096
MAX_LAYERS = 32
MAX_STROKES = 12000
MAX_POINTS = 400000
MAX_PROJECT_BYTES = 25 * 1024 * 1024
MAX_IMAGE_BYTES = 8 * 1024 * 1024
TOOLS = ("pencil", "marker", "brush", "eraser")
class ArtError(ValueError):
    pass

def new_project(width=1600, height=900):
    if (type(width) is not int or type(height) is not int
            or not 64 <= width <= MAX_SIDE or not 64 <= height <= MAX_SIDE):
        raise ArtError("Canvas width and height must be 64–4096 pixels")
    return {"version":VERSION,"width":width,"height":height,
            "layers":[{"name":"Ink","visible":True,"strokes":[],
                       "image_png":None}],"active":0}

def _color(value):
    if (not isinstance(value,str) or len(value)!=9 or value[0]!="#"
            or any(c not in "0123456789abcdefABCDEF" for c in value[1:])):
        raise ArtError("A stroke needs an exact #RRGGBBAA color")
    return value.upper()

def create_stroke(points, *, tool="pencil", color="#E8E5FFFF", width=5):
    if tool not in TOOLS:
        raise ArtError("Invalid painting tool")
    if type(width) not in (int,float) or not math.isfinite(width) or not .5 <= width <= 128:
        raise ArtError("Brush width must be 0.5–128 pixels")
    if (not isinstance(points,(tuple,list)) or not 1<=len(points)<=8192):
        raise ArtError("A brush stroke needs 1–8192 coordinate pairs")
    cleaned=[]
    for item in points:
        if (not isinstance(item,(tuple,list)) or len(item)!=2
                or any(type(v) not in (int,float) or not math.isfinite(v)
                       or not -4096 <= v <= 8192 for v in item)):
            raise ArtError("Stroke coordinates must be finite and bounded")
        cleaned.append([round(float(item[0]),3),round(float(item[1]),3)])
    return {"tool":tool,"color":_color(color),"width":round(float(width),2),
            "points":cleaned}

def validate_project(value):
    if not isinstance(value,dict) or set(value)!={"version","width","height","layers","active"}:
        raise ArtError("Not a Spider Art Lab project")
    if value["version"]!=VERSION:
        raise ArtError("Unsupported Spider Art Lab project version")
    if (type(value["width"]) is not int or type(value["height"]) is not int
            or not 64<=value["width"]<=MAX_SIDE or not 64<=value["height"]<=MAX_SIDE):
        raise ArtError("Unsupported canvas dimensions")
    layers=value["layers"]
    if not isinstance(layers,list) or not 1<=len(layers)<=MAX_LAYERS:
        raise ArtError("Artwork needs 1–32 layers")
    if type(value["active"]) is not int or not 0<=value["active"]<len(layers):
        raise ArtError("Active painting layer is invalid")
    total_strokes=0
    total_points=0
    image_bytes=0
    for layer in layers:
        if not isinstance(layer,dict) or set(layer)!={"name","visible","strokes","image_png"}:
            raise ArtError("Unsupported layer data")
        name=layer["name"]
        if (not isinstance(name,str) or not 1<=len(name)<=70
                or any(ord(c)<32 for c in name)):
            raise ArtError("Invalid layer name")
        if type(layer["visible"]) is not bool:
            raise ArtError("Layer visibility must be true or false")
        strokes=layer["strokes"]
        if not isinstance(strokes,list):
            raise ArtError("Layer strokes must be a list")
        total_strokes+=len(strokes)
        if total_strokes>MAX_STROKES:
            raise ArtError("Project exceeds 12,000 strokes")
        for stroke in strokes:
            if not isinstance(stroke,dict) or set(stroke)!={"tool","color","width","points"}:
                raise ArtError("Invalid stroke data")
            clean=create_stroke(stroke["points"],tool=stroke["tool"],
                                color=stroke["color"],width=stroke["width"])
            if stroke!=clean:
                raise ArtError("Stroke values are not normalized")
            total_points+=len(stroke["points"])
            if total_points>MAX_POINTS:
                raise ArtError("Project exceeds 400,000 points")
        image=layer["image_png"]
        if image is not None:
            if not isinstance(image,str) or len(image)>MAX_IMAGE_BYTES*4//3+16:
                raise ArtError("Imported raster exceeds 8 MiB")
            try:
                data=base64.b64decode(image,validate=True)
            except (ValueError,base64.binascii.Error) as error:
                raise ArtError("Invalid base64 raster reference") from error
            if not data.startswith(b"\x89PNG\r\n\x1a\n") or len(data)>MAX_IMAGE_BYTES:
                raise ArtError("Raster layers must contain bounded PNG data")
            image_bytes+=len(data)
            if image_bytes>MAX_IMAGE_BYTES:
                raise ArtError("Combined embedded PNGs exceed 8 MiB")
    return value

def add_layer(project,name="New layer", *, image_png=None):
    validate_project(project)
    if len(project["layers"])>=MAX_LAYERS:
        raise ArtError("Art Lab supports at most 32 layers")
    next_layer={"name":name,"visible":True,"strokes":[],"image_png":image_png}
    candidate=copy.deepcopy(project)
    candidate["layers"].append(next_layer)
    candidate["active"]=len(candidate["layers"])-1
    return validate_project(candidate)

def append_stroke(project,stroke):
    validate_project(project)
    candidate=copy.deepcopy(project)
    candidate["layers"][candidate["active"]]["strokes"].append(stroke)
    return validate_project(candidate)

def _safe_source(path):
    p=Path(path).expanduser()
    if p.is_symlink() or not p.is_file() or p.suffix.lower()!=".spiderart":
        raise ArtError("Choose a local, regular .spiderart file")
    if p.stat().st_size>MAX_PROJECT_BYTES:
        raise ArtError("Project is larger than 25 MiB")
    return p

def open_project(path):
    source=_safe_source(path)
    try:
        with source.open("rb") as stream:
            data=stream.read(MAX_PROJECT_BYTES+1)
        if len(data)>MAX_PROJECT_BYTES:
            raise ArtError("Project is too large")
        return validate_project(json.loads(data.decode("utf-8")))
    except (json.JSONDecodeError,UnicodeError,OSError) as error:
        raise ArtError("Cannot open that Spider Art Lab project") from error

def save_project(path,project):
    validate_project(project)
    target=Path(path).expanduser()
    if target.exists() or target.is_symlink() or target.suffix.lower()!=".spiderart":
        raise ArtError("Choose a NEW .spiderart filename; existing artwork is protected")
    if not target.parent.is_dir() or target.parent.is_symlink():
        raise ArtError("Choose an existing local artwork folder")
    payload=(json.dumps(project,ensure_ascii=False,separators=(",",":"))+"\n").encode()
    if len(payload)>MAX_PROJECT_BYTES:
        raise ArtError("Artwork exceeds the safe project size")
    temporary=None
    try:
        fd,temporary=tempfile.mkstemp(prefix=".spider-art-",suffix=".part",
                                      dir=str(target.parent))
        os.fchmod(fd,0o600)
        with os.fdopen(fd,"wb") as file:
            file.write(payload)
            file.flush()
            os.fsync(file.fileno())
        if target.exists() or target.is_symlink():
            raise ArtError("Artwork file already exists")
        os.link(temporary,target,follow_symlinks=False)
    finally:
        if temporary:
            Path(temporary).unlink(missing_ok=True)
    return target
