"""Spider Studio native multi-region recorded WAV arrangement dialog.

Edit up to twelve regions of the SAME original verified track. Each row
contains source in/out, destination song position and independent fades.
The real PCM source preview is sampled read-only; no file is modified.
"""
from __future__ import annotations
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter,QColor,QPen
from PyQt5.QtWidgets import (
    QDialog,QVBoxLayout,QLabel,QHBoxLayout,QPushButton,QSpinBox,QDoubleSpinBox,
    QTableWidget,QTableWidgetItem,QAbstractItemView,QDialogButtonBox,QWidget,
    QScrollArea)
try:
    from .session_regions import MAX_REGIONS,normalize_regions,REGION_FIELDS
    from .session_clip_edit import normalize_clip_edit
    from .session_waveform import waveform_peaks
    from .session_regions_timeline import RegionArrangement
    from .multitrack import SessionError
except ImportError:
    from session_regions import MAX_REGIONS,normalize_regions,REGION_FIELDS
    from session_clip_edit import normalize_clip_edit
    from session_waveform import waveform_peaks
    from session_regions_timeline import RegionArrangement
    from multitrack import SessionError

COLUMNS=("Source in (s)","Source out (s)","Song at (s)",
         "Fade in (ms)","Fade out (ms)")
EDIT_FIELDS=("start_ms","end_ms","at_ms","fade_in_ms","fade_out_ms")


class RegionsWaveform(QWidget):
    def __init__(self,editor):
        super().__init__(editor)
        self.editor=editor
        self.setMinimumSize(650,115)
        self.setAccessibleName("Real source waveform with selected region overlays")

    def paintEvent(self,event):
        painter=QPainter(self)
        try:
            painter.fillRect(self.rect(),QColor("#141026"))
            left=12
            width=max(20,self.width()-24)
            top=9
            height=self.height()-22
            mid=top+height//2
            painter.setPen(QColor("#443657"))
            painter.drawLine(left,mid,left+width,mid)
            peaks=self.editor.peaks
            for i,amp in enumerate(peaks):
                x=left+round(i*width/max(1,len(peaks)-1))
                length=round(min(1.,amp)*height*.44)
                painter.setPen(QPen(QColor("#8777b9"),1))
                painter.drawLine(x,mid-length,x,mid+length)
            max_ms=max(1,self.editor.source_ms)
            for index,region in enumerate(self.editor.rows()):
                a=left+round(region["start_ms"]*width/max_ms)
                b=left+round(region["end_ms"]*width/max_ms)
                if b<=a:
                    continue
                color=QColor("#7be8c3") if index==self.editor.table.currentRow() else QColor("#bb9dec")
                color.setAlpha(125)
                painter.fillRect(a,top,max(1,b-a),height,color)
                painter.setPen(QPen(QColor("#ded1ff"),1))
                painter.drawLine(a,top,a,top+height)
                painter.drawLine(b,top,b,top+height)
        finally:
            painter.end()


