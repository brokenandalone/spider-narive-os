"""Working native mission desk inside each Spider OS bay, not a launcher.

Only deliberate local edits to mission state; source files, user projects,
OS services, user accounts and the desktop are never modified.
"""
from pathlib import Path

from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QListWidget,
    QListWidgetItem, QLineEdit, QPushButton, QComboBox, QFileDialog,
    QMessageBox, QInputDialog, QScrollArea,
)

from bay_missions import MissionStore, BLUEPRINTS, BAYS, STATUSES


class BayMissionPanel(QWidget):
    def __init__(self, bay, parent=None, store=None):
        super().__init__(parent)
        if bay not in BAYS:
            raise ValueError("Unknown native bay")
        self.bay = bay
        self.store = store if store is not None else MissionStore()
        self.projects = []
        self.setObjectName("spiderNativeMissionDesk")
        outer = QVBoxLayout(self)
        heading = QLabel(BLUEPRINTS[bay][0].upper() + " / MISSION DESK")
        heading.setStyleSheet("font-size:20px;font-weight:bold;color:#f4e8f3")
        outer.addWidget(heading)
        info = QLabel(
            "Projects, goals and follow-through inside the actual bay. "
            "No extra desktop shortcuts. Your mission list stays on this computer.")
        info.setWordWrap(True)
        outer.addWidget(info)

        self.status_line = QLabel("")
        self.status_line.setWordWrap(True)
        outer.addWidget(self.status_line)

        quick = QGroupBox("Start real work")
        quick_layout = QVBoxLayout(quick)
        suggestions = QComboBox()
        suggestions.addItems(BLUEPRINTS[bay][1])
        self.suggestions = suggestions
        quick_layout.addWidget(suggestions)
        start = QPushButton("Add selected mission to this bay")
        start.setMinimumHeight(42)
        start.clicked.connect(self.add_suggested)
        quick_layout.addWidget(start)
        outer.addWidget(quick)

        entry = QHBoxLayout()
        self.title = QLineEdit()
        self.title.setPlaceholderText("New project, goal or research question")
        self.title.setAccessibleName("Mission title")
        self.title.returnPressed.connect(self.add_typed)
        entry.addWidget(self.title, 1)
        add = QPushButton("Add mission")
        add.setMinimumHeight(42)
        add.clicked.connect(self.add_typed)
        entry.addWidget(add)
        outer.addLayout(entry)

        self.list = QListWidget()
        self.list.setMinimumHeight(180)
        self.list.setAccessibleName("Local missions for " + bay)
        self.list.currentItemChanged.connect(self.update_actions)
        outer.addWidget(self.list, 1)

        controls = QHBoxLayout()
        self.status = QComboBox()
        self.status.addItems(["next", "active", "blocked", "done"])
        self.status.setAccessibleName("Mission status")
        controls.addWidget(self.status)
        self.change_button = QPushButton("Update status")
        self.change_button.clicked.connect(self.change_status)
        controls.addWidget(self.change_button)
        self.folder_button = QPushButton("Open project folder")
        self.folder_button.clicked.connect(self.open_folder)
        controls.addWidget(self.folder_button)
        outer.addLayout(controls)

        movement = QHBoxLayout()
        self.destination = QComboBox()
        for ident, (name, _) in BLUEPRINTS.items():
            if ident != bay:
                self.destination.addItem(name, ident)
        movement.addWidget(self.destination, 1)
        handoff = QPushButton("Move to bay")
        handoff.clicked.connect(self.move_mission)
        self.handoff_button = handoff
        movement.addWidget(handoff)
        outer.addLayout(movement)

        footer = QHBoxLayout()
        bind = QPushButton("Attach an existing project folder")
        bind.clicked.connect(self.attach_folder)
        footer.addWidget(bind)
        delete = QPushButton("Remove selected mission")
        delete.clicked.connect(self.remove_mission)
        self.delete_button = delete
        footer.addWidget(delete)
        outer.addLayout(footer)
        self.refresh()

    def selected(self):
        item = self.list.currentItem()
        ident = item.data(Qt.UserRole) if item else None
        return next((entry for entry in self.projects if entry["id"] == ident), None)

    def refresh(self):
        try:
            self.projects = self.store.for_bay(self.bay)
            self.list.clear()
            for mission in self.projects:
                label = "[{}] {}".format(mission["status"].upper(), mission["title"])
                if mission["folder"]:
                    label += "  ·  folder linked"
                widget = QListWidgetItem(label)
                widget.setData(Qt.UserRole, mission["id"])
                self.list.addItem(widget)
            self.status_line.setText(
                "{} missions  ·  {} active  ·  {} complete".format(
                    len(self.projects),
                    sum(m["status"] == "active" for m in self.projects),
                    sum(m["status"] == "done" for m in self.projects)))
            self.update_actions()
        except (OSError, ValueError, TypeError) as error:
            self.status_line.setText("Mission desk unavailable: " + str(error))
            self.projects = []
            self.list.clear()
            self.update_actions()

    def update_actions(self, *_):
        mission = self.selected()
        for control in (self.change_button, self.delete_button, self.handoff_button):
            control.setEnabled(mission is not None)
        self.folder_button.setEnabled(bool(mission and mission["folder"]))
        if mission:
            self.status.setCurrentText(mission["status"])

    def error(self, error):
        QMessageBox.warning(self, "Spider OS mission desk", str(error))

    def add_suggested(self):
        self._add(self.suggestions.currentText())

    def add_typed(self):
        self._add(self.title.text())

    def _add(self, title, folder=""):
        try:
            self.store.add(self.bay, title, folder=folder)
            self.title.clear()
            self.refresh()
        except (OSError, ValueError, KeyError) as error:
            self.error(error)

    def attach_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Choose the local project directory", str(Path.home()))
        if not folder:
            return
        name, accepted = QInputDialog.getText(
            self, "Name this project", "Project name:",
            text=Path(folder).name)
        if accepted and name.strip():
            self._add(name, folder)

    def change_status(self):
        mission = self.selected()
        if not mission:
            return
        try:
            self.store.update(mission["id"], status=self.status.currentText())
            self.refresh()
        except (OSError, KeyError, ValueError) as error:
            self.error(error)

    def move_mission(self):
        mission = self.selected()
        if not mission:
            return
        destination = self.destination.currentData()
        try:
            self.store.update(mission["id"], destination=destination)
            self.refresh()
        except (OSError, KeyError, ValueError) as error:
            self.error(error)

    def open_folder(self):
        mission = self.selected()
        if not mission or not mission["folder"]:
            return
        folder = Path(mission["folder"])
        if folder.is_symlink() or not folder.is_dir():
            self.error("The attached project folder is no longer available.")
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder))):
            self.error("No file manager accepted the project folder.")

    def remove_mission(self):
        mission = self.selected()
        if not mission:
            return
        choice = QMessageBox.question(
            self, "Remove mission?",
            "Remove this mission from the desk? The actual project folder is NOT deleted.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if choice == QMessageBox.Yes:
            try:
                self.store.remove(mission["id"])
                self.refresh()
            except (OSError, KeyError, ValueError) as error:
                self.error(error)
