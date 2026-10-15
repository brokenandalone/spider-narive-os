"""Manual grade and study-time journal for a selected course."""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTabWidget,
    QWidget, QTableWidget, QTableWidgetItem, QAbstractItemView,
    QMessageBox, QInputDialog,
)
try:
    from .study_progress import grade_summary, session_summary
except ImportError:
    from study_progress import grade_summary, session_summary


class StudyProgressDialog(QDialog):
    def __init__(self, store, course_id, parent=None):
        super().__init__(parent)
        self.store = store
        self.course_id = course_id
        course = store.course(course_id)
        if not course:
            raise ValueError("Select an existing course.")
        self.setWindowTitle("Study | Progress: " + course["name"])
        self.resize(820, 620)
        layout = QVBoxLayout(self)
        intro = QLabel(
            "Private, manually entered progress. These scores and study minutes "
            "are not synchronized to SNHU, and do not represent official grades or GPA.")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        tabs = QTabWidget()
        layout.addWidget(tabs, 1)
        grade_tab = QWidget()
        grade_layout = QVBoxLayout(grade_tab)
        self.grade_summary = QLabel()
        self.grade_summary.setWordWrap(True)
        grade_layout.addWidget(self.grade_summary)
        self.grades = QTableWidget(0, 3)
        self.grades.setHorizontalHeaderLabels(
            ["Assignment", "Due", "Manual earned / possible"])
        self.grades.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.grades.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.grades.horizontalHeader().setStretchLastSection(True)
        grade_layout.addWidget(self.grades)
        grade_actions = QHBoxLayout()
        for title, method in [("Record or update points", self.set_grade),
                              ("Clear manual score", self.clear_grade)]:
            button = QPushButton(title)
            button.clicked.connect(method)
            grade_actions.addWidget(button)
        grade_layout.addLayout(grade_actions)
        tabs.addTab(grade_tab, "My grade tracker")

        session_tab = QWidget()
        session_layout = QVBoxLayout(session_tab)
        self.time_summary = QLabel()
        session_layout.addWidget(self.time_summary)
        self.sessions = QTableWidget(0, 3)
        self.sessions.setHorizontalHeaderLabels(["Recorded", "Topic", "Minutes"])
        self.sessions.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.sessions.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.sessions.horizontalHeader().setStretchLastSection(True)
        session_layout.addWidget(self.sessions)
        time_actions = QHBoxLayout()
        for title, method in [("Log completed study session", self.log_session),
                              ("Remove session entry", self.remove_session)]:
            button = QPushButton(title)
            button.clicked.connect(method)
            time_actions.addWidget(button)
        session_layout.addLayout(time_actions)
        tabs.addTab(session_tab, "Study time journal")

        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        layout.addWidget(close)
        self.refresh()

    def selected_id(self, table):
        row = table.currentRow()
        if row < 0:
            return None
        item = table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def refresh(self):
        scores = self.store.assignment_scores(self.course_id)
        self.grades.setRowCount(0)
        for score in scores:
            row = self.grades.rowCount()
            self.grades.insertRow(row)
            name = QTableWidgetItem(score["title"])
            name.setData(Qt.UserRole, score["id"])
            self.grades.setItem(row, 0, name)
            self.grades.setItem(row, 1, QTableWidgetItem(score["due"]))
            points = (f"{score['earned']} / {score['possible']}"
                      if score["earned"] is not None else "not entered")
            self.grades.setItem(row, 2, QTableWidgetItem(points))
        summary = grade_summary(scores)
        if summary["percentage"] is None:
            self.grade_summary.setText("No manual scores entered yet.")
        else:
            self.grade_summary.setText(
                f"Manual points: {summary['earned']} / {summary['possible']}"
                f" = {summary['percentage']}% across {summary['graded']} scored assignments."
                " This is not your official SNHU course grade.")

        history = self.store.study_sessions(self.course_id)
        self.sessions.setRowCount(0)
        for entry in history:
            row = self.sessions.rowCount()
            self.sessions.insertRow(row)
            stamp = QTableWidgetItem(entry["created_at"])
            stamp.setData(Qt.UserRole, entry["id"])
            self.sessions.setItem(row, 0, stamp)
            self.sessions.setItem(row, 1, QTableWidgetItem(entry["topic"]))
            self.sessions.setItem(row, 2, QTableWidgetItem(str(entry["minutes"])))
        time = session_summary(history)
        self.time_summary.setText(
            f"Last {time['sessions']} logged sessions: "
            f"{time['minutes']} minutes ({time['hours']} hours). "
            "Only sessions you record yourself are counted.")

    def set_grade(self):
        assignment_id = self.selected_id(self.grades)
        if not assignment_id:
            QMessageBox.information(self, "Grade tracker", "Select an assignment row.")
            return
        earned, ok = QInputDialog.getDouble(
            self, "Manual points earned", "Earned points:", 0, 0, 100000, 2)
        if not ok:
            return
        possible, ok = QInputDialog.getDouble(
            self, "Manual points possible", "Possible points:", 100, 0.01, 100000, 2)
        if not ok:
            return
        try:
            self.store.set_assignment_score(assignment_id, earned, possible)
            self.refresh()
        except ValueError as error:
            QMessageBox.warning(self, "Grade tracker", str(error))

    def clear_grade(self):
        assignment_id = self.selected_id(self.grades)
        if not assignment_id:
            return
        if QMessageBox.question(
                self, "Remove manual points",
                "Remove the entered score for this assignment?") == QMessageBox.Yes:
            self.store.clear_assignment_score(assignment_id)
            self.refresh()

    def log_session(self):
        topic, ok = QInputDialog.getText(self, "Log study session",
                                         "What did you study?")
        if not ok:
            return
        minutes, ok = QInputDialog.getInt(
            self, "Study minutes", "Minutes you already studied:", 25, 1, 600)
        if not ok:
            return
        try:
            self.store.add_study_session(self.course_id, topic, minutes)
            self.refresh()
        except ValueError as error:
            QMessageBox.warning(self, "Study session", str(error))

    def remove_session(self):
        session_id = self.selected_id(self.sessions)
        if not session_id:
            return
        if QMessageBox.question(
                self, "Remove logged session",
                "Remove this local study-time entry?") == QMessageBox.Yes:
            self.store.delete_study_session(self.course_id, session_id)
            self.refresh()
