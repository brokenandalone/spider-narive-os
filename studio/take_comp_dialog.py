"""Native opt-in Spider Studio two-take comp editor.

A first usable punch/take comp workflow with two source takes and one
editable transition. Engine supports larger edit-decision lists separately.
No recording devices are opened by this dialog.
"""
from pathlib import Path
from PyQt5.QtCore import QThread,pyqtSignal
from PyQt5.QtWidgets import (
    QDialog,QVBoxLayout,QLabel,QComboBox,QHBoxLayout,QDoubleSpinBox,
    QPushButton,QSpinBox,QDialogButtonBox)
try:
    from .take_comp_engine import comp_takes,CompSegment
except ImportError:
    from take_comp_engine import comp_takes,CompSegment

class TakeCompDialog(QDialog):
    def __init__(self,takes,parent=None):
        super().__init__(parent)
        self.setWindowTitle("Spider Audio Studio · Comp Recorded Takes")
        self.setMinimumWidth(560)
        self.takes=list(takes)
        layout=QVBoxLayout(self)
        title=QLabel("COMPOSITE YOUR PERFORMANCE · NO ORIGINAL WAVS ARE EDITED")
        title.setStyleSheet("font-weight:bold;color:#b99aeb;font-size:15px")
        layout.addWidget(title)
        explain=QLabel(
            "Select two equal-length, same-format recordings. The new take uses "
            "the first singer/instrument until the split time and the second "
            "afterward. Add a small crossfade to hide the seam. This is a "
            "two-source, one-split comp editor, not a full drag-and-drop DAW.")
        explain.setWordWrap(True)
        layout.addWidget(explain)
        row=QHBoxLayout()
        row.addWidget(QLabel("First take"))
        self.before=QComboBox()
        row.addWidget(self.before)
        row.addWidget(QLabel("Then"))
        self.after=QComboBox()
        row.addWidget(self.after)
        for index,take in enumerate(self.takes):
            label=f"{index+1:02d} · {take['role']} · {Path(take['path']).name}"
            self.before.addItem(label,index)
            self.after.addItem(label,index)
        if len(self.takes)>1:
            self.after.setCurrentIndex(1)
        layout.addLayout(row)
        edit=QHBoxLayout()
        edit.addWidget(QLabel("Transition at"))
        self.split=QDoubleSpinBox()
        self.split.setRange(.01,300)
        self.split.setDecimals(3)
        self.split.setValue(1.)
        self.split.setSuffix(" s")
        edit.addWidget(self.split)
        edit.addWidget(QLabel("Crossfade"))
        self.fade=QSpinBox()
        self.fade.setRange(0,50)
        self.fade.setValue(8)
        self.fade.setSuffix(" ms")
        edit.addWidget(self.fade)
        layout.addLayout(edit)
        self.status=QLabel(
            "Source files must have matching sample rates, channels, bit depth, "
            "and timeline length. Your original takes are protected.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._confirm)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _confirm(self):
        if self.before.currentData()==self.after.currentData():
            self.status.setText("Choose two different recordings.")
            return
        self.accept()

class CompWorker(QThread):
    recorded=pyqtSignal(object,str)
    def __init__(self,first,second,split_ms,fade_ms,dest,role,parent=None):
        super().__init__(parent)
        import threading
        self.stop_event=threading.Event()
        self.first,self.second=first,second
        self.split_ms=split_ms
        self.fade_ms=fade_ms
        self.dest=dest
        self.role=role

    def run(self):
        try:
            import wave
            with wave.open(str(self.first),"rb") as wav:
                rate=wav.getframerate()
                frames=wav.getnframes()
            split=round(self.split_ms*rate/1000)
            if not 0<split<frames:
                raise ValueError("Transition must fall strictly inside the recording")
            result=comp_takes(
                [self.first,self.second],
                [CompSegment(0,split,0),CompSegment(split,frames,1)],
                self.dest,crossfade_ms=self.fade_ms,stop=self.stop_event)
            self.recorded.emit({
                "path":result["path"],"role":self.role,
                "duration_seconds":frames/rate,
                "sample_rate":rate,"channels":result["channels"],
                "sample_width_bits":result["width"]*8,
                "comp_sources":2,"crossfade_ms":self.fade_ms,
            },"")
        except (ValueError,OSError,RuntimeError) as error:
            self.recorded.emit(None,str(error)[:300])
