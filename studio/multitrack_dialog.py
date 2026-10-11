"""Native editor for building honest, real-track Spider Studio DAW handoffs."""
from pathlib import Path
import threading

from PyQt5.QtCore import Qt, QThread, QUrl, pyqtSignal
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QApplication, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QMessageBox, QPushButton, QSpinBox,
    QVBoxLayout,
)

if __package__:
    from .multitrack import ROLES, DEFAULT_OUTPUT, SessionError, export_session
else:
    from multitrack import ROLES, DEFAULT_OUTPUT, SessionError, export_session


class SessionExportWorker(QThread):
    result = pyqtSignal(str, str)

    def __init__(self, tracks, title, tempo):
        super().__init__(QApplication.instance())
        self.tracks, self.title, self.tempo = list(tracks), title, tempo
        self.stop = threading.Event()
        QApplication.instance().aboutToQuit.connect(self.shutdown)

    def shutdown(self):
        self.stop.set()
        self.wait()

    def run(self):
        try:
            path = export_session(self.tracks, title=self.title,
                                  tempo_bpm=self.tempo, stop=self.stop)
            self.result.emit(str(path), "Private multitrack session created. All originals preserved.")
        except (SessionError, OSError, ValueError) as error:
            self.result.emit("", str(error))


class MultitrackDialog(QDialog):
    """Choose independent WAV tracks manually; zero-offset export for local DAWs."""

    def __init__(self, seed_tracks=(), title="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Spider Studio: DAW multitrack session")
        self.resize(740, 510)
        self.entries = []
        self.exported_path = None
        self.worker = None
        layout = QVBoxLayout(self)
        description = QLabel(
            "Give each real WAV its own role: lead vocals, guest harmonies, rhythm guitar, "
            "lead guitar, bass, drums or keys. A generated whole-song take remains "
            "a reference mix, NOT independent guitar or singer stems. "
            "Every exported WAV starts at time zero; check timing in your DAW."
        )
        description.setWordWrap(True)
        layout.addWidget(description)
        form = QFormLayout()
        self.project_title = QLineEdit(title or "Untitled Studio Session")
        self.tempo = QSpinBox()
        self.tempo.setRange(0, 300)
        self.tempo.setSpecialValueText("Unspecified")
        form.addRow("Session title", self.project_title)
        form.addRow("Tempo (BPM)", self.tempo)
        layout.addLayout(form)
        add_row = QHBoxLayout()
        self.role = QComboBox()
        for code in ROLES:
            self.role.addItem(code.replace("_", " ").title(), code)
        self.role.setCurrentIndex(ROLES.index("rhythm_guitar"))
        self.add_button = QPushButton("Add WAV as selected role")
        self.add_button.clicked.connect(self.choose_track)
        self.remove_button = QPushButton("Remove selected")
        self.remove_button.clicked.connect(self.remove_selected)
        add_row.addWidget(self.role)
        add_row.addWidget(self.add_button)
        add_row.addWidget(self.remove_button)
        layout.addLayout(add_row)
        self.track_list = QListWidget()
        layout.addWidget(self.track_list)
        self.status = QLabel("Import existing WAV stems or recordings; no AI model runs during export.")
        self.status.setTextFormat(Qt.PlainText)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        action_row = QHBoxLayout()
        self.export_button = QPushButton("Create editable DAW session")
        self.export_button.clicked.connect(self.start_export)
        self.cancel_button = QPushButton("Stop copying")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_export)
        self.open_button = QPushButton("Open exported folder")
        self.open_button.setEnabled(False)
        self.open_button.clicked.connect(self.open_exported)
        action_row.addWidget(self.export_button)
        action_row.addWidget(self.cancel_button)
        action_row.addWidget(self.open_button)
        layout.addLayout(action_row)
        layout.addWidget(QLabel("Session is saved privately in " + str(DEFAULT_OUTPUT)))
        for entry in seed_tracks:
            try:
                self.add_track_path(entry["path"], entry["role"], entry.get("label", ""))
            except (SessionError, KeyError, TypeError):
                self.status.setText("Some suggested sources were unavailable. Add verified WAVs manually.")

    def add_track_path(self, path, role, label=""):
        source = Path(path).expanduser()
        if (role not in ROLES or source.is_symlink() or not source.is_file()
                or source.suffix.lower() != ".wav"):
            raise SessionError("Select an existing, regular WAV and a valid role.")
        actual = source.resolve()
        if any(Path(item["path"]).resolve() == actual for item in self.entries):
            raise SessionError("That WAV is already included as another track.")
        if len(self.entries) >= 24:
            raise SessionError("Sessions can contain up to 24 WAV tracks.")
        label = (label or actual.stem).strip()[:100]
        self.entries.append({"path": str(actual), "role": role, "label": label})
        self.track_list.addItem(f"{len(self.entries):02d} | {role.replace('_', ' ')} | {label} | {actual}")

    def choose_track(self):
        path, _ = QFileDialog.getOpenFileName(self, "Add independent audio track", str(Path.home()),
                                             "WAV audio (*.wav)")
        if path:
            try:
                self.add_track_path(path, self.role.currentData())
                self.status.setText("Track added. Verify this WAV really contains only the chosen part.")
            except SessionError as error:
                self.status.setText(str(error))

    def remove_selected(self):
        row = self.track_list.currentRow()
        if row >= 0 and self.worker is None:
            self.entries.pop(row)
            self.track_list.takeItem(row)

    def start_export(self):
        if self.worker is not None:
            return
        if not self.entries:
            self.status.setText("Add at least one real WAV track first.")
            return
        bpm = self.tempo.value() or None
        self.worker = SessionExportWorker(self.entries, self.project_title.text(), bpm)
        self.worker.result.connect(self.export_done)
        self.worker.finished.connect(self.export_finished)
        self.add_button.setEnabled(False)
        self.remove_button.setEnabled(False)
        self.export_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.status.setText("Copying original WAV tracks into a new private DAW session...")
        self.worker.start()

    def export_done(self, path, message):
        self.status.setText(message)
        if path:
            self.exported_path = Path(path)
            self.open_button.setEnabled(True)

    def export_finished(self):
        worker, self.worker = self.worker, None
        self.add_button.setEnabled(True)
        self.remove_button.setEnabled(True)
        self.export_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        if worker is not None:
            worker.deleteLater()

    def cancel_export(self):
        if self.worker is not None:
            self.worker.stop.set()
            self.cancel_button.setEnabled(False)
            self.status.setText("Stopping export; originals remain untouched.")

    def open_exported(self):
        if self.exported_path and self.exported_path.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.exported_path)))

    def closeEvent(self, event):
        if self.worker is not None:
            self.worker.shutdown()
        super().closeEvent(event)
