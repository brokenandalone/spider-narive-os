"""Real native session-mixer channel strip for independent recorded tracks.

The dialog only edits bounded mixer settings. Actual processing happens on
the offline verified WAV render and preserves every recorded source.
"""
from PyQt5.QtWidgets import (
    QDialog,QVBoxLayout,QLabel,QFormLayout,QSpinBox,QCheckBox,
    QDialogButtonBox)
try:
    from .session_track_fx import normalize_track_effects
except ImportError:
    from session_track_fx import normalize_track_effects

class ChannelStripDialog(QDialog):
    def __init__(self,track_name,settings=None,parent=None):
        super().__init__(parent)
        self.setWindowTitle("Spider Audio Studio · Track EQ & Dynamics")
        self.setMinimumWidth(370)
        self.setObjectName("spiderChannelStrip")
        existing=normalize_track_effects(settings)
        self.setStyleSheet(
            "#spiderChannelStrip { background:#171126; color:#efe7ff; }"
            "QLabel { color:#e9dcff; }"
            "QSpinBox { background:#33264f; color:#fff; border:1px solid #8466bf; }")
        outer=QVBoxLayout(self)
        title=QLabel("CHANNEL STRIP · "+str(track_name)[:70])
        title.setStyleSheet("font-size:16px;font-weight:bold;color:#c5a8ff;")
        outer.addWidget(title)
        note=QLabel(
            "These are per-track offline mix settings. Source WAVs are never "
            "modified. The final limiter runs once on the stereo master bus.")
        note.setWordWrap(True)
        outer.addWidget(note)
        form=QFormLayout()
        self.controls={}
        for key,label in (
            ("bass_db","Low EQ (105 Hz)"),
            ("mids_db","Middle EQ (1.05 kHz)"),
            ("treble_db","High EQ (6.3 kHz)")):
            value=QSpinBox()
            value.setRange(-12,12)
            value.setSuffix(" dB")
            value.setValue(existing[key])
            value.setAccessibleName(label)
            self.controls[key]=value
            form.addRow(label,value)
        self.compression=QCheckBox("Gentle compression (3:1)")
        self.compression.setChecked(existing["compression"])
        form.addRow(self.compression)
        self.room=QSpinBox()
        self.room.setRange(0,40)
        self.room.setSuffix(" %")
        self.room.setValue(existing["room"])
        form.addRow("Short room reflections",self.room)
        outer.addLayout(form)
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    def values(self):
        return normalize_track_effects({
            key:control.value() for key,control in self.controls.items()
        } | {"compression":self.compression.isChecked(),
             "room":self.room.value()})
