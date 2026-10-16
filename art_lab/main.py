"""Spider Art Lab: actual native editable painting workspace, not a launcher.

Vector stroke layers, opt-in PNG reference layers, pencil/paint/marker/eraser,
undo/redo, zoom, private versioned projects and create-new-only PNG exports.
The Web embeds SpiderArtLab directly inside its existing Art Lab bay.
"""
from __future__ import annotations

import base64
import copy
from datetime import datetime
import os
from pathlib import Path
import struct
import tempfile

from PyQt5.QtCore import Qt, QSize, QRect, QPointF
from PyQt5.QtGui import QColor, QPainter, QPainterPath, QPen, QBrush, QImage
from PyQt5.QtWidgets import (
    QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QComboBox,QSpinBox,
    QListWidget,QScrollArea,QSplitter,QFileDialog,QMessageBox,QColorDialog,
    QInputDialog,QFrame)
try:
    from .project import (
        ArtError,new_project,validate_project,add_layer,append_stroke,
        create_stroke,open_project,save_project,MAX_IMAGE_BYTES)
except ImportError:
    from project import (
        ArtError,new_project,validate_project,add_layer,append_stroke,
        create_stroke,open_project,save_project,MAX_IMAGE_BYTES)

ART_HOME=Path.home()/"Documents/Spider Art Lab"
PURPLE="#a78bfa"

def _brush_color(rgba):
    return QColor(*(int(rgba[i:i+2],16) for i in (1,3,5,7)))

def _draw_stroke(painter,stroke):
    painter.setRenderHint(QPainter.Antialiasing,True)
    color=_brush_color(stroke["color"])
    tool=stroke["tool"]
    if tool=="eraser":
        painter.setCompositionMode(QPainter.CompositionMode_Clear)
        color=QColor(0,0,0,255)
    else:
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
    if tool=="marker":
        color.setAlpha(min(color.alpha(),90))
    elif tool=="pencil":
        color.setAlpha(min(color.alpha(),200))
    painter.setPen(QPen(color,stroke["width"],Qt.SolidLine,
                        Qt.RoundCap,Qt.RoundJoin))
    points=stroke["points"]
    if len(points)==1:
        painter.drawPoint(QPointF(*points[0]))
    else:
        path=QPainterPath(QPointF(*points[0]))
        for x,y in points[1:]:
            path.lineTo(x,y)
        painter.drawPath(path)
    painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

def render_artwork(document):
    """Create a raster preview/export from exact editable layer sources."""
    validate_project(document)
    width,height=document["width"],document["height"]
    result=QImage(width,height,QImage.Format_ARGB32_Premultiplied)
    result.fill(Qt.transparent)
    composite=QPainter(result)
    try:
        for layer in document["layers"]:
            if not layer["visible"]:
                continue
            image=QImage(width,height,QImage.Format_ARGB32_Premultiplied)
            image.fill(Qt.transparent)
            painter=QPainter(image)
            try:
                if layer["image_png"]:
                    png=base64.b64decode(layer["image_png"])
                    raster=QImage.fromData(png,"PNG")
                    if raster.isNull():
                        raise ArtError("Imported PNG could not be rendered")
                    painter.drawImage(QRect(0,0,width,height),raster)
                for stroke in layer["strokes"]:
                    _draw_stroke(painter,stroke)
            finally:
                painter.end()
            composite.drawImage(0,0,image)
    finally:
        composite.end()
    return result

def export_artwork(path, document):
    """Export a NEW, verified PNG without modifying a project or existing art."""
    target=Path(path).expanduser()
    if target.suffix.lower()!=".png" or target.exists() or target.is_symlink():
        raise ArtError("Choose a new .png output filename; earlier paintings are protected")
    if not target.parent.is_dir() or target.parent.is_symlink():
        raise ArtError("PNG export needs a real, existing output folder")
    frame=render_artwork(document)
    tmp=None
    try:
        fd,tmp=tempfile.mkstemp(prefix=".spider-art-",suffix=".png",
                                dir=str(target.parent))
        os.fchmod(fd,0o600)
        os.close(fd)
        if not frame.save(tmp,"PNG"):
            raise ArtError("PNG export could not render the artwork")
        if target.exists() or target.is_symlink():
            raise ArtError("Another file appeared at the chosen export name")
        os.link(tmp,target,follow_symlinks=False)
    finally:
        if tmp is not None:
            Path(tmp).unlink(missing_ok=True)
    return target