class TrackRegionsDialog(QDialog):
    def __init__(self,track,regions=None, *, clip=None,offset_ms=0,parent=None):
        super().__init__(parent)
        self.track=dict(track)
        self.source_ms=round(track["frames"]*1000/track["sample_rate"])
        self.peaks=waveform_peaks(track["path"])
        self.setWindowTitle("Spider Audio Studio · Multi-Region Timeline")
        self.setObjectName("spiderAudioRegions")
        self.resize(1050,530)
        self.setStyleSheet(
            "#spiderAudioRegions {background:#160f24;color:#f5efff;}"
            "QLabel {color:#e6dafa;}"
            "QPushButton, QSpinBox, QDoubleSpinBox {background:#302348;"
            "color:#f5ecff;border:1px solid #7255a3;padding:5px;}"
            "QTableWidget {background:#201831;color:#e8defa;}")
        root=QVBoxLayout(self)
        heading=QLabel("SPIDER STUDIO · MULTI-REGION RECORDED PERFORMANCE")
        heading.setStyleSheet("font-size:18px;color:#c8aeff;font-weight:bold")
        root.addWidget(heading)
        explanation=QLabel(
            "Arrange up to twelve source passages from this SAME verified WAV. "
            "Select an 'in' and 'out' range for each, and the position where "
            "it plays in the song. Regions may overlap. The real source waveform "
            "is read-only; rendering happens later in the Session Mixer.")
        explanation.setWordWrap(True)
        root.addWidget(explanation)
        self.table=QTableWidget(0,5)
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setColumnWidth(0,172)
        self.table.setColumnWidth(1,172)
        self.table.setColumnWidth(2,172)
        self.table.setColumnWidth(3,166)
        self.table.setColumnWidth(4,166)
        self.table.currentCellChanged.connect(self._redraw)
        root.addWidget(self.table,1)
        command=QHBoxLayout()
        for title,method in (
            ("＋ Add region",self.add_region),
            ("Duplicate",self.duplicate_region),
            ("Remove region",self.remove_region),
            ("Move up",lambda:self.move_region(-1)),
            ("Move down",lambda:self.move_region(1))):
            button=QPushButton(title)
            button.clicked.connect(method)
            command.addWidget(button)
        root.addLayout(command)
        self.wave=RegionsWaveform(self)
        root.addWidget(self.wave)
        root.addWidget(QLabel(
            "Drag a region in its song lane to move it; source in/out stay unchanged. "
            "Song placement also remains precisely editable in the table."))
        self.arrangement=RegionArrangement(self)
        self.arrange_scroll=QScrollArea(self)
        self.arrange_scroll.setWidgetResizable(True)
        self.arrange_scroll.setMaximumHeight(240)
        self.arrange_scroll.setWidget(self.arrangement)
        root.addWidget(self.arrange_scroll)
        self.status=QLabel(
            "Regions refer to the original recording; no source or previous mix is overwritten.")
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        actions=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        actions.accepted.connect(self._accept_checked)
        actions.rejected.connect(self.reject)
        root.addWidget(actions)
        initial,_=normalize_regions(track,regions)
        if not initial:
            options,clip_region=normalize_clip_edit(track,clip,delay_ms=offset_ms)
            initial=[{
                "start_ms":options["trim_start_ms"],
                "end_ms":options["trim_end_ms"] or self.source_ms,
                "at_ms":offset_ms,
                "fade_in_ms":options["fade_in_ms"],
                "fade_out_ms":options["fade_out_ms"]}]
        for region in initial:
            self._insert(region)
        self.table.setCurrentCell(0,0)

    def _redraw(self,*args):
        if hasattr(self,"wave"):
            self.wave.update()
        if hasattr(self,"arrangement"):
            self.arrangement.refresh()

    def _insert(self,region):
        if self.table.rowCount()>=MAX_REGIONS:
            raise SessionError("Limit of twelve regions reached.")
        row=self.table.rowCount()
        self.table.insertRow(row)
        for col,key in enumerate(EDIT_FIELDS):
            if col<3:
                knob=QDoubleSpinBox()
                knob.setDecimals(3)
                knob.setSingleStep(.025)
                knob.setSuffix(" s")
                knob.setRange(0,self.source_ms/1000 if col<2 else 7200.)
                knob.setValue(region[key]/1000)
            else:
                knob=QSpinBox()
                knob.setRange(0,30000)
                knob.setSingleStep(25)
                knob.setSuffix(" ms")
                knob.setValue(region[key])
            knob.valueChanged.connect(self._redraw)
            self.table.setCellWidget(row,col,knob)
        self._redraw()

    def rows(self):
        values=[]
        for row in range(self.table.rowCount()):
            values.append({
                key:(round(self.table.cellWidget(row,col).value()*1000)
                     if col<3 else self.table.cellWidget(row,col).value())
                for col,key in enumerate(EDIT_FIELDS)})
        return values

    def add_region(self):
        if self.table.rowCount()>=MAX_REGIONS:
            self.status.setText("Twelve is the maximum number of source regions.")
            return
        if self.table.rowCount():
            source=self.rows()[-1]
            # Default to the last region's source bounds but place directly
            # after it for fast adjacent recording-comp edits.
            proposed={**source,"at_ms":min(7200000,
                source["at_ms"]+max(0,source["end_ms"]-source["start_ms"]))}
        else:
            proposed=dict(start_ms=0,end_ms=self.source_ms,at_ms=0,
                          fade_in_ms=0,fade_out_ms=0)
        self._insert(proposed)
        self.table.setCurrentCell(self.table.rowCount()-1,0)
        self._redraw()

    def duplicate_region(self):
        current=self.table.currentRow()
        if current<0:
            return
        if self.table.rowCount()>=MAX_REGIONS:
            self.status.setText("Twelve is the maximum number of source regions.")
            return
        original=self.rows()[current]
        self._insert(original)
        self.table.setCurrentCell(self.table.rowCount()-1,0)
        self._redraw()

    def remove_region(self):
        current=self.table.currentRow()
        if current<0 or self.table.rowCount()<=1:
            self.status.setText("Keep at least one region in the timeline.")
            return
        self.table.removeRow(current)
        self.table.setCurrentCell(min(current,self.table.rowCount()-1),0)
        self._redraw()

    def move_region(self,delta):
        row=self.table.currentRow()
        dest=row+delta
        if row<0 or dest<0 or dest>=self.table.rowCount():
            return
        current=self.rows()
        current[row],current[dest]=current[dest],current[row]
        # Recreate widgets to preserve source data and callback wiring.
        self.table.setRowCount(0)
        for region in current:
            self._insert(region)
        self.table.setCurrentCell(dest,0)
        self._redraw()

    def values(self):
        return normalize_regions(self.track,self.rows())[0]

    def _accept_checked(self):
        try:
            normalized=self.values()
        except SessionError as error:
            self.status.setText("Fix these edits: "+str(error))
            return
        self.status.setText(f"Validated {len(normalized)} non-destructive regions.")
        self.accept()
