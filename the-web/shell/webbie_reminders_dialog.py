"""Visible, owner-operated local reminder editor for Spider OS Webbie."""
from pathlib import Path
import sys

from PyQt5.QtCore import Qt, QDateTime
from PyQt5.QtWidgets import (
    QComboBox, QDateTimeEdit, QDialog, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QMessageBox, QPushButton, QVBoxLayout,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "webbie/agent"))
from local_reminders import add_reminder, delete_reminder, list_reminders


class WebbieRemindersDialog(QDialog):
    """All reminder mutations originate from this explicit local GUI."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Webbie · My Local Reminders")
        self.setMinimumWidth(500)
        self.setStyleSheet("""
            QDialog { background: #120d18; color: #f5eff8; }
            QLabel { color: #f5eff8; }
            QLineEdit, QDateTimeEdit, QComboBox, QListWidget {
                color: #f5eff8; background: #24162f;
                border: 1px solid #8751b5; padding: 7px; }
            QPushButton { color: white; background: #6d28d9;
                border-radius: 6px; padding: 9px; }
        """)
        root = QVBoxLayout(self)
        note = QLabel(
            "Reminders are stored only on this PC. Webbie will notify you "
            "when the desktop is active, she is awake, and quiet hours end. "
            "These are not live calendar or recovery-meeting lookups.")
        note.setWordWrap(True)
        root.addWidget(note)
        self.items = QListWidget()
        self.items.setAccessibleName("Saved Webbie reminders")
        root.addWidget(self.items)
        self.title_field = QLineEdit()
        self.title_field.setMaxLength(100)
        self.title_field.setPlaceholderText("What should Webbie remind you about?")
        root.addWidget(self.title_field)
        self.when_field = QDateTimeEdit()
        self.when_field.setCalendarPopup(True)
        self.when_field.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.when_field.setDateTime(QDateTime.currentDateTime().addSecs(3600))
        root.addWidget(self.when_field)
        self.repeat_field = QComboBox()
        self.repeat_field.addItem("Once", "once")
        self.repeat_field.addItem("Every day", "daily")
        self.repeat_field.addItem("Every week", "weekly")
        root.addWidget(self.repeat_field)
        controls = QHBoxLayout()
        root.addLayout(controls)
        create = QPushButton("Add reminder")
        create.clicked.connect(self.create_reminder)
        controls.addWidget(create)
        delete = QPushButton("Remove selected")
        delete.clicked.connect(self.remove_selected)
        controls.addWidget(delete)
        close = QPushButton("Close")
        close.clicked.connect(self.close)
        controls.addWidget(close)
        self.refresh()

    def refresh(self):
        self.items.clear()
        for item in list_reminders():
            when = item["due"].replace("T", " ")
            label = (f'{item["title"]}  |  {when}  |  '
                     f'{item["repeat"].capitalize()}')
            self.items.addItem(label)
            self.items.item(self.items.count() - 1).setData(
                Qt.UserRole, item["id"])

    def create_reminder(self):
        try:
            add_reminder(
                self.title_field.text(),
                self.when_field.dateTime().toString("yyyy-MM-ddTHH:mm"),
                self.repeat_field.currentData(),
            )
        except (OSError, PermissionError, ValueError) as error:
            QMessageBox.warning(self, "Reminder not saved", str(error))
            return
        self.title_field.clear()
        self.refresh()

    def remove_selected(self):
        item = self.items.currentItem()
        if item is None:
            return
        identifier = item.data(Qt.UserRole)
        try:
            deleted = delete_reminder(identifier)
        except (OSError, PermissionError, ValueError) as error:
            QMessageBox.warning(self, "Reminder not removed", str(error))
            return
        if deleted:
            self.refresh()
