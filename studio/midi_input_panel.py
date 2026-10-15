"""Opt-in external MIDI keyboard input for native Spider Audio Studio.

No device opens on application startup. Refresh/connect are owner-triggered.
Requires optional mido + python-rtmidi on the installed PC, with no automatic
pip install or system package change.
"""
from __future__ import annotations

import threading
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

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
                        if getattr(msg, "type", None) == "note_on":
                            note = getattr(msg, "note", -1)
                            velocity = getattr(msg, "velocity", -1)
                            if type(note) is int and 0 <= note <= 127 and type(velocity) is int and 1 <= velocity <= 127:
                                self.note_on.emit(note, velocity)
                    self._stop.wait(.01)
        except (OSError, RuntimeError, ImportError, AttributeError) as error:
            self.failure.emit("MIDI device error: " + str(error)[:180])

class MidiInputPanel(QWidget):
    def __init__(self, on_note, parent=None):
        super().__init__(parent)
        self.on_note = on_note
        self.worker = None
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
        self.connect_button.setText("Connect MIDI input")
        self.refresh()

    def disconnect(self):
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
