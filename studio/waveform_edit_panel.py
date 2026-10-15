"""Working non-destructive waveform editor panel inside Spider Audio Studio.

The original WAV never changes. Playback is an optional short preview, while
the offline edit/export functions continue working without a sound device.
"""
from __future__ import annotations

from pathlib import Path
from PyQt5.QtCore import Qt, QBuffer, QByteArray, QIODevice, QRectF, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import (
    QCheckBox, QDoubleSpinBox, QFileDialog, QGridLayout, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)
try:
    from PyQt5.QtMultimedia import QAudio, QAudioFormat, QAudioOutput
except ImportError:
    QAudio = QAudioFormat = QAudioOutput = None

try:
    from .waveform_edit_engine import import_wav, render_clip, outline, export_clip
except ImportError:
    from waveform_edit_engine import import_wav, render_clip, outline, export_clip

class WaveformCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.peaks = []
        self.setMinimumHeight(220)
        self.setAccessibleName("Spider Audio Studio waveform preview")

    def set_peaks(self, peaks):
        self.peaks = list(peaks)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#11101d"))
        p.setRenderHint(QPainter.Antialiasing)
        width, height = self.width(), self.height()
        mid = height // 2
        p.setPen(QPen(QColor("#665083"), 1))
        p.drawLine(0, mid, width, mid)
        if self.peaks:
            p.setPen(QPen(QColor("#bd91fb"), max(1, width / max(1, len(self.peaks)) * .62)))
            for i, (minimum, maximum) in enumerate(self.peaks):
                x = int((i + .5) * width / len(self.peaks))
                p.drawLine(x, int(mid - maximum * height * .43),
                           x, int(mid - minimum * height * .43))
        else:
            p.setPen(QPen(QColor("#ddd0f8"), 1))
            p.drawText(self.rect(), Qt.AlignCenter, "Import a PCM WAV to inspect its waveform")
        p.end()

class ClipExportWorker(QThread):
    done = pyqtSignal(bool, str)

    def __init__(self, clip, destination, parent=None):
        super().__init__(parent)
        self.clip = clip
        self.destination = destination

    def run(self):
        try:
            export_clip(self.clip, self.destination)
            self.done.emit(True, "Exported edit: " + Path(self.destination).name)
        except (OSError, ValueError, RuntimeError) as error:
            self.done.emit(False, str(error)[:300])


class WaveformEditPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.original_clip = None
        self.clip = None
        self._audio = None
        self._audio_buffer = None
        self.worker = None
        self._preview_supported = QAudioOutput is not None
        self.setObjectName("spiderWaveformEditor")
        self.setStyleSheet("""
            QWidget#spiderWaveformEditor { background:#100e1d; color:#ede3f9; }
            QLabel {color:#eee5fc;}
            QPushButton {background:#28203b;color:#f5ebff;border:1px solid #8569a5;
                         border-radius:7px;padding:8px;}
            QDoubleSpinBox,QSpinBox {background:#221930;color:#f1e7fc;padding:5px;}
        """)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("WAVEFORM EDITOR / NON-DESTRUCTIVE AUDIO LAB"))
        layout.addWidget(QLabel(
            "Import uncompressed 16-bit WAV. Trim, gain, fade and reverse without changing "
            "the original. Export separately to keep Ardour/Audacity projects safe."))
        buttons = QHBoxLayout()
        buttons.addWidget(self._button("Import WAV", self.import_file))
        buttons.addWidget(self._button("▶ Preview first 5 seconds", self.preview))
        buttons.addWidget(self._button("■ Stop", self.stop_preview))
        buttons.addWidget(self._button("Export edited WAV", self.export_file))
        layout.addLayout(buttons)
        self.canvas = WaveformCanvas(self)
        layout.addWidget(self.canvas, 1)
        self.details = QLabel("No source file imported.")
        layout.addWidget(self.details)
        options = QGridLayout()
        self.start = self._seconds()
        self.end = self._seconds()
        self.gain = QSpinBox()
        self.gain.setRange(-36, 12)
        self.gain.setSuffix(" dB")
        self.fade_in = QSpinBox()
        self.fade_in.setRange(0, 10000)
        self.fade_in.setSuffix(" ms")
        self.fade_out = QSpinBox()
        self.fade_out.setRange(0, 10000)
        self.fade_out.setSuffix(" ms")
        self.reverse = QCheckBox("Reverse clip")
        fields = [
            ("Trim start", self.start), ("Trim end", self.end),
            ("Gain", self.gain), ("Fade in", self.fade_in),
            ("Fade out", self.fade_out), ("Reverse", self.reverse),
        ]
        for index, (label, widget) in enumerate(fields):
            options.addWidget(QLabel(label), index // 3, (index % 3) * 2)
            options.addWidget(widget, index // 3, (index % 3) * 2 + 1)
        layout.addLayout(options)
        for control in (self.start, self.end, self.gain, self.fade_in, self.fade_out):
            control.valueChanged.connect(self.update_edit)
        self.reverse.toggled.connect(self.update_edit)
        self.status = QLabel("Ready. PCM stereo/mono clips, 8–96 kHz, up to 180 seconds and 48 MB.")
        layout.addWidget(self.status)

    def _button(self, label, callback):
        button = QPushButton(label)
        button.clicked.connect(callback)
        return button

    def _seconds(self):
        control = QDoubleSpinBox()
        control.setRange(0, 180)
        control.setDecimals(2)
        control.setSingleStep(.05)
        control.setSuffix(" sec")
        return control

    def import_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Import audio for non-destructive editing",
            str(Path.home() / "Music"), "WAV audio (*.wav)")
        if not filename:
            return
        try:
            candidate = import_wav(filename)
            self.stop_preview()
            self.original_clip = candidate
            self.clip = candidate
            self.start.blockSignals(True)
            self.end.blockSignals(True)
            self.gain.blockSignals(True)
            self.fade_in.blockSignals(True)
            self.fade_out.blockSignals(True)
            self.reverse.blockSignals(True)
            try:
                self.start.setValue(0)
                self.end.setValue(candidate.duration)
                self.gain.setValue(0)
                self.fade_in.setValue(0)
                self.fade_out.setValue(0)
                self.reverse.setChecked(False)
                self.end.setMaximum(candidate.duration)
                self.start.setMaximum(candidate.duration)
            finally:
                for ctrl in (self.start, self.end, self.gain,
                             self.fade_in, self.fade_out, self.reverse):
                    ctrl.blockSignals(False)
            self.details.setText(
                f"{candidate.original.name} · {candidate.channels} channels · "
                f"{candidate.rate} Hz · {candidate.duration:.2f} sec")
            self.update_edit()
        except (ValueError, OSError, EOFError) as error:
            QMessageBox.warning(self, "Cannot import audio", str(error)[:300])

    def update_edit(self):
        if self.original_clip is None:
            return
        source = self.original_clip
        start = min(source.total_frames - 1, round(self.start.value() * source.rate))
        end = min(source.total_frames, round(self.end.value() * source.rate))
        if end <= start:
            self.status.setText("Trim end must be later than trim start.")
            return
        try:
            clip = source.edited(
                start=start, end=end, gain_db=self.gain.value(),
                fade_in_ms=self.fade_in.value(), fade_out_ms=self.fade_out.value(),
                reverse=self.reverse.isChecked())
            self.clip = clip
            self.canvas.set_peaks(outline(clip, 250))
            self.status.setText(
                f"Selected {clip.duration:.2f} sec. Editing settings are non-destructive.")
        except ValueError as error:
            self.status.setText(str(error))

    def _format(self, clip):
        fmt = QAudioFormat()
        fmt.setSampleRate(clip.rate)
        fmt.setChannelCount(clip.channels)
        fmt.setSampleSize(16)
        fmt.setCodec("audio/pcm")
        fmt.setByteOrder(QAudioFormat.LittleEndian)
        fmt.setSampleType(QAudioFormat.SignedInt)
        return fmt

    def stop_preview(self):
        if self._audio is not None:
            self._audio.stop()
            self._audio.deleteLater()
            self._audio = None
            self._audio_buffer = None

    def preview(self):
        if self.clip is None:
            self.status.setText("Import a WAV first.")
            return
        if not self._preview_supported:
            self.status.setText("Preview needs Qt Multimedia on this computer. WAV editing/export still works.")
            return
        self.stop_preview()
        try:
            short = self.clip.edited(end=min(
                self.clip.end, self.clip.start + 5 * self.clip.rate))
            pcm = render_clip(short)
            audio = QAudioOutput(self._format(short), self)
            buffer = QBuffer(audio)
            buffer.setData(QByteArray(pcm))
            buffer.open(QIODevice.ReadOnly)
            self._audio = audio
            self._audio_buffer = buffer
            audio.setVolume(.65)
            audio.start(buffer)
            self.status.setText("Previewing first five seconds of the edited audio.")
        except (ValueError, RuntimeError, OSError) as error:
            self.status.setText("Preview failed: " + str(error)[:250])

    def export_file(self):
        if self.clip is None:
            self.status.setText("Import a WAV first.")
            return
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export edited clip to NEW file",
            str(self.clip.original.with_name(self.clip.original.stem + "-Spider-Edit.wav")),
            "WAV audio (*.wav)")
        if not filename:
            return
        if self.worker is not None and self.worker.isRunning():
            self.status.setText("A waveform export is already running.")
            return
        self.worker = ClipExportWorker(self.clip, filename, self)
        self.worker.done.connect(
            lambda ok, msg: self.status.setText(msg if ok else "Export failed: " + msg))
        self.worker.start()
        self.status.setText("Exporting edited WAV in the background; original stays unchanged.")

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            event.ignore()
            self.status.setText("Waveform export is still running; window preserved.")
            return
        self.stop_preview()
        super().closeEvent(event)
