"""Offline image-to-ink outline for Spider Art Lab reference PNG layers.

The raster is scaled to at most 720 pixels on its long edge, reducing memory
and avoiding multi-second full-resolution pixel algorithms in the Qt editor.
This is a simple configurable luminance edge trace, not semantic segmentation.
No network, generative model or image file overwrites are involved.
"""
from __future__ import annotations
import struct

from PyQt5.QtCore import QByteArray,QBuffer,QIODevice,Qt
from PyQt5.QtGui import QImage,QColor
try:
    from .project import ArtError,MAX_IMAGE_BYTES
except ImportError:
    from project import ArtError,MAX_IMAGE_BYTES

def photo_outline(png, *, threshold=36, max_side=720):
    if not isinstance(png,bytes) or not 24<=len(png)<=MAX_IMAGE_BYTES:
        raise ArtError("A real PNG reference image is required")
    if not png.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ArtError("Outline tracing only accepts PNG image data")
    width,height=struct.unpack(">II",png[16:24])
    if not 1<=width<=4096 or not 1<=height<=4096:
        raise ArtError("Reference image dimensions are unsafe")
    if type(threshold) is not int or not 8<=threshold<=150:
        raise ArtError("Outline threshold must be from 8 to 150")
    if type(max_side) is not int or not 64<=max_side<=720:
        raise ArtError("Outline preview must remain safely bounded")
    img=QImage.fromData(png,"PNG")
    if img.isNull():
        raise ArtError("Cannot decode reference PNG")
    if max(width,height)>max_side:
        img=img.scaled(max_side,max_side,Qt.KeepAspectRatio,
                       Qt.SmoothTransformation)
    img=img.convertToFormat(QImage.Format_RGB32)
    w,h=img.width(),img.height()
    grayscale=[]
    for y in range(h):
        row=[]
        for x in range(w):
            px=img.pixelColor(x,y)
            row.append((54*px.red()+183*px.green()+19*px.blue())//256)
        grayscale.append(row)
    result=QImage(w,h,QImage.Format_ARGB32)
    result.fill(Qt.transparent)
    for y in range(1,h-1):
        top,mid,lower=grayscale[y-1],grayscale[y],grayscale[y+1]
        for x in range(1,w-1):
            gx=(top[x+1]-top[x-1]+2*(mid[x+1]-mid[x-1])
                +lower[x+1]-lower[x-1])
            gy=(lower[x-1]-top[x-1]+2*(lower[x]-top[x])
                +lower[x+1]-top[x+1])
            strength=min(255,(abs(gx)+abs(gy))//4)
            if strength>=threshold:
                result.setPixelColor(x,y,QColor(18,11,28,
                                                min(255,strength+60)))
    data=QByteArray()
    writer=QBuffer(data)
    if not writer.open(QIODevice.WriteOnly) or not result.save(writer,"PNG"):
        raise ArtError("Could not encode outlined reference")
    writer.close()
    output=bytes(data)
    if not output.startswith(b"\x89PNG\r\n\x1a\n") or len(output)>MAX_IMAGE_BYTES:
        raise ArtError("Outline exceeded bounded PNG size")
    return output
