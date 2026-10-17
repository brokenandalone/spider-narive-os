"""Owner-facing Webbie focus task editor across Spider OS workspaces."""
from pathlib import Path
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QMessageBox, QPushButton, QVBoxLayout,
)

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"webbie/brain"))
from focus_tasks import (WORKSPACES, add_task, change_task,
                         delete_task, list_tasks, current_focus)


class WebbieFocusDialog(QDialog):
    """No models, speech, screenshots, networking, or automatic execution."""
    def __init__(self, parent=None, *, workspace="default"):
        super().__init__(parent)
        self.setWindowTitle("Webbie · Focus and Projects")
        self.setMinimumWidth(570)
        self.setMinimumHeight(430)
        self.setStyleSheet("""
            QDialog { background:#120d18; color:#f5eff8; }
            QLabel { color:#f5eff8; }
            QListWidget, QLineEdit, QComboBox {
                color:#f5eff8; background:#24162f;
                border:1px solid #8751b5; padding:7px; }
            QPushButton { background:#6d28d9; color:white; padding:9px;
                border-radius:6px; }
        """)
        self.workspace=QComboBox()
        for name in sorted(WORKSPACES):
            self.workspace.addItem(name.replace("-", " ").title(),name)
        self.choose_workspace(workspace)
        root=QVBoxLayout(self)
        intro=QLabel(
            "Your own active tasks and next steps. Nothing entered here "
            "automatically runs a program, changes files, or contacts a website. "
            "Webbie can use these titles as temporary planning context.")
        intro.setWordWrap(True)
        root.addWidget(intro)
        form=QFormLayout(); root.addLayout(form)
        self.workspace.currentIndexChanged.connect(self.refresh)
        form.addRow("Workspace",self.workspace)
        self.title=QLineEdit()
        self.title.setMaxLength(100)
        self.title.setPlaceholderText("e.g. Mix the next Broken Sorrow track")
        form.addRow("Project or task",self.title)
        self.next_step=QLineEdit()
        self.next_step.setMaxLength(180)
        self.next_step.setPlaceholderText("e.g. Review the recorded guitar takes")
        form.addRow("Next step",self.next_step)
        row=QHBoxLayout(); root.addLayout(row)
        add=QPushButton("Add focus task")
        add.clicked.connect(self.create_task); row.addWidget(add)
        save=QPushButton("Save selected next step")
        save.clicked.connect(self.update_step); row.addWidget(save)
        self.items=QListWidget()
        self.items.setAccessibleName("Webbie owner focus tasks")
        root.addWidget(self.items)
        row2=QHBoxLayout(); root.addLayout(row2)
        for text,status in (("Resume","active"),("Pause","paused"),("Mark done","done")):
            button=QPushButton(text)
            button.clicked.connect(lambda _, s=status:self.change_status(s))
            row2.addWidget(button)
        delete=QPushButton("Delete selected")
        delete.clicked.connect(self.remove_selected)
        row2.addWidget(delete)
        close=QPushButton("Close")
        close.clicked.connect(self.close)
        root.addWidget(close)
        self.refresh()

    def choose_workspace(self, workspace):
        index=self.workspace.findData(workspace)
        self.workspace.setCurrentIndex(index if index>=0 else
                                       self.workspace.findData("default"))

    def refresh(self, *args):
        self.items.clear()
        selected=self.workspace.currentData()
        if selected is None:
            return
        items=list_tasks(workspace=selected)
        for item in sorted(items,key=lambda i:i["updated"],reverse=True):
            shown=f'{item["status"].upper()}  {item["title"]}  |  Next: {item["next_step"]}'
            self.items.addItem(shown)
            self.items.item(self.items.count()-1).setData(Qt.UserRole,item["id"])

    def _selected_id(self):
        selected=self.items.currentItem()
        return selected.data(Qt.UserRole) if selected is not None else None

    def _write(self, callback):
        try:
            callback()
        except (OSError, PermissionError, ValueError) as error:
            QMessageBox.warning(self,"Focus not updated",str(error))
            return
        self.refresh()

    def create_task(self):
        def action():
            add_task(self.workspace.currentData(),self.title.text(),
                     self.next_step.text())
            self.title.clear()
            self.next_step.clear()
        self._write(action)

    def update_step(self):
        identifier=self._selected_id()
        if identifier is not None:
            self._write(lambda:change_task(identifier,next_step=self.next_step.text()))

    def change_status(self,status):
        identifier=self._selected_id()
        if identifier is not None:
            self._write(lambda:change_task(identifier,status=status))

    def remove_selected(self):
        identifier=self._selected_id()
        if identifier is None:
            return
        if QMessageBox.question(
                self,"Delete focus task?",
                "Remove this saved local focus task? No other file is changed.",
                QMessageBox.Yes|QMessageBox.No,QMessageBox.No)==QMessageBox.Yes:
            self._write(lambda:delete_task(identifier))
