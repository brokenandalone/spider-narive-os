"""Explicit, versioned upload of a finished Study document to school OneDrive.

Browsing is read-only. Uploads never replace or delete existing cloud files.
No school action occurs without a separate button click and confirmation.
"""
from datetime import datetime, timezone
from pathlib import Path
import re
import secrets

from PyQt5.QtCore import QProcess
from PyQt5.QtWidgets import QLabel, QMessageBox, QPushButton

try:
    from .school_onedrive import REMOTE, SchoolOneDriveDialog, remote_ready
    from .course_materials import safe_remote_file
except ImportError:
    from school_onedrive import REMOTE, SchoolOneDriveDialog, remote_ready
    from course_materials import safe_remote_file


def versioned_upload_path(folder, local_file, *, timestamp=None, token=None):
    """Produce a fresh remote-relative DOCX file path, never an overwrite path."""
    source = Path(local_file)
    if source.suffix.lower() != ".docx":
        raise ValueError("Export an APA Word DOCX document before uploading.")
    stem = re.sub(r"[^A-Za-z0-9_-]+", "-", source.stem).strip("-")[:60] or "homework"
    when = timestamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    nonce = token or secrets.token_hex(4)
    return safe_remote_file(folder, stem + "-" + when + "-" + nonce + ".docx")


class SchoolDraftUploadDialog(SchoolOneDriveDialog):
    def __init__(self, parent, course_folder, local_file):
        super().__init__(parent, course_folder)
        self.setWindowTitle("Save APA homework to school OneDrive")
        self.local_file = Path(local_file)
        self.destination = None
        note = QLabel(
            "Browse to your school folder, then upload a new version of this Word file. "
            "An existing school assignment will never be replaced.")
        note.setWordWrap(True)
        self.layout().addWidget(note)
        self.upload_button = QPushButton("Upload this exported APA Word paper")
        self.upload_button.clicked.connect(self.upload_export)
        self.layout().addWidget(self.upload_button)

    def upload_export(self):
        if self.process is not None or self.browse_process is not None:
            self.status.setText("Finish the current OneDrive operation first.")
            return
        if not remote_ready():
            self.status.setText("Connect the separate school OneDrive account first.")
            return
        if (self.local_file.is_symlink() or not self.local_file.is_file() or
                self.local_file.suffix.lower() != ".docx"):
            self.status.setText("Export a regular APA DOCX document first.")
            return
        if self.local_file.stat().st_size > 16 * 1024 * 1024:
            self.status.setText("The exported Word document exceeds the 16 MB upload limit.")
            return
        try:
            destination = versioned_upload_path(self.remote_folder, self.local_file)
        except ValueError as error:
            self.status.setText(str(error))
            return
        answer = QMessageBox.question(
            self, "Upload school assignment?",
            "Send the selected exported Word file to your school OneDrive?\n\n" +
            REMOTE + ":" + destination +
            "\n\nThis creates a new version. Nothing is submitted to your course.")
        if answer != QMessageBox.Yes:
            self.status.setText("Upload cancelled. Local Word file remains unchanged.")
            return
        self.destination = REMOTE + ":" + destination
        self.process = QProcess(self)
        self.process.setProgram("rclone")
        self.process.setArguments([
            "copyto", str(self.local_file), self.destination,
            "--ignore-existing", "--transfers", "1", "--max-duration", "3m"])
        self.process.finished.connect(self.upload_finished)
        self.process.errorOccurred.connect(self.upload_error)
        self.upload_button.setEnabled(False)
        self.status.setText("Uploading new version to school OneDrive...")
        self.process.start()

    def _release(self):
        if self.process is not None:
            self.process.deleteLater()
            self.process = None
        self.upload_button.setEnabled(True)

    def upload_finished(self, code, status):
        if self.process is None:
            return
        if code == 0:
            self.status.setText("OneDrive upload command completed: " + self.destination +
                                ". Confirm the file appears in your school folder.")
        else:
            self.status.setText("School upload failed. The local Word file is unchanged.")
        self._release()

    def upload_error(self, error):
        self.status.setText("Could not start the school OneDrive upload.")
        self._release()
