"""PyQt session reopening, audited track controls, and private offline mix renders."""
from pathlib import Path
import threading

from PyQt5.QtCore import Qt, QThread, QUrl, pyqtSignal
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QApplication, QAbstractItemView, QCheckBox, QDialog, QDoubleSpinBox,
    QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSpinBox,
    QTableWidget, QTableWidgetItem, QVBoxLayout,
)

if __package__:
    from .session_project import inspect_session
    from .session_mix import render_session
    from .multitrack import SessionError
else:
    from session_project import inspect_session
    from session_mix import render_session
    from multitrack import SessionError


class SessionAuditWorker(QThread):
    result = pyqtSignal(object, str)

    def __init__(self, folder):
        super().__init__(QApplication.instance())
        self.folder = folder
        self.stop = threading.Event()
        QApplication.instance().aboutToQuit.connect(self.shutdown)

    def shutdown(self):
        self.stop.set()
        self.wait()

    def run(self):
        try:
            self.result.emit(inspect_session(self.folder, stop=self.stop), "")
        except (SessionError, OSError, ValueError) as error:
            self.result.emit(None, str(error))


class SessionMixWorker(QThread):
    result = pyqtSignal(str, str)

    def __init__(self, folder, controls, include_reference):
        super().__init__(QApplication.instance())
        self.folder, self.controls = folder, controls
        self.include_reference = include_reference
        self.stop = threading.Event()
        QApplication.instance().aboutToQuit.connect(self.shutdown)

    def shutdown(self):
        self.stop.set()
        self.wait()

    def run(self):
        try:
            output = render_session(self.folder, controls=self.controls,
                                    include_reference=self.include_reference,
                                    stop=self.stop)
            self.result.emit(str(output), "New 48 kHz stereo WAV mix saved. Originals untouched.")
        except (SessionError, OSError, ValueError) as error:
            self.result.emit("", str(error))


