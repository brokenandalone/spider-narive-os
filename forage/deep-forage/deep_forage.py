#!/usr/bin/env python3
"""Deep Forage native UI: sequential queue, graceful stop, report/source history."""
import html
import os
from pathlib import Path
import subprocess
import sys
import threading

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QMainWindow, QPushButton, QTextBrowser, QVBoxLayout, QWidget,
)

ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from engine import deep_research, ResearchCancelled, REPORT_DIR
from research_archive import list_reports
from workspace_export import export_report


class ResearchWorker(QThread):
    progress = pyqtSignal(str)
    completed = pyqtSignal(object)
    failed = pyqtSignal(str)
    stopped = pyqtSignal(str)

    def __init__(self, topic, depth="standard", focus="general"):
        super().__init__()
        self.topic = topic
        self.depth = depth
        self.focus = focus
        self.cancel_event = threading.Event()

    def cancel(self):
        self.cancel_event.set()

    def run(self):
        try:
            result = deep_research(
                self.topic, progress=self.progress.emit,
                cancel=self.cancel_event.is_set,
                depth=self.depth, focus=self.focus,
            )
            self.completed.emit(result)
        except ResearchCancelled as error:
            self.stopped.emit(str(error))
        except Exception as error:
            self.failed.emit(str(error))


class DeepForageWindow(QMainWindow):
    def __init__(self, initial_topic=""):
        super().__init__()
        self.worker = None
        self.pending_topics = []
        self.history_rows = []
        self.last_report = None
        self.last_sources = None
        self.setWindowTitle("Deep Forage | Spider OS")
        self.resize(1080, 800)
        self.setStyleSheet("""
            QWidget, QMainWindow {background:#09070c;color:#f5eff8;font-size:14px;}
            QLineEdit, QTextBrowser, QComboBox, QListWidget {
                background:#150f1d;border:1px solid #8150ae;
                border-radius:7px;padding:9px;color:#f5eff8;
                selection-background-color:#7132a8;selection-color:#fff;
            }
            QComboBox QAbstractItemView {
                background:#180e20;color:#fff;selection-background-color:#7132a8;
            }
            QPushButton {
                background:#63218f;border:1px solid #a35bea;
                border-radius:7px;padding:10px;color:#fff;font-weight:bold;
            }
            QPushButton:disabled {background:#282230;color:#aaa1ad;border-color:#51445b;}
            QPushButton:hover:!disabled {background:#8130b7;}
        """)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(11)

        title = QLabel("DEEP FORAGE")
        title.setStyleSheet("font-size:30px;font-weight:bold;color:#d8b4fe;")
        layout.addWidget(title)
        description = QLabel("RESEARCH  •  VERIFY  •  COMPARE  •  EXPORT")
        description.setStyleSheet("color:#c5b5ce;")
        layout.addWidget(description)

        self.topic = QLineEdit(initial_topic)
        self.topic.setPlaceholderText("What should Deep Forage investigate?")
        self.topic.returnPressed.connect(self.research)
        layout.addWidget(self.topic)

        options = QHBoxLayout()
        self.depth = QComboBox()
        self.depth.addItems(["Quick (6 sources)", "Standard (12 sources)", "Intensive (20 sources)"])
        self.depth.setCurrentIndex(1)
        self.depth.setAccessibleName("Research depth")
        options.addWidget(self.depth, 1)
        self.focus = QComboBox()
        self.focus.addItems(["General", "Academic", "Technical", "Creative"])
        self.focus.setAccessibleName("Research lens")
        options.addWidget(self.focus, 1)
        layout.addLayout(options)

        row = QHBoxLayout()
        self.run_button = QPushButton("BEGIN RESEARCH")
        self.run_button.clicked.connect(self.research)
        row.addWidget(self.run_button)
        self.stop_button = QPushButton("STOP RESEARCH")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_research)
        row.addWidget(self.stop_button)
        layout.addLayout(row)

        self.status = QLabel("Ready. Search runs on this PC; results require verified sources.")
        self.status.setStyleSheet("color:#ceb6de;")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        queue_title = QLabel("Pending research queue")
        queue_title.setStyleSheet("color:#d8b4fe;font-weight:bold;")
        layout.addWidget(queue_title)
        self.queue_view = QListWidget()
        self.queue_view.setMaximumHeight(105)
        layout.addWidget(self.queue_view)

        self.output = QTextBrowser()
        self.output.setOpenExternalLinks(True)
        layout.addWidget(self.output, 1)

        saved = QHBoxLayout()
        self.open_report = QPushButton("OPEN SAVED REPORT")
        self.open_report.clicked.connect(self.open_saved_report)
        self.open_report.setEnabled(False)
        saved.addWidget(self.open_report)
        self.open_sources = QPushButton("OPEN SOURCE EXPORT")
        self.open_sources.clicked.connect(self.open_saved_sources)
        self.open_sources.setEnabled(False)
        saved.addWidget(self.open_sources)
        layout.addLayout(saved)

        handoff = QHBoxLayout()
        study = QPushButton("EXPORT TO STUDY")
        study.clicked.connect(lambda: self.export_to("study"))
        handoff.addWidget(study)
        author = QPushButton("EXPORT TO AUTHOR")
        author.clicked.connect(lambda: self.export_to("author"))
        handoff.addWidget(author)
        layout.addLayout(handoff)

        history_row = QHBoxLayout()
        self.history = QComboBox()
        self.history.setAccessibleName("Previous research reports")
        history_row.addWidget(self.history, 1)
        self.history_button = QPushButton("OPEN HISTORY")
        self.history_button.clicked.connect(self.open_history)
        history_row.addWidget(self.history_button)
        layout.addLayout(history_row)
        self.refresh_history()

    def refresh_history(self):
        self.history_rows = list_reports(REPORT_DIR)
        self.history.clear()
        for record in self.history_rows:
            self.history.addItem(
                record["title"] + "  [" + record["evidence_status"] + "]",
                record["path"],
            )
        self.history_button.setEnabled(bool(self.history_rows))

    def _refresh_queue(self):
        self.queue_view.clear()
        self.queue_view.addItems([
            f"{topic}  [{depth}, {focus}]"
            for topic, depth, focus in self.pending_topics
        ])

    def research(self):
        topic = self.topic.text().strip()
        if not topic:
            self.status.setText("Enter a research question first.")
            return
        depth = ("quick", "standard", "intensive")[self.depth.currentIndex()]
        focus = self.focus.currentText().lower()
        if self.worker and self.worker.isRunning():
            if len(self.pending_topics) >= 20:
                self.status.setText("Queue full. Finish or cancel existing work first.")
                return
            self.pending_topics.append((topic, depth, focus))
            self._refresh_queue()
            self.status.setText(f"Queued: {topic}")
            self.topic.clear()
            return
        self._start(topic, depth, focus)

    def _start(self, topic, depth, focus):
        self.topic.clear()
        self.output.clear()
        self.run_button.setText("ADD TO QUEUE")
        self.stop_button.setEnabled(True)
        self.status.setText(f"Researching: {topic}")
        self.worker = ResearchWorker(topic, depth=depth, focus=focus)
        self.worker.progress.connect(self.status.setText)
        self.worker.completed.connect(self.completed)
        self.worker.failed.connect(self.failed)
        self.worker.stopped.connect(self.stopped)
        self.worker.finished.connect(self._after_finished)
        self.worker.start()

    def stop_research(self):
        self.pending_topics.clear()
        self._refresh_queue()
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.stop_button.setEnabled(False)
            self.status.setText("Stopping after the current network operation or model chunk.")
        else:
            self.status.setText("Queue cleared.")

    def _after_finished(self):
        self.stop_button.setEnabled(False)
        if self.pending_topics:
            next_topic, depth, focus = self.pending_topics.pop(0)
            self._refresh_queue()
            self._start(next_topic, depth, focus)
        else:
            self.run_button.setText("BEGIN RESEARCH")

    def failed(self, message):
        self.status.setText("Research failed. Previous saved reports are unaffected.")
        self.output.setPlainText(message)

    def stopped(self, message):
        self.status.setText(message)
        self.output.setPlainText("Cancelled. No partial report was published.")

    def completed(self, result):
        self.last_report = result["report_path"]
        self.last_sources = result.get("sources_path")
        self.open_report.setEnabled(True)
        self.open_sources.setEnabled(bool(self.last_sources))
        state = result.get("evidence_status", "unknown")
        self.status.setText("Research finished. Evidence status: " + state)
        report = html.escape(result["report"]).replace("\n", "<br>")
        links = []
        for number, source in enumerate(result["sources"], start=1):
            title = html.escape(str(source.get("title", "Source")))
            url = html.escape(str(source.get("url", "")), quote=True)
            kind = html.escape(str(source.get("evidence_kind", "unknown")))
            links.append(f'{number}. <a href="{url}">{title}</a> ({kind})')
        self.output.setHtml(
            "<h2>Deep Forage Report</h2><p>" + report + "</p><hr>"
            "<h3>Evidence sources</h3>" + "<br>".join(links)
            + "<hr><p>Saved: " + html.escape(self.last_report) + "</p>"
        )
        self.refresh_history()

    def export_to(self, workspace):
        path = self.last_report or self.history.currentData()
        if not path:
            self.status.setText("No completed research report to export.")
            return
        folder = QFileDialog.getExistingDirectory(
            self, f"Choose destination folder for {workspace.title()} report",
            str(Path.home() / "Documents")
        )
        if not folder:
            return
        try:
            exported = export_report(path, workspace, folder, research_root=REPORT_DIR)
        except (OSError, ValueError) as error:
            self.status.setText(f"Export blocked: {error}")
            return
        self.status.setText("Explicit export saved: " + exported)

    @staticmethod
    def _open(path):
        if path and Path(path).is_file() and not Path(path).is_symlink():
            subprocess.Popen(["xdg-open", path], start_new_session=True)

    def open_saved_report(self):
        self._open(self.last_report)

    def open_saved_sources(self):
        self._open(self.last_sources)

    def open_history(self):
        path = self.history.currentData()
        self._open(path)


def main():
    initial = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    app = QApplication(sys.argv)
    app.setApplicationName("Deep Forage")
    window = DeepForageWindow(initial)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