class ArtCanvas(QWidget):
    def __init__(self,owner):
        super().__init__(owner)
        self.owner=owner
        self.zoom=1.
        self.cached=None
        self.current=[]
        self.setMouseTracking(True)
        self.setCursor(Qt.CrossCursor)
        self.setAutoFillBackground(False)
        self.rebuild()

    def rebuild(self):
        self.cached=render_artwork(self.owner.document)
        self.setFixedSize(round(self.owner.document["width"]*self.zoom),
                          round(self.owner.document["height"]*self.zoom))
        self.update()

    def set_zoom(self,zoom):
        self.zoom=zoom
        self.setFixedSize(round(self.owner.document["width"]*zoom),
                          round(self.owner.document["height"]*zoom))
        self.update()

    def _point(self,position):
        doc=self.owner.document
        return [round(min(max(position.x()/self.zoom,0),doc["width"]-1),3),
                round(min(max(position.y()/self.zoom,0),doc["height"]-1),3)]

    def mousePressEvent(self,event):
        if event.button()!=Qt.LeftButton:
            return
        self.current=[self._point(event.pos())]
        self.update()

    def mouseMoveEvent(self,event):
        if not (event.buttons()&Qt.LeftButton) or not self.current:
            return
        point=self._point(event.pos())
        if point!=self.current[-1] and len(self.current)<8192:
            self.current.append(point)
        self.update()

    def mouseReleaseEvent(self,event):
        if event.button()!=Qt.LeftButton or not self.current:
            return
        point=self._point(event.pos())
        if point!=self.current[-1] and len(self.current)<8192:
            self.current.append(point)
        points=self.current
        self.current=[]
        self.owner.commit_paint(points)

    def paintEvent(self,event):
        p=QPainter(self)
        try:
            p.fillRect(self.rect(),QColor("#eeeaf6"))
            p.scale(self.zoom,self.zoom)
            if self.cached is not None:
                p.drawImage(0,0,self.cached)
            if self.current:
                _draw_stroke(p,self.owner.make_stroke(self.current))
        finally:
            p.end()

