"""Two-deck WAV DJ mixer inside the real Spider Studio application.

Nova's existing streaming broadcast is completely independent and untouched.
Crossfader is applied to preview/bounce, not yet a real-time beatmatched deck.
"""
from pathlib import Path

from PyQt5.QtCore import Qt, QBuffer, QByteArray, QIODevice, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QFileDialog, QGridLayout, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QSlider, QVBoxLayout, QWidget,
)
try:
    from PyQt5.QtMultimedia import QAudioFormat, QAudioOutput
except ImportError:
    QAudioFormat = QAudioOutput = None
try:
    from .waveform_edit_engine import import_wav
    from .dj_deck_engine import render_deck_chunks, write_deck_wav
except ImportError:
    from waveform_edit_engine import import_wav
    from dj_deck_engine import render_deck_chunks, write_deck_wav

class DJBounce(QThread):
    ready = pyqtSignal(bool, str)

    def __init__(self, a, b, output, cross, gain_a, gain_b, parent=None):
        super().__init__(parent)
        self.a, self.b = a, b
        self.output = output
        self.cross, self.gain_a, self.gain_b = cross, gain_a, gain_b

    def run(self):
        try:
            write_deck_wav(self.a, self.b, self.output, self.cross, self.gain_a, self.gain_b)
            self.ready.emit(True, "DJ mix exported as stereo PCM WAV.")
        except (OSError, ValueError, RuntimeError) as error:
            self.ready.emit(False, str(error)[:300])

class DJDeckPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.decks = [None, None]
        self._audio = None
        self._audio_data = None
        self.worker = None
        self.setObjectName("spiderDJDeckPanel")
        self.setStyleSheet("""
          QWidget#spiderDJDeckPanel {background:#100a1f;color:#eee6fa;}
          QLabel {color:#eee6fa;}
          QPushButton {background:#30233f;color:#f4ebff;border:1px solid #8b5bac;
            border-radius:8px;padding:10px;min-height:33px;}
          QPushButton:hover {background:#54366f;}
          QSlider::groove:horizontal {height:7px;background:#534365;}
          QSlider::handle:horizontal {width:16px;background:#daaaef;}
        """)
        main = QVBoxLayout(self)
        main.addWidget(QLabel("SPIDER DJ LAB / TWO-DECK CROSSFADER"))
        info = QLabel("Open two PCM WAV files, set independent deck volumes and crossfade. "
                      "Preview five seconds or export a stereo mix. Tempo sync and Nova "
                      "live-radio handoff remain future development.")
        info.setWordWrap(True)
        main.addWidget(info)
        row = QHBoxLayout()
        main.addLayout(row)
        self.deck_labels = []
        for i in range(2):
            side = QVBoxLayout()
            title = QLabel("DECK A" if i == 0 else "DECK B")
            title.setStyleSheet("color:#c9a3fa;font-size:22px;font-weight:bold;")
            side.addWidget(title)
            label = QLabel("No WAV loaded")
            label.setWordWrap(True)
            side.addWidget(label)
            self.deck_labels.append(label)
            load = QPushButton("Load deck " + "AB"[i])
            load.clicked.connect(lambda checked=False, which=i: self.load_deck(which))
            side.addWidget(load)
            row.addLayout(side, 1)
        main.addWidget(QLabel("CROSSFADER   ←  A                               B  →"))
        self.cross = QSlider(Qt.Horizontal)
        self.cross.setRange(-100, 100)
        self.cross.setValue(0)
        self.cross.setAccessibleName("Deck A Deck B crossfader")
        main.addWidget(self.cross)
        gain_row = QGridLayout()
        self.gains = []
        for i in range(2):
            label = QLabel("DECK " + "AB"[i] + " VOLUME")
            slide = QSlider(Qt.Horizontal)
            slide.setRange(0, 100)
            slide.setValue(100)
            slide.setAccessibleName("Deck " + "AB"[i] + " gain")
            gain_row.addWidget(label, i, 0)
            gain_row.addWidget(slide, i, 1)
            self.gains.append(slide)
        main.addLayout(gain_row)
        for slider in (self.cross, *self.gains):
            slider.valueChanged.connect(lambda value: self._changed())
        action_row = QHBoxLayout()
        play = QPushButton("▶ Preview current mix (5 sec)")
        play.clicked.connect(self.preview)
        action_row.addWidget(play)
        stop = QPushButton("■ Stop")
        stop.clicked.connect(self.stop)
        action_row.addWidget(stop)
        save = QPushButton("Export DJ mix WAV")
        save.clicked.connect(self.export)
        action_row.addWidget(save)
        main.addLayout(action_row)
        self.status = QLabel("This is a standalone mixing prototype; BCN/Nova radio service stays untouched.")
        self.status.setWordWrap(True)
        main.addWidget(self.status)
        main.addStretch()

    def _changed(self):
        self.status.setText(
            "Deck A/B crossfader position: " + str(self.cross.value())
            + ". Re-preview to hear the new mix setting.")

    def load_deck(self, index):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Import WAV for DJ deck", str(Path.home() / "Music"),
            "WAV audio (*.wav)")
        if not filename:
            return
        try:
            new_clip = import_wav(filename)
            other = self.decks[1-index]
            if other is not None and other.rate != new_clip.rate:
                raise ValueError("Both decks must have the same WAV sample rate")
            self.stop()
            self.decks[index] = new_clip
            self.deck_labels[index].setText(
                f"{new_clip.original.name}\n{new_clip.rate} Hz · "
                f"{new_clip.channels} channels · {new_clip.duration:.1f}s")
            self.status.setText("Deck loaded. Drag crossfader and preview or export.")
        except (OSError, ValueError, EOFError) as error:
            QMessageBox.warning(self, "Cannot load DJ deck", str(error)[:300])

    def stop(self):
        if self._audio is not None:
            self._audio.stop()
            self._audio.deleteLater()
        self._audio = None
        self._audio_data = None

    def preview(self):
        if self.decks == [None, None]:
            self.status.setText("Load at least one audio deck first.")
            return
        if QAudioOutput is None:
            self.status.setText("Qt Multimedia is not installed; offline mix export still works.")
            return
        self.stop()
        try:
            rate = (self.decks[0] or self.decks[1]).rate
            audio = b"".join(render_deck_chunks(
                *self.decks, cross=self.cross.value(),
                gain_a=self.gains[0].value(), gain_b=self.gains[1].value(),
                limit_frames=rate * 5))
            fmt = QAudioFormat()
            fmt.setSampleRate(rate)
            fmt.setChannelCount(2)
            fmt.setSampleSize(16)
            fmt.setCodec("audio/pcm")
            fmt.setByteOrder(QAudioFormat.LittleEndian)
            fmt.setSampleType(QAudioFormat.SignedInt)
            output = QAudioOutput(fmt, self)
            reader = QBuffer(output)
            reader.setData(QByteArray(audio))
            reader.open(QIODevice.ReadOnly)
            output.setVolume(.6)
            self._audio, self._audio_data = output, reader
            output.start(reader)
            self.status.setText("Previewing first five seconds at the chosen crossfader position.")
        except (OSError, ValueError, RuntimeError) as error:
            self.status.setText("DJ preview failed: " + str(error)[:300])

    def export(self):
        if self.decks == [None, None]:
            self.status.setText("Load at least one deck to export.")
            return
        if self.worker is not None and self.worker.isRunning():
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Spider DJ WAV", str(Path.home() / "Music" / "Spider-DJ-Mix.wav"),
            "WAV audio (*.wav)")
        if not path:
            return
        self.worker = DJBounce(self.decks[0], self.decks[1], path,
                               self.cross.value(), self.gains[0].value(),
                               self.gains[1].value(), self)
        self.worker.ready.connect(
            lambda ok, msg: self.status.setText(msg if ok else "Export failed: " + msg))
        self.worker.start()
        self.status.setText("Rendering DJ crossfade to stereo WAV without changing the imported files.")

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            event.ignore()
            return
        self.stop()
        super().closeEvent(event)
