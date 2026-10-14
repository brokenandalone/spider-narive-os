"""Wave 8 GUI: deliberate file selection, safe bounded asynchronous reviews."""
from __future__ import annotations
from pathlib import Path
import sys

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox, QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit,
    QPushButton, QVBoxLayout, QWidget,
)

from operations_wave8_author import continuity_coverage
from operations_wave8_studio import production_brief
from operations_wave8_study import rubric_signals
from operations_wave8_research import research_provenance
from operations_wave8_kali import purple_training_plan
from operations_wave8_webbie import assistant_readiness
from operations_wave8_system import (
    source_snapshot, compare_source_snapshot, backup_folder_inventory,
)

# Explicit fixed operation keys; user-provided text never selects executable code.
OPERATIONS = {
    "studio": ("Studio | Production readiness", "folder", None,
               "Review up to 24 selected WAV stems, rates, levels and possible roles."),
    "author": ("Author | Continuity coverage", "folder", "json",
               "Choose chapter folder, then YOUR own canon-characters JSON map."),
    "study": ("Study | Rubric signals", "text", "text",
              "Choose a draft and a separate instructor rubric, both TXT/Markdown."),
    "forage": ("Deep Forage | Citation provenance", "text", "json",
               "Choose a saved Markdown report and its sources JSON export."),
    "kali": ("Kali Bay | Purple learning plan", None, None,
             "Use existing read-only tool inventory to suggest permitted lab lessons."),
    "webbie": ("Webbie | Local AI readiness", None, None,
               "Check service presence, local Ollama tags and relevant installed modules."),
    "system": ("System | Baseline snapshot", None, None,
               "Capture source checksums and basic service state in memory."),
    "compare": ("System | Compare a previous baseline", "json", None,
                "Compare source fingerprints against a manually selected earlier snapshot."),
    "backup": ("Recovery | Backup folder inventory", "folder", None,
               "Count naming-matched backup directories without reading their contents."),
}

WORK = {
    "studio": production_brief,
    "author": continuity_coverage,
    "study": rubric_signals,
    "forage": research_provenance,
    "kali": purple_training_plan,
    "webbie": assistant_readiness,
    "system": source_snapshot,
    "compare": compare_source_snapshot,
    "backup": backup_folder_inventory,
}
assert set(OPERATIONS) == set(WORK)

CHOOSER = {
    "text": ("Text and Markdown (*.txt *.md *.markdown)",),
    "json": ("JSON file (*.json)",),
}


class ReviewWorker(QThread):
    result_ready = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, operation, arguments, parent=None):
        super().__init__(parent)
        self.operation = operation
        self.arguments = list(arguments)

    def run(self):
        try:
            result = WORK[self.operation](*self.arguments)
            self.result_ready.emit(result)
        except Exception as exc:
            # Error types only: don't leak arbitrary private text or file contents
            # from parser/exception messages into the GUI.
            self.failed.emit(
                "Review could not finish (" + type(exc).__name__ +
                "). Check that files and folders use the required formats."
            )


class Wave8Panel(QWidget):
    """Owner-selected review actions only; no model or microphone can trigger them."""

    def __init__(self, publish, parent=None):
        super().__init__(parent)
        self.publish = publish
        self.paths = [None, None]
        self.worker = None
        self.busy = False
        main = QVBoxLayout(self)
        self.explanation = QLabel(
            "WAVE 8  /  OWNER-APPROVED PROJECT REVIEWS\n"
            "Choose exactly which files or folder to inspect. Nothing changes them."
        )
        self.explanation.setWordWrap(True)
        main.addWidget(self.explanation)
        self.jobs = QComboBox()
        self.jobs.setObjectName("spiderWave8Operation")
        for identifier, entry in OPERATIONS.items():
            self.jobs.addItem(entry[0], identifier)
        self.jobs.currentIndexChanged.connect(self.refresh_fields)
        main.addWidget(self.jobs)
        self.details = QLabel()
        self.details.setWordWrap(True)
        main.addWidget(self.details)
        self.path_row = []
        for i in range(2):
            row = QHBoxLayout()
            label = QLabel("No input selected.")
            label.setWordWrap(True)
            button = QPushButton("Choose source...")
            button.clicked.connect(
                lambda checked=False, index=i: self.choose_source(index)
            )
            row.addWidget(button)
            row.addWidget(label, 1)
            main.addLayout(row)
            self.path_row.append((button, label))
        self.run_button = QPushButton("RUN SELECTED READ-ONLY REVIEW")
        self.run_button.setObjectName("spiderWave8Run")
        self.run_button.clicked.connect(self.run_operation)
        main.addWidget(self.run_button)
        self.status = QLabel("Ready. No background operations.")
        self.status.setWordWrap(True)
        main.addWidget(self.status)
        self.report = QPlainTextEdit()
        self.report.setReadOnly(True)
        self.report.setObjectName("spiderWave8Report")
        self.report.setPlaceholderText("Report appears here after you click Run.")
        main.addWidget(self.report, 1)
        self.refresh_fields()

    def refresh_fields(self):
        key = self.jobs.currentData()
        if key not in OPERATIONS:
            return
        self.paths = [None, None]
        self.details.setText(OPERATIONS[key][3])
        for i, (button, label) in enumerate(self.path_row):
            typ = OPERATIONS[key][i + 1]
            button.setVisible(typ is not None)
            label.setVisible(typ is not None)
            if typ:
                button.setText("Choose " + ("folder" if typ == "folder" else "file") + "...")
                label.setText("No source selected.")
        self.status.setText("Preview only. Run requires a direct click.")

    def choose_source(self, index):
        key = self.jobs.currentData()
        typ = OPERATIONS[key][index + 1]
        if not typ or self.busy:
            return
        if typ == "folder":
            location = QFileDialog.getExistingDirectory(
                self, "Select local folder to review", str(Path.home())
            )
        else:
            location, _ = QFileDialog.getOpenFileName(
                self, "Select local file to review", str(Path.home()),
                CHOOSER[typ][0],
            )
        if location:
            self.paths[index] = location
            # Only basename in the live UI, not full private directory path.
            self.path_row[index][1].setText(Path(location).name or "Selected folder")

    def run_operation(self):
        if self.busy:
            return
        key = self.jobs.currentData()
        spec = OPERATIONS[key]
        args = []
        for position in (0, 1):
            if spec[position + 1]:
                if not self.paths[position]:
                    self.status.setText("Please select all required inputs.")
                    return
                args.append(self.paths[position])
        self.worker = ReviewWorker(key, args, self)
        self.worker.result_ready.connect(self._success)
        self.worker.failed.connect(self._failure)
        self.worker.finished.connect(self._finished)
        self.busy = True
        self.run_button.setEnabled(False)
        self.jobs.setEnabled(False)
        for button, _ in self.path_row:
            button.setEnabled(False)
        self.status.setText("Reviewing only the selected files; please wait.")
        self.worker.start()

    def _success(self, result):
        self.publish("Wave 8", result)
        self.status.setText("Read-only review finished. Report is not automatically saved.")

    def _failure(self, message):
        self.status.setText(message)
        QMessageBox.warning(self, "Spider Operations Wave 8", message)

    def _finished(self):
        self.busy = False
        self.run_button.setEnabled(True)
        self.jobs.setEnabled(True)
        for button, _ in self.path_row:
            button.setEnabled(True)

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            QMessageBox.information(
                self, "Review still running",
                "The bounded local review is finishing. Close this window after it completes."
            )
            event.ignore()
        else:
            super().closeEvent(event)