class SessionMixDialog(QDialog):
    """Session table is populated only after all local file hashes validate."""

    def __init__(self, session_folder=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Spider Studio: Verified Session Mixing")
        self.resize(1080, 590)
        self.session = None
        self.checker = None
        self.worker = None
        self.rendered = None
        layout = QVBoxLayout(self)
        note = QLabel(
            "Reopen a Spider Studio multitrack session, inspect real independent WAVs, "
            "then control each track before exporting a NEW stereo mix. "
            "Nothing here separates AI instruments or trains a singer model."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        source = QHBoxLayout()
        self.folder = QLineEdit(str(session_folder) if session_folder else "")
        self.folder.setPlaceholderText("Choose a previously exported Spider Studio session folder")
        self.choose_button = QPushButton("Browse session folder")
        self.choose_button.clicked.connect(self.choose_folder)
        self.check_button = QPushButton("Verify and load tracks")
        self.check_button.clicked.connect(self.load_session)
        source.addWidget(self.folder)
        source.addWidget(self.choose_button)
        source.addWidget(self.check_button)
        layout.addLayout(source)
        self.meta = QLabel("Track verification checks the original recorded WAVs and SHA-256 hashes.")
        self.meta.setWordWrap(True)
        layout.addWidget(self.meta)
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            ["File", "Role", "Gain", "Pan", "Mute", "Solo", "Start delay (ms)", "Label"]
        )
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setColumnWidth(0, 185)
        self.table.setColumnWidth(1, 135)
        self.table.setColumnWidth(2, 85)
        self.table.setColumnWidth(3, 85)
        self.table.setColumnWidth(4, 55)
        self.table.setColumnWidth(5, 55)
        self.table.setColumnWidth(6, 140)
        layout.addWidget(self.table)
        self.include_reference = QCheckBox(
            "Explicitly include a full-song reference mix (may double recorded instruments)"
        )
        layout.addWidget(self.include_reference)
        self.status = QLabel("No session loaded.")
        self.status.setTextFormat(Qt.PlainText)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        actions = QHBoxLayout()
        self.mix_button = QPushButton("Render non-destructive session mix")
        self.mix_button.setEnabled(False)
        self.mix_button.clicked.connect(self.start_mix)
        self.stop_button = QPushButton("Stop rendering")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_mix)
        self.play_button = QPushButton("Listen to last rendered WAV")
        self.play_button.setEnabled(False)
        self.play_button.clicked.connect(self.listen)
        self.open_button = QPushButton("Open rendered mix folder")
        self.open_button.setEnabled(False)
        self.open_button.clicked.connect(self.open_rendered_folder)
        for button in (self.mix_button, self.stop_button, self.play_button, self.open_button):
            actions.addWidget(button)
        layout.addLayout(actions)
        if session_folder:
            self.load_session()

    def choose_folder(self):
        path = QFileDialog.getExistingDirectory(
            self, "Open a verified Studio session", str(Path.home() / "Documents"))
        if path:
            self.folder.setText(path)
            self.load_session()

    def load_session(self):
        if self.worker is not None or self.checker is not None:
            return
        self.session = None
        self.table.setRowCount(0)
        self.mix_button.setEnabled(False)
        self.play_button.setEnabled(False)
        self.open_button.setEnabled(False)
        self.rendered = None
        self.status.setText("Checking track metadata and original SHA-256 checksums...")
        self.checker = SessionAuditWorker(self.folder.text().strip())
        self.checker.result.connect(self.audit_done)
        self.checker.finished.connect(self.audit_finished)
        self.check_button.setEnabled(False)
        self.choose_button.setEnabled(False)
        self.checker.start()

    def audit_done(self, session, error):
        if session is None:
            self.status.setText(error or "Session could not be verified.")
            return
        self.session = session
        self.table.setRowCount(len(session["tracks"]))
        for index, track in enumerate(session["tracks"]):
            self.table.setItem(index, 0, QTableWidgetItem(track["filename"]))
            self.table.setItem(index, 1, QTableWidgetItem(track["role"].replace("_", " ")))
            self.table.setItem(index, 7, QTableWidgetItem(track["label"]))
            gain = QDoubleSpinBox()
            gain.setRange(0.0, 2.0)
            gain.setSingleStep(0.05)
            gain.setDecimals(2)
            gain.setValue(1.0)
            self.table.setCellWidget(index, 2, gain)
            pan = QDoubleSpinBox()
            pan.setRange(-1.0, 1.0)
            pan.setSingleStep(0.1)
            pan.setDecimals(2)
            pan.setValue(0.0)
            self.table.setCellWidget(index, 3, pan)
            self.table.setCellWidget(index, 4, QCheckBox())
            self.table.setCellWidget(index, 5, QCheckBox())
            delay = QSpinBox()
            delay.setRange(0, 20000)
            delay.setSingleStep(10)
            self.table.setCellWidget(index, 6, delay)
        rates = ", ".join(map(str, session["sample_rates"]))
        self.meta.setText(
            f"{session['title']} | {len(session['tracks'])} verified tracks | "
            f"{rates} Hz source rates | imports resampled to 48 kHz stereo"
        )
        self.status.setText(
            "Ready. Reference mixes are excluded unless explicitly opted in. "
            "All tracks begin at their saved zero offset, plus optional per-track delay."
        )
        self.mix_button.setEnabled(True)

    def audit_finished(self):
        worker, self.checker = self.checker, None
        self.check_button.setEnabled(True)
        self.choose_button.setEnabled(True)
        if worker is not None:
            worker.deleteLater()

    def mix_controls(self):
        if self.session is None:
            raise SessionError("Verify a saved session before mixing.")
        result = {}
        for index, track in enumerate(self.session["tracks"]):
            result[track["filename"]] = {
                "gain": self.table.cellWidget(index, 2).value(),
                "pan": self.table.cellWidget(index, 3).value(),
                "mute": self.table.cellWidget(index, 4).isChecked(),
                "solo": self.table.cellWidget(index, 5).isChecked(),
                "delay_ms": self.table.cellWidget(index, 6).value(),
            }
        return result

    def start_mix(self):
        if self.worker is not None or self.checker is not None or self.session is None:
            return
        self.mix_button.setEnabled(False)
        self.check_button.setEnabled(False)
        self.choose_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status.setText("Re-verifying WAVs, then rendering privately with FFmpeg...")
        self.worker = SessionMixWorker(
            str(self.session["directory"]), self.mix_controls(),
            self.include_reference.isChecked()
        )
        self.worker.result.connect(self.mix_done)
        self.worker.finished.connect(self.mix_finished)
        self.worker.start()

    def mix_done(self, path, message):
        self.status.setText(message)
        if path:
            self.rendered = Path(path)
            self.play_button.setEnabled(True)
            self.open_button.setEnabled(True)

    def mix_finished(self):
        worker, self.worker = self.worker, None
        self.mix_button.setEnabled(self.session is not None)
        self.check_button.setEnabled(True)
        self.choose_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        if worker is not None:
            worker.deleteLater()

    def stop_mix(self):
        if self.worker is not None:
            self.worker.stop.set()
            self.stop_button.setEnabled(False)
            self.status.setText("Stopping render; source tracks remain unchanged.")

    def listen(self):
        if self.rendered and self.rendered.is_file() and not self.rendered.is_symlink():
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.rendered))):
                self.status.setText("No audio player opened. Open the WAV folder manually.")

    def open_rendered_folder(self):
        if self.rendered and self.rendered.parent.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.rendered.parent)))

    def closeEvent(self, event):
        if self.checker is not None:
            self.checker.shutdown()
        if self.worker is not None:
            self.worker.shutdown()
        super().closeEvent(event)
