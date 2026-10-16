"""Interactive clip placement canvas for Spider's non-destructive WAV region editor.

One visual lane per region. Drag a region on its lane to move its start
on the song timeline (25 ms snapping), without moving or touching its source.
The numeric millisecond position field remains authoritative and editable.
"""
from __future__ import annotations
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor,QPainter,QPen,QFont
from PyQt5.QtWidgets import QWidget

HEADER=34
LANE=29
MARGIN=15
VISIBLE_MIN_MS=10000

class RegionArrangement(QWidget):
    def __init__(self,editor):
        super().__init__(editor)
        self.editor=editor
        self.drag_row=None
        self.drag_anchor=0
        self.drag_initial=0
        self.setMinimumWidth(600)
        self.setMouseTracking(True)
        self.setAccessibleName("Interactive WAV clip placement lanes; drag a region to move it in the song")
        self.refresh()

    def refresh(self):
        if not hasattr(self.editor,"table"):
            return
        self.setMinimumHeight(HEADER+max(2,self.editor.table.rowCount())*LANE+10)
        self.update()

    def _duration(self,part):
        return max(1,part["end_ms"]-part["start_ms"])

    def _extent(self,parts):
        return max([VISIBLE_MIN_MS]+[
            part["at_ms"]+self._duration(part)+1000 for part in parts])

    def _plot(self,part,row,extent):
        width=max(40,self.width()-MARGIN*2)
        a=MARGIN+round(part["at_ms"]*width/extent)
        b=MARGIN+round((part["at_ms"]+self._duration(part))*width/extent)
        y=HEADER+row*LANE+3
        return a,y,max(3,b-a),LANE-7

    def paintEvent(self,event):
        p=QPainter(self)
        try:
            p.setRenderHint(QPainter.Antialiasing,True)
            p.fillRect(self.rect(),QColor("#120d20"))
            parts=self.editor.rows()
            extent=self._extent(parts)
            width=max(40,self.width()-MARGIN*2)
            p.setPen(QColor("#cab1f7"))
            p.setFont(QFont("Sans Serif",9))
            p.drawText(MARGIN,15,"SONG TIMELINE · DRAG REGIONS TO MOVE THEM")
            p.setPen(QPen(QColor("#4a3b61"),1))
            for index in range(6):
                x=MARGIN+round(index*width/5)
                p.drawLine(x,HEADER-6,x,self.height()-8)
                p.setPen(QColor("#998bb3"))
                p.drawText(x+2,HEADER-10,f"{index*extent/5000:.1f}s")
                p.setPen(QPen(QColor("#4a3b61"),1))
            for row,part in enumerate(parts):
                x,y,w,h=self._plot(part,row,extent)
                selected=row==self.editor.table.currentRow()
                fill=QColor("#846bc1") if selected else QColor("#46345f")
                p.fillRect(x,y,w,h,fill)
                p.setPen(QPen(QColor("#e5d6ff") if selected else QColor("#bca4e5"),1))
                p.drawRect(x,y,w,h)
                p.drawText(x+3,y+h-5,f"{row+1} · {part['at_ms']/1000:.2f}s")
        finally:
            p.end()

    def mousePressEvent(self,event):
        if event.button()!=Qt.LeftButton:
            return
        row=(event.y()-HEADER)//LANE
        parts=self.editor.rows()
        if not 0<=row<len(parts):
            return
        self.editor.table.setCurrentCell(row,0)
        a,y,w,h=self._plot(parts[row],row,self._extent(parts))
        if a<=event.x()<=a+w and y<=event.y()<=y+h:
            self.drag_row=row
            self.drag_anchor=event.x()
            self.drag_initial=parts[row]["at_ms"]
            self.setCursor(Qt.ClosedHandCursor)
        self.update()

    def mouseMoveEvent(self,event):
        if self.drag_row is None or not(event.buttons()&Qt.LeftButton):
            return
        row=self.drag_row
        parts=self.editor.rows()
        if not 0<=row<len(parts):
            return
        duration=self._duration(parts[row])
        extent=self._extent(parts)
        width=max(40,self.width()-MARGIN*2)
        moved_ms=round((event.x()-self.drag_anchor)*extent/width)
        # 25 ms snap; never position the final PCM outside two hours.
        destination=max(0,min(7200000-duration,
                              round((self.drag_initial+moved_ms)/25)*25))
        self.editor.table.cellWidget(row,2).setValue(destination/1000)
        self.update()

    def mouseReleaseEvent(self,event):
        self.drag_row=None
        self.setCursor(Qt.ArrowCursor)
