"""Actual Spider Audio Studio clip timeline for a verified session WAV.

This edits EDL metadata, not the original recording. The waveform uses
bounded real PCM samples. All edits flow through the verified FFmpeg mixer.
"""
from __future__ import annotations
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor,QFont,QPainter,QPen
from PyQt5.QtWidgets import (
    QDialog,QVBoxLayout,QFormLayout,QHBoxLayout,QLabel,QDoubleSpinBox,
    QSpinBox,QDialogButtonBox,QWidget)
try:
    from .session_clip_edit import normalize_clip_edit,DEFAULTS
    from .session_waveform import waveform_peaks
    from .multitrack import SessionError
except ImportError:
    from session_clip_edit import normalize_clip_edit,DEFAULTS
    from session_waveform import waveform_peaks
    from multitrack import SessionError


class WaveformThumbnail(QWidget):
    """A real, sampled waveform with colored retained clip and fade regions."""
    def __init__(self,owner):
        super().__init__(owner)
        self.owner=owner
        self.setMinimumHeight(128)
        self.setMinimumWidth(480)
        self.setAccessibleName("Waveform of the selected real recorded WAV")

    def paintEvent(self,event):
        p=QPainter(self)
        try:
            p.setRenderHint(QPainter.Antialiasing,True)
            p.fillRect(self.rect(),QColor("#130f21"))
            w=max(10,self.width()-20)
            h=max(10,self.height()-34)
            left,top=10,12
            middle=top+h/2
            p.setPen(QPen(QColor("#433358"),1))
            p.drawLine(left,round(middle),left+w,round(middle))
            length=max(1,self.owner.source_duration_ms)
            cut_in=min(length,self.owner.start.value()*1000)
            cut_out=(self.owner.end.value()*1000
                     if self.owner.end.value()>0 else length)
            x1=left+round(cut_in*w/length)
            x2=left+round(cut_out*w/length)
            p.fillRect(x1,top,max(0,x2-x1),h,QColor("#352451"))
            retained=max(1,x2-x1)
            keep_seconds=max(.001,(cut_out-cut_in)/1000)
            fade_start=round(retained*min(1,self.owner.fade_in.value()/1000/keep_seconds))
            fade_end=round(retained*min(1,self.owner.fade_out.value()/1000/keep_seconds))
            if fade_start:
                p.fillRect(x1,top,fade_start,h,QColor(19,15,33,120))
                p.setPen(QPen(QColor("#f1bd96"),1))
                p.drawLine(x1,top+h,x1+fade_start,top)
            if fade_end:
                p.fillRect(x2-fade_end,top,fade_end,h,QColor(19,15,33,120))
                p.setPen(QPen(QColor("#f1bd96"),1))
                p.drawLine(x2-fade_end,top,x2,top+h)
            p.setPen(QPen(QColor("#b7a0e0"),1))
            n=len(self.owner.peaks)
            for i,peak in enumerate(self.owner.peaks):
                x=left+round(i*w/max(1,n-1))
                size=max(1,round(peak*(h-10)/2))
                p.setPen(QColor("#a88ed2") if x1<=x<=x2 else QColor("#5c536c"))
                p.drawLine(x,round(middle-size),x,round(middle+size))
            p.setPen(QPen(QColor("#a8f2db"),2))
            for x in (x1,x2):
                p.drawLine(x,top,x,top+h)
            p.setPen(QColor("#ede8f8"))
            p.setFont(QFont("Sans Serif",9))
            p.drawText(left,self.height()-5,"Source 0:00")
            label=f"Source {self.owner.source_duration_ms/1000:.3f} s"
            p.drawText(left+w-145,self.height()-22,145,20,Qt.AlignRight,label)
        finally:
            p.end()


class TrackClipDialog(QDialog):
    def __init__(self,track,clip=None,placement_ms=0,parent=None):
        super().__init__(parent)
        self.track=dict(track)
        self.setWindowTitle("Spider Audio Studio · Edit Recorded Clip")
        self.setObjectName("spiderRecordedClipEditor")
        self.setMinimumWidth(690)
        self.setStyleSheet(
            "#spiderRecordedClipEditor {background:#171126;color:#f5edff}"
            "QLabel {color:#e2d8f6}"
            "QDoubleSpinBox, QSpinBox {background:#312549;color:white;"
            "border:1px solid #8769b4;padding:5px;}")
        options,_=normalize_clip_edit(track,clip,delay_ms=placement_ms)
        self.source_duration_ms=track["frames"]*1000/track["sample_rate"]
        self.peaks=waveform_peaks(track["path"])
        layout=QVBoxLayout(self)
        heading=QLabel("RECORDING TIMELINE  /  NON-DESTRUCTIVE CLIP EDIT")
        heading.setStyleSheet("color:#c3a4ff;font-size:16px;font-weight:700;")
        layout.addWidget(heading)
        note=QLabel(
            f"{track['label']} · {track['filename']} · "
            f"{self.source_duration_ms/1000:.3f}s at {track['sample_rate']} Hz\n"
            "Trim the original source region, place the retained audio "
            "later in the song, and fade in/out without modifying any WAV. "
            "A saved mix preset remembers all clip edits.")
        note.setWordWrap(True)
        layout.addWidget(note)
        fields=QFormLayout()
        self.start=QDoubleSpinBox()
        self.end=QDoubleSpinBox()
        maximum=int(self.source_duration_ms)//1/1000
        for knob in (self.start,self.end):
            knob.setDecimals(3)
            knob.setSingleStep(.025)
            knob.setRange(0,maximum)
            knob.setSuffix(" s")
        self.start.setValue(options["trim_start_ms"]/1000)
        self.end.setValue(options["trim_end_ms"]/1000)
        fields.addRow("Trim source from:",self.start)
        fields.addRow("Trim source until: (0 = original end)",self.end)
        self.position=QDoubleSpinBox()
        self.position.setDecimals(3)
        self.position.setSingleStep(.025)
        self.position.setRange(0,20.0)
        self.position.setSuffix(" s")
        self.position.setValue(placement_ms/1000)
        fields.addRow("Place clip at song time:",self.position)
        self.fade_in=QSpinBox()
        self.fade_out=QSpinBox()
        for fade in (self.fade_in,self.fade_out):
            fade.setRange(0,30000)
            fade.setSingleStep(50)
            fade.setSuffix(" ms")
        self.fade_in.setValue(options["fade_in_ms"])
        self.fade_out.setValue(options["fade_out_ms"])
        fields.addRow("Fade in:",self.fade_in)
        fields.addRow("Fade out:",self.fade_out)
        layout.addLayout(fields)
        self.preview=WaveformThumbnail(self)
        layout.addWidget(self.preview)
        for knob in (self.start,self.end,self.position,
                     self.fade_in,self.fade_out):
            knob.valueChanged.connect(self.preview.update)
        self.status=QLabel("The highlighted section will be kept in the offline mix.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        actions=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        actions.accepted.connect(self._accept_valid)
        actions.rejected.connect(self.reject)
        layout.addWidget(actions)

    def values(self):
        proposed={
            "trim_start_ms":round(self.start.value()*1000),
            "trim_end_ms":round(self.end.value()*1000),
            "fade_in_ms":self.fade_in.value(),
            "fade_out_ms":self.fade_out.value(),
        }
        placement=round(self.position.value()*1000)
        options,region=normalize_clip_edit(
            self.track,proposed,delay_ms=placement)
        return options,placement,region

    def _accept_valid(self):
        try:
            self.values()
        except SessionError as exc:
            self.status.setText("Adjust the clip: "+str(exc))
            return
        self.accept()
