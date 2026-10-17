"""Explicit school OneDrive -> Webbie Homework document selection.

Uses the existing school remote and folder browser, never Webbie's personal
remote. Only the selected file is downloaded to a private temporary directory,
read as text, and then deleted. It does not submit or upload anything.
"""
import tempfile
from pathlib import Path

from PyQt5.QtCore import QProcess, Qt
from PyQt5.QtWidgets import QComboBox, QLabel, QPushButton

try:
    from .school_onedrive import REMOTE, SchoolOneDriveDialog, remote_ready
    from .course_materials import (MAX_FILE_BYTES, read_course_document,
                                   safe_remote_file, format_selected_source)
except ImportError:
    from school_onedrive import REMOTE, SchoolOneDriveDialog, remote_ready
    from course_materials import (MAX_FILE_BYTES, read_course_document,
                                  safe_remote_file, format_selected_source)


class SchoolMaterialPicker(SchoolOneDriveDialog):
    """A bounded, explicit file picker; return selected_material after Accept."""
    def __init__(self, parent, course_folder):
        super().__init__(parent, course_folder)
        self.setWindowTitle("Choose school OneDrive document for Webbie")
        self.selected_material = None
        self._temporary = None
        self._cloud_path = None
        self.kind = QComboBox()
        self.kind.addItem("Assignment directions or rubric", "instructions")
        self.kind.addItem("Reading, source, or class notes", "materials")
        self.kind.addItem("My own previous writing, for style only", "style")
        self.layout().addWidget(QLabel("How should Webbie use the selected file?"))
        self.layout().addWidget(self.kind)
        self.use_button = QPushButton("Use selected file in Homework Assistant")
        self.use_button.clicked.connect(self.use_selected)
        self.layout().addWidget(self.use_button)

    def use_selected(self):
        if self.process is not None or self.browse_process is not None:
            self.status.setText("Finish the current school drive operation first.")
            return
        if not remote_ready():
            self.status.setText("Configure school_onedrive with your university account first.")
            return
        item = self.files.currentItem()
        if item is None:
            self.status.setText("Browse OneDrive and select a document first.")
            return
        name, is_directory = item.data(Qt.UserRole)
        if is_directory:
            self.status.setText("Open the folder and choose a file, not a folder.")
            return
        try:
            cloud_path = safe_remote_file(self.remote_folder, name)
        except ValueError as error:
            self.status.setText(str(error))
            return
        self._temporary = tempfile.TemporaryDirectory(prefix="spider-study-import-")
        self._cloud_path = cloud_path
        local = Path(self._temporary.name) / name
        # One file, never entire folders; never touch the live course directory.
        self.process = QProcess(self)
        self.process.setProgram("rclone")
        self.process.setArguments([
            "copyto", REMOTE + ":" + cloud_path, str(local),
            "--max-size", str(MAX_FILE_BYTES), "--max-duration", "2m",
            "--transfers", "1", "--ignore-existing"
        ])
        self.process.finished.connect(self.import_finished)
        self.process.errorOccurred.connect(self.import_error)
        self.use_button.setEnabled(False)
        self.status.setText("Reading the chosen school file for Webbie...")
        self.process.start()

    def _cleanup(self):
        if self.process is not None:
            self.process.deleteLater()
            self.process = None
        if self._temporary is not None:
            self._temporary.cleanup()
            self._temporary = None
        self.use_button.setEnabled(True)

    def import_finished(self, code, status):
        if self.process is None:
            return
        if code != 0:
            self.status.setText("OneDrive could not download the selected file.")
            self._cleanup()
            return
        try:
            name = self._cloud_path.split("/")[-1]
            filename = Path(self._temporary.name) / name
            document = read_course_document(filename)
            kind = self.kind.currentData()
            text = document if kind == "style" else format_selected_source(self._cloud_path, document)
            self.selected_material = (kind, text)
        except (ValueError, OSError, RuntimeError, ImportError,
                UnicodeError, TimeoutError) as error:
            self.status.setText("Document was not imported: " + str(error))
            self._cleanup()
            return
        self._cleanup()
        self.accept()

    def import_error(self, error):
        self.status.setText("Could not start the school OneDrive file transfer.")
        self._cleanup()

    def closeEvent(self, event):
        super().closeEvent(event)
        if event.isAccepted() and self._temporary is not None:
            self._temporary.cleanup()
            self._temporary = None
