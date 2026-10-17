"""Native, playable Spider Audio Studio instrument rack inside the real bay.

Four drum lanes with 16-step pattern, guitar/bass notes and keyboard.
All audio synthesized locally. Preview uses Qt sound when available,
and explicit Export creates separate PCM WAV with overwrite confirmation.
No extra desktop launcher and no installed Ubuntu Studio apps replaced.
"""
from __future__ import annotations

import os
from pathlib import Path
import tempfile

from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QCheckBox, QComboBox, QSpinBox, QFileDialog, QMessageBox, QGroupBox,
)
try:
    from PyQt5.QtMultimedia import QSoundEffect
except ImportError:
    QSoundEffect = None

from instrument_engine import (NOTES, DRUMS, demo_pattern, export_wav)


class InstrumentRack(QWidget):
    """An instrument workbench, not links to third-party apps."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("spiderNativeInstrumentRack")
        self.preview_path = None
        self.player = QSoundEffect(self) if QSoundEffect is not None else None
        self.instrument = "Keyboard"
        base = QVBoxLayout(self)
        title = QLabel("SPIDER AUDIO STUDIO / LIVE INSTRUMENT RACK")
        title.setStyleSheet("font-size:19px;font-weight:bold;color:#dbb9ff")
        base.addWidget(title)
        note = QLabel(
            "Play guitar, bass and keyboard notes or program four drum lanes. "
            "WAV synthesis runs locally. For full multitrack recording and "
            "effects, keep using Ardour, Guitarix, Hydrogen and other Ubuntu Studio tools.")
        note.setWordWrap(True)
        base.addWidget(note)
        row = QHBoxLayout()
        row.addWidget(QLabel("Instrument"))
        self.mode = QComboBox()
        for option in ("Keyboard", "Guitar", "Bass", "Drums"):
            self.mode.addItem(option)
        self.mode.currentTextChanged.connect(self.choose_mode)
        row.addWidget(self.mode)
        row.addWidget(QLabel("Octave"))
        self.octave = QSpinBox()
        self.octave.setRange(2, 5)
        self.octave.setValue(3)
        row.addWidget(self.octave)
        base.addLayout(row)

        self.keys_group = QGroupBox("Playable notes")
        keyboard = QGridLayout(self.keys_group)
        self.keys = []
        for index, name in enumerate(NOTES):
            trigger = QPushButton(name)
            trigger.setObjectName("instrumentNote" + name.replace("#", "Sharp"))
            trigger.setAccessibleName("Play " + name + " on chosen instrument")
            trigger.setMinimumHeight(50)
            trigger.clicked.connect(
                lambda checked=False, pitch=name: self.play_note(pitch))
            keyboard.addWidget(trigger, index // 6, index % 6)
            self.keys.append(trigger)
        base.addWidget(self.keys_group)

        self.drums_group = QGroupBox("16-step drum machine")
        grid = QGridLayout(self.drums_group)
        grid.addWidget(QLabel("Instrument / step"), 0, 0)
        for step in range(16):
            number = QLabel(str(step + 1))
            number.setAlignment(Qt.AlignCenter)
            grid.addWidget(number, 0, step + 1)
        self.steps = {}
        defaults = demo_pattern()
        for row_index, instrument in enumerate(DRUMS, 1):
            grid.addWidget(QLabel(instrument), row_index, 0)
            self.steps[instrument] = []
            for step in range(16):
                toggle = QCheckBox()
                toggle.setChecked(defaults[instrument][step])
                toggle.setAccessibleName(instrument + " at step " + str(step + 1))
                grid.addWidget(toggle, row_index, step + 1,
                               alignment=Qt.AlignCenter)
                self.steps[instrument].append(toggle)
        row = QHBoxLayout()
        self.tempo = QSpinBox()
        self.tempo.setRange(45, 220)
        self.tempo.setValue(110)
        self.tempo.setSuffix(" BPM")
        row.addWidget(QLabel("Tempo"))
        row.addWidget(self.tempo)
        row.addWidget(QLabel("Bars"))
        self.bars = QSpinBox()
        self.bars.setRange(1, 4)
        self.bars.setValue(2)
        row.addWidget(self.bars)
        reset = QPushButton("Reset drum pattern")
        reset.clicked.connect(self.reset_pattern)
        row.addWidget(reset)
        grid.addLayout(row, 5, 0, 1, 17)
        base.addWidget(self.drums_group)
        self.drums_group.hide()

        buttons = QHBoxLayout()
        audition = QPushButton("Preview sound")
        audition.setAccessibleName("Preview instrument or drum pattern")
        audition.clicked.connect(self.preview)
        buttons.addWidget(audition)
        export = QPushButton("Export a new WAV")
        export.setAccessibleName("Export instrument or drum WAV")
        export.clicked.connect(self.export)
        buttons.addWidget(export)
        base.addLayout(buttons)
        self.status = QLabel(
            "Ready. Click a note to hear it. This doesn't record over any of your songs.")
        self.status.setWordWrap(True)
        base.addWidget(self.status)
        base.addStretch(1)

    def choose_mode(self, name):
        self.instrument = name
        self.keys_group.setVisible(name != "Drums")
        self.drums_group.setVisible(name == "Drums")

    def pattern(self):
        return {name: [button.isChecked() for button in self.steps[name]]
                for name in DRUMS}

    def reset_pattern(self):
        original = demo_pattern()
        for name in DRUMS:
            for step, checked in enumerate(original[name]):
                self.steps[name][step].setChecked(checked)

    def wav(self, note="C"):
        return export_wav(
            self.instrument, note=note, octave=self.octave.value(),
            pattern=self.pattern(), bpm=self.tempo.value(),
            bars=self.bars.value())

    def play_note(self, note):
        if self.instrument == "Drums":
            return
        self._preview_bytes(self.wav(note))

    def preview(self):
        self._preview_bytes(self.wav())

    def _preview_bytes(self, content):
        if self.player is None:
            self.status.setText(
                "Qt Multimedia is unavailable. You can still export a real WAV.")
            return
        try:
            if self.player.isPlaying():
                self.player.stop()
            old_path = self.preview_path
            fd, filename = tempfile.mkstemp(prefix="spider-instrument-", suffix=".wav")
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(content)
            except Exception:
                os.unlink(filename)
                raise
            self.preview_path = filename
            self.player.setSource(QUrl.fromLocalFile(filename))
            self.player.setVolume(0.62)
            self.player.play()
            # A previous sample is no longer in use after the new source is set.
            if old_path:
                try:
                    Path(old_path).unlink(missing_ok=True)
                except OSError:
                    pass
            self.status.setText(self.instrument + " preview requested using local audio.")
        except OSError as error:
            self.status.setText("Preview unavailable: " + str(error))

    def export(self):
        preferred = str(
            Path.home() / "Documents/Spider Studio" /
            ("drum-pattern.wav" if self.instrument == "Drums" else
             self.instrument.lower() + "-note.wav"))
        selected, _ = QFileDialog.getSaveFileName(
            self, "Export your new instrument sound", preferred,
            "WAV audio (*.wav)")
        if not selected:
            return
        destination = Path(selected)
        if destination.suffix.lower() != ".wav":
            destination = destination.with_suffix(".wav")
        if destination.is_symlink():
            self.status.setText("Symlink export target rejected.")
            return
        if destination.exists():
            approved = QMessageBox.question(
                self, "Replace existing WAV?",
                "That file already exists. Replace it with the new export?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if approved != QMessageBox.Yes:
                return
        try:
            payload = self.wav()
            parent = destination.parent
            if not parent.is_dir():
                raise FileNotFoundError("Choose an existing export folder")
            fd, temporary = tempfile.mkstemp(prefix=".instrument-", suffix=".wav",
                                             dir=parent)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(payload)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, destination)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
            self.status.setText("New WAV exported: " + str(destination))
        except (OSError, ValueError) as error:
            self.status.setText("Export failed: " + str(error))

    def closeEvent(self, event):
        if self.player is not None:
            self.player.stop()
            self.player.setSource(QUrl())
        if self.preview_path:
            try:
                Path(self.preview_path).unlink(missing_ok=True)
            except OSError:
                pass
            self.preview_path = None
        super().closeEvent(event)
