"""Manually controlled steps for one Study assignment; no school submission."""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QAbstractItemView, QPushButton, QInputDialog, QMessageBox,
)
try:
    from .milestones import STARTER_STEPS, valid_step
except ImportError:
    from milestones import STARTER_STEPS, valid_step


class MilestonesDialog(QDialog):
    def __init__(self, store, assignment_id, parent=None):
        super().__init__(parent)
        self.store = store
        self.assignment_id = assignment_id
        assignment = store.assignment_record(assignment_id)
        if assignment is None:
            raise ValueError("This assignment no longer exists.")
        self.setWindowTitle("Study | Checklist: " + assignment["title"])
        self.resize(760, 520)
        layout = QVBoxLayout(self)
        self.summary = QLabel()
        layout.addWidget(self.summary)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Step", "Personal target date", "Status"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        buttons = QHBoxLayout()
        for caption, method in [
            ("Add step", self.add_step),
            ("Starter checklist", self.add_starter),
            ("Mark done", self.mark_done),
            ("Reopen", self.reopen),
            ("Delete selected", self.delete_selected),
        ]:
            button = QPushButton(caption)
            button.clicked.connect(method)
            buttons.addWidget(button)
        layout.addLayout(buttons)
        notice = QLabel("Target dates are your own planning dates, not verified SNHU deadlines.")
        notice.setWordWrap(True)
        layout.addWidget(notice)
        self.refresh()

    def refresh(self):
        rows = self.store.assignment_steps(self.assignment_id)
        self.table.setRowCount(0)
        for entry in rows:
            index = self.table.rowCount()
            self.table.insertRow(index)
            title = QTableWidgetItem(entry["title"])
            title.setData(Qt.UserRole, entry["id"])
            self.table.setItem(index, 0, title)
            self.table.setItem(index, 1, QTableWidgetItem(entry["due"]))
            self.table.setItem(index, 2, QTableWidgetItem(
                "Done" if entry["completed"] else "To do"))
        done = sum(int(r["completed"]) for r in rows)
        self.summary.setText(f"{done}/{len(rows)} steps completed")

    def selected_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def add_step(self):
        title, ok = QInputDialog.getText(self, "Add checklist step", "Step description:")
        if not ok:
            return
        due, ok = QInputDialog.getText(
            self, "Personal target date", "Optional YYYY-MM-DD, or blank:")
        if not ok:
            return
        try:
            title, due = valid_step(title, due)
            if not self.store.add_assignment_step(self.assignment_id, title, due):
                QMessageBox.information(self, "Checklist", "That step already exists.")
            self.refresh()
        except ValueError as error:
            QMessageBox.warning(self, "Checklist", str(error))

    def add_starter(self):
        proposed = "\n".join("• " + step for step in STARTER_STEPS)
        if QMessageBox.question(
                self, "Add starter steps",
                "Add a generic writing checklist? Adjust it to your actual rubric. "
                "Existing steps won't be duplicated.\n\n" + proposed) != QMessageBox.Yes:
            return
        self.store.add_assignment_steps(self.assignment_id, [(s, "") for s in STARTER_STEPS])
        self.refresh()

    def mark_done(self):
        self.update_status(True)

    def reopen(self):
        self.update_status(False)

    def update_status(self, completed):
        step_id = self.selected_id()
        if step_id is None:
            return
        self.store.set_step_completed(self.assignment_id, step_id, completed)
        self.refresh()

    def delete_selected(self):
        step_id = self.selected_id()
        if step_id is None:
            return
        if QMessageBox.question(
                self, "Remove step", "Remove this planning step?") == QMessageBox.Yes:
            self.store.delete_assignment_step(self.assignment_id, step_id)
            self.refresh()
