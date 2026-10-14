"""Manual-only Spider project checklist GUI. No background task or shell execution."""
from __future__ import annotations
import json
from pathlib import Path

from PyQt5.QtWidgets import (
    QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QMessageBox, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
)
from operations_wave8_projects import (
    TEMPLATES, new_plan, mark_step, plan_summary, save_plan, load_plan,
)


class ProjectBoard(QWidget):
    def __init__(self, publish, parent=None):
        super().__init__(parent)
        self.publish = publish
        self.plan = None
        self.setObjectName("spiderOperationsProjects")
        layout = QVBoxLayout(self)
        heading = QLabel(
            "PROJECT BOARD  /  You decide what happens.\n"
            "Create, review and mark steps yourself. Nothing runs automatically."
        )
        heading.setWordWrap(True)
        layout.addWidget(heading)
        row = QHBoxLayout()
        layout.addLayout(row)
        self.template = QComboBox()
        for key, value in TEMPLATES.items():
            self.template.addItem(value[0], key)
        row.addWidget(self.template)
        self.title = QLineEdit()
        self.title.setPlaceholderText("Project name (private)")
        self.title.setMaxLength(90)
        row.addWidget(self.title, 1)
        self.create = QPushButton("Create checklist")
        self.create.clicked.connect(self.create_plan)
        row.addWidget(self.create)
        self.steps = QListWidget()
        self.steps.setObjectName("spiderProjectChecklist")
        layout.addWidget(self.steps, 1)
        controls = QHBoxLayout()
        layout.addLayout(controls)
        complete = QPushButton("Mark selected done / undo")
        complete.clicked.connect(self.toggle_step)
        controls.addWidget(complete)
        load = QPushButton("Open saved plan...")
        load.clicked.connect(self.open_saved)
        controls.addWidget(load)
        save = QPushButton("Save new plan file...")
        save.clicked.connect(self.save_current)
        controls.addWidget(save)
        self.status = QLabel("No active project.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.report = QPlainTextEdit()
        self.report.setReadOnly(True)
        self.report.setMaximumHeight(125)
        layout.addWidget(self.report)

    def refresh(self):
        self.steps.clear()
        if self.plan is None:
            self.status.setText("No active project.")
            return
        for position, step in enumerate(self.plan["steps"], 1):
            label = ("☑ " if step["complete"] else "☐ ") + str(position) + ". " + step["title"]
            self.steps.addItem(label)
        summary = plan_summary(self.plan)
        self.status.setText(
            "Current project: " + self.plan["title"] + " | " +
            str(summary["tasks_completed"]) + "/" + str(summary["tasks_total"]) +
            " steps manually checked"
        )
        self.report.setPlainText(
            json.dumps(summary, indent=2, ensure_ascii=False)
        )
        self.publish("Projects", summary)

    def create_plan(self):
        try:
            self.plan = new_plan(self.template.currentData(), self.title.text())
            self.refresh()
        except ValueError as error:
            QMessageBox.warning(self, "Projects", str(error))

    def toggle_step(self):
        if self.plan is None or self.steps.currentRow() < 0:
            self.status.setText("Select an active checklist step.")
            return
        position = self.steps.currentRow()
        try:
            self.plan = mark_step(
                self.plan, position, not self.plan["steps"][position]["complete"]
            )
            self.refresh()
            self.steps.setCurrentRow(position)
        except ValueError as error:
            QMessageBox.warning(self, "Projects", str(error))

    def open_saved(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open saved Spider project plan", str(Path.home()),
            "JSON plan (*.json)"
        )
        if not filename:
            return
        try:
            proposal = load_plan(filename)
        except (OSError, ValueError, UnicodeError) as error:
            QMessageBox.warning(self, "Projects", f"Unable to load plan: {type(error).__name__}")
            return
        # Never execute contents; only validated literal fixed-step checklists.
        self.plan = proposal
        self.title.setText(proposal["title"])
        index = self.template.findData(proposal["template"])
        if index >= 0:
            self.template.setCurrentIndex(index)
        self.refresh()

    def save_current(self):
        if self.plan is None:
            self.status.setText("Create or load a project first.")
            return
        proposal = "Spider_Project_" + self.plan["id"][:8] + ".json"
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save new private project plan",
            str(Path.home() / proposal), "JSON plan (*.json)"
        )
        if not filename:
            return
        try:
            save_plan(self.plan, filename)
            self.status.setText("Saved with private permissions. Existing files not overwritten.")
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Projects", f"Not saved: {type(error).__name__}")
