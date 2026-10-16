"""Native Spider Studio non-destructive vocal and instrument effects controls."""
from pathlib import Path
from PyQt5.QtCore import QThread,pyqtSignal
from PyQt5.QtWidgets import (
    QDialog,QVBoxLayout,QLabel,QHBoxLayout,QSpinBox,QCheckBox,
    QDialogButtonBox)
try:
    from .take_effects import TakeEffects,apply_take_effects
except ImportError:
    from take_effects import TakeEffects,apply_take_effects

class TakeEffectsDialog(QDialog):
    def __init__(self,source,parent=None):
        super().__init__(parent)
        self.setWindowTitle("Spider Studio · Shape Recorded Take")
        self.setMinimumWidth(550)
        layout=QVBoxLayout(self)
        heading=QLabel("BUILT-IN STUDIO EFFECTS · EXPORT A NEW WAV")
        heading.setStyleSheet("font-weight:bold;font-size:15px;color:#c9a6ed")
        layout.addWidget(heading)
        description=QLabel(
            f"Recording: {Path(source).name}\n"
            "Shape bass, midrange and treble, add 3:1 compression and a subtle "
            "short reflected room sound. Final limiter helps prevent clipping. "
            "This is offline FFmpeg DSP, not VST/LV2 hosting. "
            "The source WAV will never be modified.")
        description.setWordWrap(True)
        layout.addWidget(description)
        self.controls={}
        for label,name in (("Bass EQ","bass_db"),("Midrange EQ","mids_db"),
                           ("Treble EQ","treble_db")):
            row=QHBoxLayout()
            row.addWidget(QLabel(label))
            knob=QSpinBox()
            knob.setRange(-12,12)
            knob.setSuffix(" dB")
            knob.setAccessibleName(label)
            row.addWidget(knob)
            layout.addLayout(row)
            self.controls[name]=knob
        self.compression=QCheckBox("Compression (3:1 ratio, gentle)")
        layout.addWidget(self.compression)
        row=QHBoxLayout()
        row.addWidget(QLabel("Room reflections"))
        self.room=QSpinBox()
        self.room.setRange(0,40)
        self.room.setSuffix(" %")
        row.addWidget(self.room)
        layout.addLayout(row)
        self.status=QLabel("A new 24-bit WAV is created only after render validation.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def settings(self):
        return TakeEffects(
            self.controls["bass_db"].value(),
            self.controls["mids_db"].value(),
            self.controls["treble_db"].value(),
            self.compression.isChecked(),self.room.value()).validate()

class EffectsWorker(QThread):
    recorded=pyqtSignal(object,str)
    def __init__(self,source,destination,role,settings,parent=None):
        super().__init__(parent)
        import threading
        self.stop_event=threading.Event()
        self.source,self.destination=source,destination
        self.role,self.settings=role,settings
    def run(self):
        try:
            result=apply_take_effects(self.source,self.destination,self.settings,
                                      stop=self.stop_event)
            result["role"]=self.role
            self.recorded.emit(result,"")
        except (ValueError,OSError,RuntimeError) as error:
            self.recorded.emit(None,str(error)[:320])
