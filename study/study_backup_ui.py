"""User-triggered asynchronous Study backup and archive validation UI."""
from datetime import datetime
from pathlib import Path
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QMessageBox, QFileDialog,
)
try:
    from .store import DB_PATH, DOCUMENTS_ROOT
    from .study_backup import create_study_backup, verify_study_backup
except ImportError:
    from store import DB_PATH, DOCUMENTS_ROOT
    from study_backup import create_study_backup, verify_study_backup


class BackupWorker(QThread):
    ready = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, action, filename, parent=None):
        super().__init__(parent)
        self.action = action
        self.filename = filename

    def run(self):
        try:
            if self.action == "create":
                result = create_study_backup(DB_PATH, DOCUMENTS_ROOT, self.filename)
                self.ready.emit(f"Backup saved: {result['destination']}\n"
                                f"Course files included: {result['files']}\n"
                                "Study database snapshot included and verified.")
            else:
                result = verify_study_backup(self.filename)
                self.ready.emit(
                    f"Backup verified: {result['files']} course files plus "
                    "Study database. This did not restore or modify anything.")
        except Exception as error:
            self.failed.emit(str(error))


class StudyBackupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Study | Private backup and verification")
        self.resize(540, 250)
        self.worker = None
        layout = QVBoxLayout(self)
        note = QLabel(
            "Create a local ZIP of your Study database and course documents. "
            "It may contain private schoolwork. Store it securely. "
            "No school passwords, browser cookies or Webbie models are included. "
            "Backups never overwrite an existing archive; restoration is not automatic.")
        note.setWordWrap(True)
        layout.addWidget(note)
        self.status = QLabel("Ready. Choose a backup action.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.create_button = QPushButton("Create a new private backup")
        self.create_button.clicked.connect(self.create)
        layout.addWidget(self.create_button)
        self.verify_button = QPushButton("Verify an existing Study backup")
        self.verify_button.clicked.connect(self.verify)
        layout.addWidget(self.verify_button)

    def create(self):
        target, _ = QFileDialog.getSaveFileName(
            self, "Save private Study backup", str(Path.home() / "Documents" /
                ("spider-study-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".zip")),
            "Study backups (*.zip)")
        if not target:
            return
        if not target.lower().endswith(".zip"):
            target += ".zip"
        if Path(target).exists():
            QMessageBox.warning(self, "Backup exists",
                                "Choose a new filename. Backups never replace existing files.")
            return
        self.start("create", target)

    def verify(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "Choose Study backup to verify", str(Path.home() / "Documents"),
            "Study backups (*.zip)")
        if file:
            self.start("verify", file)

    def start(self, action, target):
        if self.worker:
            self.status.setText("Backup verification or creation is still running.")
            return
        self.worker = BackupWorker(action, target, self)
        self.worker.ready.connect(self.finished_ok)
        self.worker.failed.connect(self.finished_error)
        self.worker.finished.connect(self.release_worker)
        self.create_button.setEnabled(False)
        self.verify_button.setEnabled(False)
        self.status.setText("Working on local files; keep this window open.")
        self.worker.start()

    def finished_ok(self, message):
        self.status.setText(message)

    def finished_error(self, message):
        self.status.setText("Backup failed: " + message +
                            "\nExisting Study files and backups were not replaced.")

    def release_worker(self):
        self.worker.deleteLater()
        self.worker = None
        self.create_button.setEnabled(True)
        self.verify_button.setEnabled(True)

    def closeEvent(self, event):
        if self.worker is not None:
            event.ignore()
            self.status.setText("Finish the backup or verification before closing.")
            return
        super().closeEvent(event)
