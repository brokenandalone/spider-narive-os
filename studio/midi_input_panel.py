"""Opt-in external MIDI keyboard input for native Spider Audio Studio.

No device opens on application startup. Refresh/connect are owner-triggered.
Requires optional mido + python-rtmidi on the installed PC, with no automatic
pip install or system package change.
"""
from __future__ import annotations

import threading
import time
from pathlib import Path
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
    QSpinBox, QFileDialog,
)

try:
    from .midi_take_recorder import MIDITake
    from .score_midi import export_performance_midi
except ImportError:
    from midi_take_recorder import MIDITake
    from score_midi import export_performance_midi

try:
    import mido
except ImportError:
    mido = None

def midi_input_names():
    if mido is None:
        return []
    try:
        return list(mido.get_input_names())
    except (OSError, RuntimeError, ImportError, AttributeError):
        return []

class MidiInputWorker(QThread):
    note_on = pyqtSignal(int, int)
    midi_event = pyqtSignal(str, int, int, float)
    failure = pyqtSignal(str)

    def __init__(self, device_name, parent=None):
        super().__init__(parent)
        self.device_name = device_name
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def run(self):
        if mido is None:
            self.failure.emit("Optional mido/python-rtmidi MIDI backend is unavailable")
            return
        try:
            with mido.open_input(self.device_name) as port:
                while not self._stop.is_set():
                    for msg in port.iter_pending():
                        if self._stop.is_set():
                            break
                        kind = getattr(msg, "type", None)
                        if kind in ("note_on", "note_off"):
                            note = getattr(msg, "note", -1)
                            velocity = getattr(msg, "velocity", -1)
                            if (type(note) is int and 0 <= note <= 127 and
                                type(velocity) is int and 0 <= velocity <= 127):
                                stamp = time.monotonic()
                                event = "note_off" if kind == "note_off" or velocity == 0 else "note_on"
                                self.midi_event.emit(event, note, velocity, stamp)
                                if event == "note_on":
                                    self.note_on.emit(note, velocity)
                    self._stop.wait(.01)
        except (OSError, RuntimeError, ImportError, AttributeError) as error:
            self.failure.emit("MIDI device error: " + str(error)[:180])

