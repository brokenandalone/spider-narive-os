"""Local weekly workload view for existing, owner-entered Study assignments."""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QCheckBox,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QPushButton,
    QMessageBox,
)
try:
    from .milestones import weekly_plan, workload_totals
except ImportError:
    from milestones import weekly_plan, workload_totals


class WeeklyPlannerDialog(QDialog):
    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store
        self.setWindowTitle("Study | Weekly workload and next actions")
        self.resize(1080, 680)
        layout = QVBoxLayout(self)
        filters = QHBoxLayout()
        filters.addWidget(QLabel("Time window:"))
        self.window = QComboBox()
        for days in (7, 14, 30):
            self.window.addItem(f"Next {days} days", days)
        self.window.currentIndexChanged.connect(self.refresh)
        filters.addWidget(self.window)
        self.include_completed = QCheckBox("Include completed assignments")
        self.include_completed.toggled.connect(self.refresh)
        filters.addWidget(self.include_completed)
        layout.addLayout(filters)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Course", "Assignment", "Due", "Urgency", "Steps done", "Next action"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.itemDoubleClicked.connect(lambda _: self.open_selected())
        layout.addWidget(self.table, 1)
        bottom = QHBoxLayout()
        refresh = QPushButton("Refresh locally")
        refresh.clicked.connect(self.refresh)
        bottom.addWidget(refresh)
        open_button = QPushButton("Open selected assignment")
        open_button.clicked.connect(self.open_selected)
        bottom.addWidget(open_button)
        layout.addLayout(bottom)
        caution = QLabel("Only dates you entered are displayed. Undated assignments "
                         "remain visible; Study does not fetch or guess SNHU deadlines.")
        caution.setWordWrap(True)
        layout.addWidget(caution)
        self.refresh()

    def refresh(self):
        days = self.window.currentData()
        if days is None:
            return
        rows = weekly_plan(
            self.store.planner_rows(),
            days=days,
            include_completed=self.include_completed.isChecked())
        self.table.setRowCount(0)
        for entry in rows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for index, value in enumerate((
                entry["course"], entry["title"], entry["due"], entry["urgency"],
                entry["progress"], entry["next_action"])):
                item = QTableWidgetItem(str(value))
                if index == 0:
                    item.setData(Qt.UserRole, (entry["id"], entry["course_id"]))
                self.table.setItem(row, index, item)
        totals = workload_totals(rows)
        self.summary.setText(
            f"{totals['visible']} visible assignments · "
            f"{totals['overdue']} overdue · {totals['due_today']} due today · "
            f"{totals['undated']} with no valid date · "
            f"{totals['steps_left']} incomplete checklist steps")

    def open_selected(self):
        index = self.table.currentRow()
        item = self.table.item(index, 0) if index >= 0 else None
        if not item:
            QMessageBox.information(self, "Weekly planner", "Select an assignment.")
            return
        assignment_id, course_id = item.data(Qt.UserRole)
        if self.store.assignment_record(assignment_id) is None:
            self.refresh()
            return
        try:
            if __package__:
                from .assignment_workspace_ui import AssignmentWorkspaceDialog
            else:
                from assignment_workspace_ui import AssignmentWorkspaceDialog
            dialog = AssignmentWorkspaceDialog(
                self.store, assignment_id, self.store.course_folder(course_id), self)
            dialog.exec_()
            self.refresh()
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Weekly planner", str(error))
