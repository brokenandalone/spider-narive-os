"""Native read-only recording inventory tab. Does not open audio devices."""
from pathlib import Path
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QTextEdit
try:
    from .audio_session_audit import audit_recordings, report_json
except ImportError:
    from audio_session_audit import audit_recordings, report_json

class RecordingAuditPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout=QVBoxLayout(self)
        label=QLabel("Inspect WAV files in a chosen folder. No recording, playback, tagging or file changes.")
        label.setWordWrap(True)
        layout.addWidget(label)
        self.scan_button=QPushButton("Choose folder and audit recordings")
        self.scan_button.clicked.connect(self.select_folder)
        layout.addWidget(self.scan_button)
        self.status=QLabel("No recordings scanned.")
        layout.addWidget(self.status)
        self.results=QTextEdit()
        self.results.setReadOnly(True)
        layout.addWidget(self.results)
    def select_folder(self):
        selected=QFileDialog.getExistingDirectory(self, "Select recording folder",
                                                   str(Path.home()/"Documents"/"Spider Studio"))
        if selected:
            self.scan(selected)
    def scan(self, folder):
        self.scan_button.setEnabled(False)
        try:
            report=audit_recordings(folder)
            counts=report["counts"]
            self.status.setText(
                f'Ready: {counts["ready"]} | Incompatible: {counts["incompatible"]} | '
                f'Unreadable: {counts["unreadable"]} | Links skipped: {report["skipped_symlinks"]}' +
                (" | LIMIT REACHED" if report["truncated"] else ""))
            self.results.setPlainText(report_json(report))
            return report
        except (OSError, ValueError) as exc:
            self.status.setText(f"Audit could not complete: {exc}")
            self.results.clear()
            return None
        finally:
            self.scan_button.setEnabled(True)
