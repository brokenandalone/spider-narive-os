#!/usr/bin/env python3
"""Spider Operations Hub: owner-click-only cross-workspace controls.

This interface cannot install packages, change services, edit documents,
start recording, or act on a model/voice suggestion. It requires GUI clicks.
"""
from __future__ import annotations
from datetime import datetime
import json
import os
from pathlib import Path
import sys

from PyQt5.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel, QMessageBox,
    QPlainTextEdit, QPushButton, QTabWidget, QVBoxLayout, QWidget,
)

from operations_quality import (
    manuscript_report, research_sources_report, study_report, wav_report,
)
from operations_services import kali_status, launch_workspace, system_status
from operations_batch import (
    studio_session_report, author_chapter_folder_report,
    study_assignment_folder_report,
)
from operations_wave8_ui import Wave8Panel
from operations_wave8_projects_ui import ProjectBoard
from wave9_ui import Wave9Panel


class OperationsHub(QWidget):
    def __init__(self):
        super().__init__()
        self.last_report = None
        self.views = {}
        self.setWindowTitle("Spider OS | Operations Hub")
        self.setObjectName("spiderOperationsHub")
        self._fit_screen()
        self.setStyleSheet("""
            QWidget {background-color:#171124;color:#f4effa;
                     font-size:12px;}
            QLabel {color:#f4effa;}
            QTabWidget::pane {border:1px solid #62448d;}
            QTabBar::tab {background:#322147;color:#f4effa;
                          border:1px solid #6d4a99;padding:9px 14px;}
            QTabBar::tab:selected {background:#7147a0;}
            QPlainTextEdit {background:#110e19;color:#efeafb;
                            border:1px solid #694c92;padding:8px;}
            QPushButton {background:#61398b;color:white;
                         padding:10px;border:1px solid #9069bd;
                         border-radius:5px;}
            QPushButton:hover {background:#8054ac;}
        """)
        main = QVBoxLayout(self)
        title = QLabel("SPIDER OS  /  OPERATIONS HUB")
        title.setStyleSheet("font-size:20px;font-weight:bold;color:#d7baff;")
        main.addWidget(title)
        note = QLabel(
            "Review projects and launch existing workspaces. No installs, "
            "recording, network research, container changes or Webbie restarts."
        )
        note.setWordWrap(True)
        main.addWidget(note)
        self.tabs = QTabWidget()
        self.tabs.setUsesScrollButtons(True)
        main.addWidget(self.tabs, 1)
        self._overview()
        self._studio()
        self._author()
        self._study()
        self._forage()
        self._kali()
        self._system()
        self.wave8 = Wave8Panel(self._publish, self)
        self.tabs.addTab(self.wave8, "Wave 8")
        self.views["Wave 8"] = self.wave8.report
        self.projects = ProjectBoard(self._publish, self)
        self.tabs.addTab(self.projects, "Projects")
        self.views["Projects"] = self.projects.report
        self.wave9 = Wave9Panel(self._publish, self)
        self.tabs.addTab(self.wave9, "Wave 9")
        self.views["Wave 9"] = self.wave9.report
        footer = QHBoxLayout()
        self.summary_status = QLabel("Waiting for an owner-selected operation.")
        self.summary_status.setWordWrap(True)
        footer.addWidget(self.summary_status, 1)
        export = QPushButton("Save latest summary...")
        export.clicked.connect(self.save_summary)
        footer.addWidget(export)
        main.addLayout(footer)

    def _fit_screen(self):
        screen = QApplication.primaryScreen()
        if not screen:
            self.resize(900, 670)
            return
        area = screen.availableGeometry()
        width = max(320, min(1040, int(area.width() * 0.86)))
        height = max(300, min(750, int(area.height() * 0.85)))
        self.resize(min(width, area.width()), min(height, area.height()))
        self.move(
            area.x() + max(0, (area.width() - self.width()) // 2),
            area.y() + max(0, (area.height() - self.height()) // 2),
        )

    def _page(self, name, explanation):
        page = QWidget()
        box = QVBoxLayout(page)
        label = QLabel(explanation)
        label.setWordWrap(True)
        box.addWidget(label)
        view = QPlainTextEdit()
        view.setReadOnly(True)
        view.setPlaceholderText("Choose an operation to see its read-only report.")
        self.views[name] = view
        self.tabs.addTab(page, name)
        return box, view

    def _button(self, row, name, handler):
        button = QPushButton(name)
        button.clicked.connect(handler)
        row.addWidget(button)
        return button

    def _publish(self, name, report):
        self.last_report = dict(report)
        self.views[name].setPlainText(
            json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True)
        )
        self.summary_status.setText(f"{name}: report ready. Nothing was modified.")

    def _error(self, operation, error):
        self.summary_status.setText(f"{operation}: unable to complete.")
        QMessageBox.warning(
            self, "Operations Hub", f"{operation} failed:\n{error}"
        )

    def _run(self, name, operation):
        try:
            report = operation()
            self._publish(name, report)
        except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
            self._error(name, error)

    def _pick(self, name, title, mask, operation):
        filename, _ = QFileDialog.getOpenFileName(self, title, str(Path.home()), mask)
        if filename:
            self._run(name, lambda: operation(filename))

    def _pick_folder(self, name, title, operation):
        directory = QFileDialog.getExistingDirectory(self, title, str(Path.home()))
        if directory:
            self._run(name, lambda: operation(directory))

    def _overview(self):
        box, _ = self._page(
            "Home", "Launch only an installed workspace you select. "
            "The Web itself is intentionally not started a second time."
        )
        for group in (("Studio", "Author", "Study"),
                      ("Forage", "Deep Forage", "Kali Bay")):
            row = QHBoxLayout()
            box.insertLayout(box.count() - 1, row)
            for workspace in group:
                self._button(
                    row, f"Open {workspace}",
                    lambda checked=False, name=workspace: self.open_workspace(name)
                )

    def open_workspace(self, name):
        try:
            pid = launch_workspace(name)
            self._publish("Home", {
                "operation": "open_workspace",
                "workspace": name,
                "launcher_pid": pid,
                "note": "Launch submitted. Verify that the actual window opened.",
            })
        except (OSError, ValueError, RuntimeError, PermissionError) as error:
            self._error(f"Open {name}", error)

    def _studio(self):
        box, _ = self._page(
            "Studio", "Inspect the start and end of a WAV recording for PCM format, "
            "sample peak and rough RMS. Does not render, play, or alter audio."
        )
        row = QHBoxLayout()
        box.insertLayout(box.count() - 1, row)
        self._button(
            row, "Choose WAV for quality preflight...",
            lambda: self._pick("Studio", "Choose PCM WAV",
                               "WAV audio (*.wav)", wav_report)
        )

        self._button(
            row, "Audit WAV stem folder...",
            lambda: self._pick_folder("Studio", "Choose recording stem folder",
                                      studio_session_report)
        )

    def _author(self):
        box, _ = self._page(
            "Author", "Check approximate chapters, headings and editorial placeholders "
            "in a TXT or Markdown manuscript. Does not access the Author database."
        )
        row = QHBoxLayout()
        box.insertLayout(box.count() - 1, row)
        self._button(
            row, "Choose manuscript...",
            lambda: self._pick("Author", "Choose manuscript",
                               "Text manuscripts (*.txt *.md *.markdown)",
                               manuscript_report)
        )

        self._button(
            row, "Review chapter folder...",
            lambda: self._pick_folder("Author", "Choose chapter folder",
                                      author_chapter_folder_report)
        )

    def _study(self):
        box, _ = self._page(
            "Study", "Optional directions can contain an explicit word range. "
            "Checks are indicators only, never a grade or APA certification."
        )
        directions_label = QLabel("Assignment directions (optional, stays in this window):")
        box.insertWidget(1, directions_label)
        self.directions = QPlainTextEdit()
        self.directions.setMaximumHeight(90)
        self.directions.setPlaceholderText("Example: 800 to 1000 words")
        box.insertWidget(2, self.directions)
        row = QHBoxLayout()
        box.insertLayout(box.count() - 1, row)
        self._button(
            row, "Choose TXT/Markdown draft...",
            lambda: self._pick(
                "Study", "Choose assignment draft", "Text drafts (*.txt *.md *.markdown)",
                lambda path: study_report(path, self.directions.toPlainText()),
            )
        )

        self._button(
            row, "Review assignment folder...",
            lambda: self._pick_folder("Study", "Choose assignment draft folder",
                                      study_assignment_folder_report)
        )

    def _forage(self):
        box, _ = self._page(
            "Forage", "Review a saved Deep Forage .sources.json export. "
            "Checks source metadata and duplicates without opening any URL."
        )
        row = QHBoxLayout()
        box.insertLayout(box.count() - 1, row)
        self._button(
            row, "Choose saved sources JSON...",
            lambda: self._pick(
                "Forage", "Choose saved research sources",
                "Research sources (*.json)", research_sources_report
            )
        )

    def _kali(self):
        box, _ = self._page(
            "Kali", "Checks the existing Kali Bay container and Purple executable "
            "inventory only. Never creates, starts, upgrades or scans."
        )
        row = QHBoxLayout()
        box.insertLayout(box.count() - 1, row)
        self._button(row, "Inspect Kali Purple readiness", lambda: self._run("Kali", kali_status))

    def _system(self):
        box, _ = self._page(
            "System", "Read-only application presence, disk space and user service states. "
            "Does not restart Webbie, KDE or the operating system."
        )
        row = QHBoxLayout()
        box.insertLayout(box.count() - 1, row)
        self._button(row, "Refresh system status", lambda: self._run("System", system_status))

    def closeEvent(self, event):
        if ((self.wave8.worker is not None and self.wave8.worker.isRunning())
                or self.wave9.is_busy()):
            QMessageBox.information(
                self, "Review is finishing",
                "Please close the Hub after the selected local review completes."
            )
            event.ignore()
            return
        super().closeEvent(event)

    def save_summary(self):
        if self.last_report is None:
            QMessageBox.information(self, "No report", "Run a check before saving.")
            return
        suggestion = "Spider_Operations_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".json"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save metadata-only report", str(Path.home() / suggestion),
            "JSON (*.json)",
        )
        if not path:
            return
        target = Path(path).expanduser()
        if target.is_symlink() or target.exists():
            QMessageBox.warning(self, "Not saved", "Choose a new filename. Existing files are never replaced.")
            return
        try:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            fd = os.open(target, flags, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(self.last_report, stream, indent=2, ensure_ascii=False)
                stream.write("\n")
            self.summary_status.setText("Summary saved with private file permissions.")
        except OSError as error:
            self._error("Save summary", error)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Spider Operations Hub")
    window = OperationsHub()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