class MidiInputPanel(QWidget):
    def __init__(self, on_note, parent=None):
        super().__init__(parent)
        self.on_note = on_note
        self.worker = None
        self.recording = None
        self.last_take = None
        self.setObjectName("spiderOptionalMidiKeyboard")
        outer = QVBoxLayout(self)
        outer.addWidget(QLabel("EXTERNAL MIDI KEYBOARD / MANUAL CONNECTION"))
        explanation = QLabel(
            "Connect a USB/MIDI keyboard to play one of Spider's instruments. "
            "This does not record audio or change ALSA/PipeWire configuration. "
            "Input devices are opened only when you click Connect.")
        explanation.setWordWrap(True)
        outer.addWidget(explanation)
        row = QHBoxLayout()
        self.device = QComboBox()
        self.device.setAccessibleName("Available MIDI keyboard input")
        row.addWidget(self.device, 1)
        refresh = QPushButton("Refresh MIDI ports")
        refresh.clicked.connect(self.refresh)
        row.addWidget(refresh)
        outer.addLayout(row)
        select = QHBoxLayout()
        select.addWidget(QLabel("Play as"))
        self.instrument = QComboBox()
        for kind in ("keys", "guitar", "bass"):
            self.instrument.addItem(kind.title(), kind)
        select.addWidget(self.instrument)
        self.connect_button = QPushButton("Connect MIDI input")
        self.connect_button.clicked.connect(self.toggle)
        select.addWidget(self.connect_button)
        outer.addLayout(select)
        take_row = QHBoxLayout()
        take_row.addWidget(QLabel("Take tempo"))
        self.take_tempo = QSpinBox()
        self.take_tempo.setRange(30, 280)
        self.take_tempo.setValue(120)
        self.take_tempo.setSuffix(" BPM")
        take_row.addWidget(self.take_tempo)
        self.record_btn = QPushButton("● Record MIDI take")
        self.record_btn.clicked.connect(self.start_recording)
        take_row.addWidget(self.record_btn)
        self.stop_record_btn = QPushButton("■ Stop take")
        self.stop_record_btn.clicked.connect(self.stop_recording)
        self.stop_record_btn.setEnabled(False)
        take_row.addWidget(self.stop_record_btn)
        self.save_record_btn = QPushButton("Save MIDI take")
        self.save_record_btn.clicked.connect(self.save_take)
        self.save_record_btn.setEnabled(False)
        take_row.addWidget(self.save_record_btn)
        outer.addLayout(take_row)
        self.status = QLabel()
        self.status.setWordWrap(True)
        outer.addWidget(self.status)
        outer.addStretch()
        self.refresh()

    def refresh(self):
        if self.worker is not None and self.worker.isRunning():
            return
        ports = midi_input_names()
        self.device.clear()
        for port in ports:
            self.device.addItem(port)
        self.connect_button.setEnabled(bool(ports))
        if mido is None:
            self.status.setText("Optional MIDI backend not installed. Virtual instruments remain usable.")
        elif not ports:
            self.status.setText("No usable MIDI inputs found. Connect a controller and refresh.")
        else:
            self.status.setText(f"{len(ports)} MIDI input(s) available. Select one to connect.")

    def toggle(self):
        if self.worker is not None and self.worker.isRunning():
            self.disconnect()
            return
        name = self.device.currentText()
        if not name:
            return
        self.worker = MidiInputWorker(name, parent=self)
        self.worker.note_on.connect(self._note)
        self.worker.midi_event.connect(self._capture_event)
        self.worker.failure.connect(self.status.setText)
        self.worker.finished.connect(self._finished)
        self.connect_button.setText("Disconnect MIDI input")
        self.connect_button.setEnabled(True)
        self.worker.start()
        self.status.setText("Connected to " + name + ". Note messages stay on this computer.")

    def _note(self, note, velocity):
        if not 24 <= note <= 96:
            self.status.setText("MIDI note outside current synth range (24–96).")
            return
        mode = self.instrument.currentData()
        self.on_note(mode, note, velocity)
        self.status.setText(f"Received MIDI {note} (velocity {velocity}) → {mode}.")

    def _finished(self):
        if self.recording is not None:
            self.stop_recording()
        self.connect_button.setText("Connect MIDI input")
        self.refresh()

    def start_recording(self):
        if self.worker is None or not self.worker.isRunning():
            self.status.setText("Connect your MIDI controller before starting a take.")
            return
        if self.recording is not None:
            return
        self.recording = MIDITake(self.take_tempo.value())
        self.recording.start(time.monotonic())
        self.record_btn.setEnabled(False)
        self.stop_record_btn.setEnabled(True)
        self.save_record_btn.setEnabled(False)
        self.status.setText(
            "Recording MIDI note timing/velocity locally. No audio or microphone captured.")

    def _capture_event(self, kind, note, velocity, timestamp):
        if self.recording is None:
            return
        try:
            self.recording.event(kind, note, velocity, timestamp,
                                 self.instrument.currentData())
        except ValueError as error:
            self.status.setText("Take capture stopped: " + str(error)[:160])
            self.stop_recording()

    def stop_recording(self):
        capture = self.recording
        if capture is None:
            return
        self.recording = None
        self.record_btn.setEnabled(True)
        self.stop_record_btn.setEnabled(False)
        try:
            capture.stop(max(time.monotonic(),capture.last_time))
            self.last_take = capture.as_performance()
            self.save_record_btn.setEnabled(True)
            self.status.setText(
                f"Captured {len(self.last_take.notes)} MIDI notes. Save the take "
                "or load the resulting MIDI file in Spider Auto Performer.")
        except ValueError as error:
            self.status.setText("No complete MIDI take: " + str(error)[:180])

    def save_take(self):
        if self.last_take is None:
            self.status.setText("Record a MIDI take first.")
            return
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save performance for Spider Auto Performer",
            str(Path.home() / "Music" / "Spider-Live-Take.mid"), "MIDI (*.mid)")
        if filename:
            try:
                export_performance_midi(self.last_take, filename)
                self.status.setText(
                    "Saved MIDI take: " + Path(filename).name
                    + ". Import it through the Auto Performer tab.")
            except (OSError, ValueError) as error:
                self.status.setText("Could not save MIDI take: " + str(error)[:220])

    def disconnect(self):
        if self.recording is not None:
            self.stop_recording()
        if self.worker is not None and self.worker.isRunning():
            self.worker.stop()
            if not self.worker.wait(1500):
                self.status.setText("MIDI connection is still closing.")
                return
        self.connect_button.setText("Connect MIDI input")
        self.refresh()

    def closeEvent(self, event):
        self.disconnect()
        if self.worker is not None and self.worker.isRunning():
            event.ignore()
        else:
            super().closeEvent(event)