class SpiderArtLab(QWidget):
    """Embeddable real Art Lab editor; the existing shell supplies navigation."""
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setObjectName("spiderArtLab")
        self.document=new_project()
        self.history=[]
        self.future=[]
        self.color="#DDD2FFFF"
        self.setStyleSheet("""
          #spiderArtLab {background:#141026;color:#f2ecff;}
          QLabel {color:#e6dffe;}
          QPushButton, QComboBox, QSpinBox {
            background:#302449;color:#faf5ff;border:1px solid #7655a5;
            border-radius:6px;padding:7px;}
          QPushButton:hover {background:#503579;}
          QListWidget {background:#241b39;color:#eee5ff;border:1px solid #7655a5;}
          QScrollArea {background:#100d1c;border:1px solid #6a538b;}
        """)
        layout=QVBoxLayout(self)
        title=QLabel("✦ SPIDER ART LAB  /  ORIGINAL CREATIVE WORKSPACE")
        title.setStyleSheet("font-size:19px;font-weight:700;color:#c3a4ff;")
        layout.addWidget(title)
        help_text=QLabel(
            "Draw and paint directly here. Editable layers, photo reference, "
            "undo/redo, PNG export and private .spiderart projects.")
        help_text.setWordWrap(True)
        layout.addWidget(help_text)
        main_actions=QHBoxLayout()
        for name,fn in (
            ("New Canvas",self.new_canvas),("Open Project",self.open_art),
            ("Save New Project",self.save_art),("Export PNG",self.export_png),
            ("Import PNG Reference",self.import_reference),
            ("Undo",self.undo),("Redo",self.redo)):
            button=QPushButton(name)
            button.clicked.connect(fn)
            main_actions.addWidget(button)
        layout.addLayout(main_actions)
        edit_row=QHBoxLayout()
        edit_row.addWidget(QLabel("Tool"))
        self.tool=QComboBox()
        for name in ("pencil","brush","marker","eraser"):
            self.tool.addItem(name.title(),name)
        edit_row.addWidget(self.tool)
        self.color_button=QPushButton("Paint Color")
        self.color_button.clicked.connect(self.pick_color)
        edit_row.addWidget(self.color_button)
        edit_row.addWidget(QLabel("Brush"))
        self.size=QSpinBox()
        self.size.setRange(1,128)
        self.size.setValue(5)
        edit_row.addWidget(self.size)
        edit_row.addWidget(QLabel("Zoom"))
        self.zoom=QComboBox()
        for ratio in (.25,.5,.75,1.,1.5,2.):
            self.zoom.addItem(f"{round(ratio*100)}%",ratio)
        self.zoom.setCurrentIndex(3)
        self.zoom.currentIndexChanged.connect(self.change_zoom)
        edit_row.addWidget(self.zoom)
        edit_row.addStretch(1)
        layout.addLayout(edit_row)
        split=QSplitter(Qt.Horizontal,self)
        self.scroll=QScrollArea()
        self.scroll.setWidgetResizable(False)
        self.canvas=ArtCanvas(self)
        self.scroll.setWidget(self.canvas)
        split.addWidget(self.scroll)
        right=QFrame()
        right.setMinimumWidth(220)
        right.setMaximumWidth(280)
        side=QVBoxLayout(right)
        side.addWidget(QLabel("LAYER STACK  /  TOP → BOTTOM"))
        self.layers=QListWidget()
        self.layers.currentRowChanged.connect(self.set_active)
        side.addWidget(self.layers,1)
        for text,method in (("＋ Add Paint Layer",self.new_layer),
                            ("Toggle Visibility",self.toggle_visible),
                            ("Rename Layer",self.rename_layer),
                            ("Move Layer Up",self.raise_layer),
                            ("Move Layer Down",self.lower_layer),
                            ("Delete Layer",self.delete_layer)):
            action=QPushButton(text)
            action.clicked.connect(method)
            side.addWidget(action)
        side.addStretch(1)
        split.addWidget(right)
        split.setStretchFactor(0,1)
        layout.addWidget(split,1)
        self.status=QLabel("Your canvas is ready. No original files will be overwritten.")
        layout.addWidget(self.status)
        self.refresh()

    def _remember(self):
        self.history.append(copy.deepcopy(self.document))
        self.history=self.history[-25:]
        self.future.clear()

    def _update(self,candidate, message):
        validate_project(candidate)
        self._remember()
        self.document=candidate
        self.refresh()
        self.status.setText(message)

    def refresh(self):
        self.layers.blockSignals(True)
        self.layers.clear()
        for i,layer in reversed(list(enumerate(self.document["layers"]))):
            icon="◉" if layer["visible"] else "○"
            layer_type=" · Photo" if layer["image_png"] else ""
            self.layers.addItem(f"{icon} {layer['name']}{layer_type}  [{i+1}]")
        self.layers.setCurrentRow(
            len(self.document["layers"])-1-self.document["active"])
        self.layers.blockSignals(False)
        self.canvas.rebuild()

    def make_stroke(self,points):
        return create_stroke(points,tool=self.tool.currentData(),
                             color=self.color,width=self.size.value())

    def commit_paint(self,points):
        try:
            result=append_stroke(self.document,self.make_stroke(points))
            self._update(result,f"Painted {len(points)} points on the selected layer.")
        except ArtError as error:
            self.status.setText("Stroke not saved: "+str(error))

    def set_active(self,row):
        if row>=0:
            self.document["active"]=len(self.document["layers"])-row-1

    def new_layer(self):
        try:
            self._update(add_layer(self.document),"New editable paint layer added.")
        except ArtError as error:
            self.status.setText(str(error))

    def _edit_layer(self,operation,message):
        candidate=copy.deepcopy(self.document)
        try:
            operation(candidate)
            self._update(candidate,message)
        except (ArtError,ValueError) as error:
            self.status.setText(str(error))

    def toggle_visible(self):
        self._edit_layer(
            lambda p:p["layers"][p["active"]].update(
                visible=not p["layers"][p["active"]]["visible"]),
            "Layer visibility changed.")

    def rename_layer(self):
        old=self.document["layers"][self.document["active"]]["name"]
        label,accepted=QInputDialog.getText(self,"Layer Name",
                                             "Give this layer a name:",text=old)
        if accepted:
            self._edit_layer(
                lambda p:p["layers"][p["active"]].update(name=label),
                "Layer renamed.")

    def _move(self,direction):
        def swap(p):
            i=p["active"]
            j=i+direction
            if j<0 or j>=len(p["layers"]):
                raise ArtError("Layer is already at the edge of the stack")
            p["layers"][i],p["layers"][j]=p["layers"][j],p["layers"][i]
            p["active"]=j
        self._edit_layer(swap,"Layer stacking order changed.")

    def raise_layer(self): self._move(1)
    def lower_layer(self): self._move(-1)

    def delete_layer(self):
        if len(self.document["layers"])==1:
            self.status.setText("Keep at least one editable paint layer.")
            return
        if QMessageBox.question(
            self,"Delete Layer",
            "Delete this layer from the current canvas? Undo can restore it.",
            QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:
            return
        def remove(p):
            del p["layers"][p["active"]]
            p["active"]=min(p["active"],len(p["layers"])-1)
        self._edit_layer(remove,"Deleted selected layer; use Undo to restore it.")

    def undo(self):
        if not self.history:return
        self.future.append(copy.deepcopy(self.document))
        self.document=self.history.pop()
        self.refresh()
        self.status.setText("Undid last paint or layer change.")

    def redo(self):
        if not self.future:return
        self.history.append(copy.deepcopy(self.document))
        self.document=self.future.pop()
        self.refresh()
        self.status.setText("Restored last undone change.")

    def pick_color(self):
        rgb=QColorDialog.getColor(_brush_color(self.color),self,"Choose Ink Color")
        if rgb.isValid():
            self.color=rgb.name().upper()+"FF"
            self.color_button.setStyleSheet(
                f"background:{rgb.name()};color:#ffffff;font-weight:bold")

    def change_zoom(self):
        if hasattr(self,"canvas"):
            self.canvas.set_zoom(self.zoom.currentData())

    def new_canvas(self):
        if QMessageBox.question(
                self,"New Canvas",
                "Start a new canvas? Unsaved changes on this canvas will be lost.",
                QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:
            return
        self.document=new_project()
        self.history.clear()
        self.future.clear()
        self.refresh()
        self.status.setText("Blank new canvas ready.")

    def _folder(self):
        ART_HOME.mkdir(parents=True,exist_ok=True,mode=0o700)
        if ART_HOME.is_symlink():
            raise ArtError("Artwork home must not be a symlink")
        return ART_HOME

    def open_art(self):
        filename,_=QFileDialog.getOpenFileName(
            self,"Open Spider Art Project",str(ART_HOME),
            "Spider Art Lab (*.spiderart)")
        if not filename:
            return
        try:
            candidate=open_project(filename)
            self.document=candidate
            self.history.clear()
            self.future.clear()
            self.refresh()
            self.status.setText("Project opened. Saving creates a NEW version.")
        except (ArtError,OSError) as error:
            self.status.setText("Could not open project: "+str(error))

    def save_art(self):
        try:
            parent=self._folder()
            suggestion=parent/("Spider-Painting-"+datetime.now().strftime("%Y%m%d-%H%M%S")+".spiderart")
            path,_=QFileDialog.getSaveFileName(self,"Save New Editable Project",
                                                str(suggestion),"Spider Art Lab (*.spiderart)")
            if path:
                if not path.lower().endswith(".spiderart"):path+=".spiderart"
                saved=save_project(path,self.document)
                self.status.setText(f"New editable project saved: {saved.name}")
        except (ArtError,OSError) as error:
            self.status.setText("Project save rejected: "+str(error))

    def export_png(self):
        try:
            parent=self._folder()
            suggestion=parent/("Spider-Painting-"+datetime.now().strftime("%Y%m%d-%H%M%S")+".png")
            path,_=QFileDialog.getSaveFileName(self,"Export Painting as PNG",
                                                str(suggestion),"PNG Painting (*.png)")
            if path:
                if not path.lower().endswith(".png"):path+=".png"
                saved=export_artwork(path,self.document)
                self.status.setText(f"New lossless PNG rendered: {saved.name}")
        except (ArtError,OSError) as error:
            self.status.setText("PNG export rejected: "+str(error))

    def import_reference(self):
        name,_=QFileDialog.getOpenFileName(
            self,"Import a PNG as a Separate Photo Reference",str(Path.home()),
            "PNG image (*.png)")
        if not name:
            return
        try:
            source=Path(name)
            if source.is_symlink() or not source.is_file():
                raise ArtError("Only regular local PNGs are supported")
            if source.stat().st_size>MAX_IMAGE_BYTES:
                raise ArtError("Photo must be no larger than 8 MiB")
            data=source.read_bytes()
            if not data.startswith(b"\x89PNG\r\n\x1a\n") or len(data)<24:
                raise ArtError("Choose an actual PNG image, not a renamed file")
            width,height=struct.unpack(">II",data[16:24])
            if not 1<=width<=4096 or not 1<=height<=4096:
                raise ArtError("PNG reference dimensions must fit 4096 pixels")
            image=QImage.fromData(data,"PNG")
            if image.isNull():
                raise ArtError("PNG reference cannot be decoded")
            candidate=add_layer(self.document,source.stem[:70],
                                image_png=base64.b64encode(data).decode("ascii"))
            self._update(candidate,"Photo reference imported on its OWN layer. Add paint layer to trace.")
        except (ArtError,OSError) as error:
            self.status.setText("Import rejected: "+str(error))
