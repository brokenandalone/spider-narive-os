"""Spider Studio vector piano-roll visualization and click-to-select notes.

A purely native Qt drawing surface: no background images, libraries,
monitoring, audio devices or externally executed notation. Bounded to one
editor page (300 note events) for predictable responsiveness.
"""
from __future__ import annotations
from fractions import Fraction
from PyQt5.QtCore import Qt,QRectF,QPointF,pyqtSignal
from PyQt5.QtGui import QColor,QPainter,QPen,QFont
from PyQt5.QtWidgets import QWidget

COLORS=["#ba8ef5","#63c7d9","#ed96bd","#a7d66c","#e0b778",
        "#7a9ff0","#cf8eea","#58dcb2"]

class SpiderPianoRoll(QWidget):
    note_selected=pyqtSignal(int)

    def __init__(self,parent=None):
        super().__init__(parent)
        self.notes=[]
        self.selected=-1
        self._hit=[]
        self.setMinimumHeight(195)
        self.setAccessibleName("Spider score piano roll; click notes to select for editing")
        self.setToolTip("Click a note to select it in the performance editor below.")

    def set_notes(self,notes):
        self.notes=list(notes[:300])
        self.selected=-1
        self._hit=[]
        self.update()

    def set_selected(self,index):
        self.selected=index if isinstance(index,int) and 0<=index<len(self.notes) else -1
        self.update()

    def paintEvent(self,event):
        painter=QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing,True)
        painter.fillRect(self.rect(),QColor("#171020"))
        painter.setPen(QColor("#c8afe7"))
        painter.setFont(QFont("Sans Serif",9))
        w,h=self.width(),self.height()
        left,top=44,21
        canvas_w=max(1,w-left-12)
        canvas_h=max(1,h-top-18)
        painter.drawText(8,14,"PITCH")
        painter.drawText(left,14,"BEATS / NOTE LENGTHS")
        self._hit=[]
        if not self.notes:
            painter.drawText(left+12,top+26,"Import or record a score to see its notes.")
            painter.end()
            return
        start=min(Fraction(n.start) for n in self.notes)
        end=max(Fraction(n.start+n.duration) for n in self.notes)
        low=min(n.pitch for n in self.notes)
        high=max(n.pitch for n in self.notes)
        low=max(0,low-2)
        high=min(127,high+2)
        lo=max(Fraction(0),start-Fraction(1,2))
        hi=end+Fraction(1,2)
        extent=max(Fraction(1),hi-lo)
        pitches=max(1,high-low+1)
        step=canvas_h/pitches
        def xy(n):
            x=left+float((n.start-lo)/extent)*canvas_w
            width=max(3,float(n.duration/extent)*canvas_w)
            y=top+(high-n.pitch)*step
            return QRectF(x,y+1,width,max(3,step-2))
        # Measure/beat grid. Cap work for long imported performances.
        interval=max(1,int(extent // 80)+1)
        first=int(lo)
        for beat in range(first,int(hi)+1,interval):
            xpos=left+float((Fraction(beat)-lo)/extent)*canvas_w
            if xpos<left or xpos>left+canvas_w:
                continue
            painter.setPen(QPen(QColor("#44345b"),1))
            painter.drawLine(round(xpos),top,round(xpos),top+canvas_h)
            painter.setPen(QColor("#b7a5cc"))
            painter.drawText(round(xpos)+2,top+canvas_h+14,str(beat))
        for pitch in range(low,high+1):
            y=top+(high-pitch)*step
            if pitch%12 == 0:
                painter.setPen(QPen(QColor("#554269"),1))
                painter.drawLine(left,round(y),left+canvas_w,round(y))
                painter.setPen(QColor("#ac95c7"))
                painter.drawText(6,round(y+min(14,step)),str(pitch))
        for index,note in enumerate(self.notes):
            rect=xy(note)
            chosen=index==self.selected
            painter.setPen(QPen(QColor("#eaf7ff" if chosen else "#20132e"),2 if chosen else 1))
            painter.setBrush(QColor("#ffe299") if chosen else QColor(COLORS[note.part%len(COLORS)]))
            painter.drawRoundedRect(rect,3,3)
            if rect.width()>22 and rect.height()>11:
                painter.setPen(QColor("#150d25"))
                painter.drawText(rect.adjusted(3,0,-2,0),Qt.AlignVCenter,str(note.pitch))
            self._hit.append((rect,index))
        painter.end()

    def mousePressEvent(self,event):
        if event.button()==Qt.LeftButton:
            where=QPointF(event.pos())
            for rect,index in reversed(self._hit):
                if rect.contains(where):
                    self.set_selected(index)
                    self.note_selected.emit(index)
                    event.accept()
                    return
        super().mousePressEvent(event)
