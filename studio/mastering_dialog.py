"""Native Spider Studio Mastering Desk with verified, reversible exports."""
import json
from pathlib import Path
import threading

from PyQt5.QtCore import Qt, QThread, QUrl, pyqtSignal
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QFileDialog,
    QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout,
)

if __package__:
    from .session_master import MasterError, PRESETS, master_wav
else:
    from session_master import MasterError, PRESETS, master_wav


class MasteringWorker(QThread):
    result = pyqtSignal(str, str)

    def __init__(self, path, options):
        super().__init__(QApplication.instance())
        self.path, self.options = str(path), dict(options)
        self.stop = threading.Event()
        QApplication.instance().aboutToQuit.connect(self.shutdown)

    def shutdown(self):
        self.stop.set()
        self.wait()

    def run(self):
        try:
            output = master_wav(self.path, stop=self.stop, **self.options)
            self.result.emit(str(output), "Master exported. Listen before releasing.")
        except (OSError, MasterError, ValueError) as error:
            self.result.emit("", str(error))


class MasteringDialog(QDialog):
    def __init__(self, source=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Spider Studio: Mastering Desk")
        self.resize(690, 420)
        self.worker = None
        self.mastered = None
        layout = QVBoxLayout(self)
        notice = QLabel(
            "Offline two-pass EBU R128 loudness normalization using local FFmpeg. "
            "This DOES NOT master the artistic balance, repair clipping or guarantee "
            "platform loudness compliance. Original WAV stays unchanged."
        )
        notice.setWordWrap(True)
        layout.addWidget(notice)
        select = QHBoxLayout()
        self.source = QLineEdit(str(source) if source else "")
        self.source.setPlaceholderText("Select the finished mix or a recorded WAV")
        self.browse_button = QPushButton("Choose WAV")
        self.browse_button.clicked.connect(self.choose_source)
        select.addWidget(self.source)
        select.addWidget(self.browse_button)
        layout.addLayout(select)
        form = QFormLayout()
        self.preset = QComboBox()
        for key, label in (
                ("balanced_stream", "Balanced streaming reference (-14 LUFS)"),
                ("dynamic_album", "Dynamic album reference (-16 LUFS)"),
                ("modern_rock", "Modern rock reference (-11 LUFS)")):
            self.preset.addItem(label, key)
        self.preset.currentIndexChanged.connect(self.preset_changed)
        self.target_note = QLabel()
        self.target_note.setWordWrap(True)
        form.addRow("Processing target", self.preset)
        form.addRow("Target details", self.target_note)
        layout.addLayout(form)
        formats = QHBoxLayout()
        self.export_flac = QCheckBox("Also export lossless FLAC")
        self.export_mp3 = QCheckBox("Also export MP3 listening copy")
        formats.addWidget(self.export_flac)
        formats.addWidget(self.export_mp3)
        layout.addLayout(formats)
        self.status = QLabel(
            "Creates a fresh private folder for each render. No internet or music models."
        )
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.PlainText)
        layout.addWidget(self.status)
        actions = QHBoxLayout()
        self.start_button = QPushButton("Analyze and master WAV")
        self.start_button.clicked.connect(self.start_master)
        self.stop_button = QPushButton("Stop mastering")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.cancel_master)
        self.play_button = QPushButton("Listen to mastered WAV")
        self.play_button.setEnabled(False)
        self.play_button.clicked.connect(self.play_master)
        self.open_button = QPushButton("Open master folder")
        self.open_button.setEnabled(False)
        self.open_button.clicked.connect(self.open_folder)
        for button in (self.start_button, self.stop_button, self.play_button, self.open_button):
            actions.addWidget(button)
        layout.addLayout(actions)
        self.measurements = QLabel("")
        self.measurements.setTextFormat(Qt.PlainText)
        self.measurements.setWordWrap(True)
        layout.addWidget(self.measurements)
        layout.addStretch()
        self.preset_changed()

    def preset_changed(self, *_):
        target = PRESETS[self.preset.currentData()]
        self.target_note.setText(
            f"Integrated {target['integrated_lufs']:.0f} LUFS; "
            f"target true peak {target['true_peak_dbtp']:.1f} dBTP; "
            f"range {target['lra']:.0f} LU. Final measurements are reported, not guaranteed."
        )

    def choose_source(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose finished PCM WAV", str(Path.home()), "WAV (*.wav)"
        )
        if path:
            self.source.setText(path)

    def start_master(self):
        if self.worker is not None:
            return
        if not self.source.text().strip():
            self.status.setText("Select a finished WAV before mastering.")
            return
        opts = {"preset": self.preset.currentData(),
                "flac": self.export_flac.isChecked(), "mp3": self.export_mp3.isChecked()}
        self.worker = MasteringWorker(self.source.text().strip(), opts)
        self.worker.result.connect(self.master_done)
        self.worker.finished.connect(self.master_finished)
        self.start_button.setEnabled(False)
        self.browse_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.play_button.setEnabled(False)
        self.open_button.setEnabled(False)
        self.mastered = None
        self.measurements.clear()
        self.status.setText("Measuring integrated loudness, then creating a new WAV...")
        self.worker.start()

    def master_done(self, output, message):
        self.status.setText(message)
        if not output:
            return
        self.mastered = Path(output)
        self.play_button.setEnabled(True)
        self.open_button.setEnabled(True)
        try:
            result = json.loads((self.mastered.parent / "master-receipt.json").read_text())
            first = result["input_measurements"]
            second = result["output_measurements"]
            self.measurements.setText(
                f"Input {first['input_i']:.1f} LUFS -> Output {second['output_i']:.1f} LUFS; "
                f"measured output peak {second['output_tp']:.1f} dBTP. "
                "Listen for pumping, distortion and musical dynamics."
            )
        except (OSError, ValueError, KeyError, TypeError):
            self.measurements.setText("Render saved; measurement report unavailable.")

    def master_finished(self):
        worker, self.worker = self.worker, None
        self.start_button.setEnabled(True)
        self.browse_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        if worker is not None:
            worker.deleteLater()

    def cancel_master(self):
        if self.worker is not None:
            self.worker.stop.set()
            self.stop_button.setEnabled(False)
            self.status.setText("Stopping. Original audio stays unchanged.")

    def play_master(self):
        if self.mastered and self.mastered.is_file() and not self.mastered.is_symlink():
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.mastered))):
                self.status.setText("No audio player opened; use Open master folder.")

    def open_folder(self):
        if self.mastered and self.mastered.parent.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.mastered.parent)))

    def closeEvent(self, event):
        if self.worker is not None:
            self.worker.shutdown()
        super().closeEvent(event)
