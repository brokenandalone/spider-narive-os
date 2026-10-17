"""Actual native utility workspaces embedded into The Web.

No standalone launchers. Device inspection and development diagnostics are
read-only; artwork exports and communications drafts require an explicit save.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit,
    QFileDialog, QMessageBox, QSpinBox, QTableWidget, QTableWidgetItem,
)

from bay_missions import MissionStore, BLUEPRINTS
try:
    from native_feature_adoption import summary_text as native_idea_summary
except ImportError:
    native_idea_summary = None  # Existing bay remains functional without this optional module.


def hardware_summary(sys_root=Path("/sys")):
    """Only read names exposed in public kernel device-class directories."""
    base = Path(sys_root)
    kinds = {
        "Network interfaces": base / "class/net",
        "Audio devices": base / "class/sound",
        "Cameras": base / "class/video4linux",
        "Input devices": base / "class/input",
        "USB nodes": base / "bus/usb/devices",
        "Storage devices": base / "block",
    }
    details = {}
    for kind, location in kinds.items():
        try:
            names = sorted(
                item.name for item in location.iterdir()
                if not item.name.startswith(".")
            )[:40]
        except (OSError, PermissionError):
            names = []
        details[kind] = names
    return details


def git_status(folder):
    """Fixed read-only commands against a user-selected local checkout."""
    folder = Path(folder)
    if not folder.is_dir() or folder.is_symlink():
        raise ValueError("Select an accessible, non-symlinked source directory")
    result = subprocess.run(
        ["git", "-C", str(folder), "status", "--short", "--untracked-files=no"],
        text=True, capture_output=True, timeout=8, check=False,
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
    )
    if result.returncode:
        raise ValueError("Not an accessible Git checkout")
    return result.stdout[:12000] or "Tracked source is clean."


class DevicesPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        body = QVBoxLayout(self)
        title = QLabel("DEVICES / HARDWARE INVENTORY")
        title.setStyleSheet("font-size:20px;font-weight:bold")
        body.addWidget(title)
        body.addWidget(QLabel(
            "Inspect connected hardware without modifying disks, drivers, "
            "network configuration, or USB devices."))
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        body.addWidget(self.output, 1)
        refresh = QPushButton("Refresh connected devices")
        refresh.setMinimumHeight(44)
        refresh.clicked.connect(self.refresh)
        body.addWidget(refresh)
        self.refresh()

    def refresh(self):
        report = hardware_summary()
        self.output.setPlainText("\n\n".join(
            "{} ({}):\n{}".format(
                kind, len(entries), "\n".join("• " + name for name in entries) or "None detected")
            for kind, entries in report.items()))


class ProductivityPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.store = MissionStore()
        body = QVBoxLayout(self)
        title = QLabel("PRODUCTIVITY / THE WHOLE WEB")
        title.setStyleSheet("font-size:20px;font-weight:bold")
        body.addWidget(title)
        info = QLabel("One view of tasks in all bays. No duplicate planner or "
                      "cloud account is required.")
        info.setWordWrap(True)
        body.addWidget(info)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Workspace", "Status", "Mission"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setMinimumHeight(260)
        body.addWidget(self.table, 1)
        self.status = QLabel("")
        body.addWidget(self.status)
        button = QPushButton("Refresh every bay")
        button.clicked.connect(self.refresh)
        body.addWidget(button)
        self.refresh()

    def refresh(self):
        try:
            missions = [m for m in self.store.read() if m["status"] != "done"]
            self.table.setRowCount(len(missions))
            for row, mission in enumerate(missions):
                fields = (BLUEPRINTS[mission["bay"]][0], mission["status"], mission["title"])
                for column, field in enumerate(fields):
                    self.table.setItem(row, column, QTableWidgetItem(field))
            self.table.resizeColumnsToContents()
            self.status.setText("{} unfinished missions across native bays".format(len(missions)))
        except (OSError, ValueError) as error:
            self.status.setText("Planner unavailable: " + str(error))


class ArtLabPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.source = None
        self.pixmap = QPixmap()
        body = QVBoxLayout(self)
        heading = QLabel("ART LAB / IMAGE WORKBENCH")
        heading.setStyleSheet("font-size:20px;font-weight:bold")
        body.addWidget(heading)
        body.addWidget(QLabel("Inspect an original and export a resized copy. Originals are never overwritten."))
        self.preview = QLabel("Choose an image to preview")
        self.preview.setMinimumHeight(220)
        self.preview.setAlignment(Qt.AlignCenter)
        body.addWidget(self.preview, 1)
        row = QHBoxLayout()
        chooser = QPushButton("Open original image")
        chooser.clicked.connect(self.choose)
        row.addWidget(chooser)
        row.addWidget(QLabel("Export width"))
        self.width = QSpinBox()
        self.width.setRange(128, 8000)
        self.width.setValue(2048)
        row.addWidget(self.width)
        self.export_button = QPushButton("Export a new PNG")
        self.export_button.clicked.connect(self.export)
        self.export_button.setEnabled(False)
        row.addWidget(self.export_button)
        body.addLayout(row)
        self.info = QLabel("")
        self.info.setWordWrap(True)
        body.addWidget(self.info)

    def choose(self):
        name, _ = QFileDialog.getOpenFileName(
            self, "Choose existing artwork", str(Path.home() / "Pictures"),
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if not name:
            return
        pixmap = QPixmap(name)
        if pixmap.isNull():
            QMessageBox.warning(self, "Art Lab", "The image could not be opened.")
            return
        self.source = Path(name)
        self.pixmap = pixmap
        self.preview.setPixmap(pixmap.scaled(
            820, 350, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.info.setText("{} × {} pixels  ·  {}".format(
            pixmap.width(), pixmap.height(), self.source.name))
        self.export_button.setEnabled(True)

    def export(self):
        if self.pixmap.isNull() or self.source is None:
            return
        name, _ = QFileDialog.getSaveFileName(
            self, "Export resized copy",
            str(self.source.with_name(self.source.stem + "-export.png")),
            "PNG image (*.png)")
        if not name:
            return
        output = Path(name)
        if output.resolve() == self.source.resolve():
            QMessageBox.warning(self, "Art Lab", "Export cannot overwrite the original artwork.")
            return
        if output.exists():
            result = QMessageBox.question(
                self, "Replace exported file?", "Replace the selected export file?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if result != QMessageBox.Yes:
                return
        scaled = self.pixmap.scaledToWidth(
            self.width.value(), Qt.SmoothTransformation)
        if scaled.save(str(output), "PNG"):
            self.info.setText("Exported a separate copy: " + str(output))
        else:
            QMessageBox.warning(self, "Art Lab", "The image export failed.")


class CommunicationsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        body = QVBoxLayout(self)
        title = QLabel("COMMUNICATIONS / PRIVATE DRAFT DESK")
        title.setStyleSheet("font-size:20px;font-weight:bold")
        body.addWidget(title)
        body.addWidget(QLabel(
            "Draft messages and save locally. No message is sent without using your "
            "chosen email or messaging service."))
        self.editor = QTextEdit()
        self.editor.setPlaceholderText("Write a letter, message, announcement or follow-up...")
        body.addWidget(self.editor, 1)
        self.status = QLabel("")
        body.addWidget(self.status)
        buttons = QHBoxLayout()
        load = QPushButton("Open a text draft")
        load.clicked.connect(self.open_draft)
        buttons.addWidget(load)
        save = QPushButton("Save draft as text")
        save.clicked.connect(self.save_draft)
        buttons.addWidget(save)
        body.addLayout(buttons)

    def open_draft(self):
        if self.editor.document().isModified():
            answer = QMessageBox.question(
                self, "Unsaved draft",
                "Discard unsaved changes before opening another draft?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if answer != QMessageBox.Yes:
                return
        name, _ = QFileDialog.getOpenFileName(
            self, "Open existing draft", str(Path.home() / "Documents"),
            "Text files (*.txt *.md)")
        if not name:
            return
        try:
            path = Path(name)
            if path.is_symlink() or path.stat().st_size > 1024 * 1024:
                raise ValueError("Draft is too large or a symlink")
            self.editor.setPlainText(path.read_text(encoding="utf-8"))
            self.editor.document().setModified(False)
            self.status.setText("Opened: " + str(path))
        except (OSError, UnicodeError, ValueError) as error:
            QMessageBox.warning(self, "Communications", str(error))

    def save_draft(self):
        name, _ = QFileDialog.getSaveFileName(
            self, "Save draft", str(Path.home() / "Documents" / "message-draft.txt"),
            "Text files (*.txt *.md)")
        if not name:
            return
        try:
            path = Path(name)
            if path.is_symlink():
                raise OSError("Cannot overwrite a symlinked file")
            if path.exists():
                answer = QMessageBox.question(
                    self, "Replace draft?", "Replace this local draft?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if answer != QMessageBox.Yes:
                    return
            path.write_text(self.editor.toPlainText(), encoding="utf-8")
            self.editor.document().setModified(False)
            self.status.setText("Saved locally: " + str(path))
        except OSError as error:
            QMessageBox.warning(self, "Communications", str(error))


    def closeEvent(self, event):
        if not self.editor.document().isModified():
            event.accept()
            return
        answer = QMessageBox.warning(
            self, "Unsaved communications draft",
            "Save your changes before leaving this bay?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save)
        if answer == QMessageBox.Cancel:
            event.ignore()
        elif answer == QMessageBox.Discard:
            event.accept()
        else:
            self.save_draft()
            if self.editor.document().isModified():
                event.ignore()
            else:
                event.accept()


class DevBayPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        body = QVBoxLayout(self)
        title = QLabel("DEV BAY / SOURCE CONTROL")
        title.setStyleSheet("font-size:20px;font-weight:bold")
        body.addWidget(title)
        body.addWidget(QLabel(
            "Inspect tracked changes in an existing Git checkout. "
            "This panel never stages, resets, commits or pushes code."))
        self.folder = QLabel("No checkout selected.")
        self.folder.setWordWrap(True)
        body.addWidget(self.folder)
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        body.addWidget(self.output, 1)
        button = QPushButton("Choose checkout and inspect changes")
        button.setMinimumHeight(44)
        button.clicked.connect(self.inspect)
        body.addWidget(button)
        adoption = QPushButton("Show best ideas for Spider OS")
        adoption.setObjectName("spiderNativeFeatureAdoptionButton")
        adoption.setMinimumHeight(44)
        adoption.clicked.connect(self.show_adoption_priorities)
        body.addWidget(adoption)

    def show_adoption_priorities(self):
        if native_idea_summary is None:
            self.output.setPlainText(
                "Feature review is not installed in this source snapshot. "
                "No OS or bay changes made.")
            return
        self.output.setPlainText(native_idea_summary())

    def inspect(self):
        name = QFileDialog.getExistingDirectory(
            self, "Choose existing code checkout", str(Path.home()))
        if not name:
            return
        self.folder.setText(str(name))
        try:
            self.output.setPlainText(git_status(name))
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            self.output.setPlainText("Inspection unavailable: " + str(error))
