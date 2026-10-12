"""Owner-reviewed Webbie unified workflow panel for one local focus task.

Brings Brain (focus), Eyes (consented local screenshot), Hands (the existing
confined operator) and Autopilot (tracked supervised steps) into one UI.
It never simulates mouse, runs shell commands, activates cameras, or approves
desktop grants. Every transition comes from an explicit GUI click or a trusted
Computer Control signal; screen/model text is not an instruction.
"""
from PyQt5.QtWidgets import (
    QDialog,QLabel,QPushButton,QTextEdit,QVBoxLayout,QHBoxLayout,QMessageBox,
)
from PyQt5.QtCore import QTimer
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"webbie/brain"))
from focus_tasks import current_focus
from unified_workflow import UnifiedWorkflow


class WebbieUnifiedWorkflowDialog(QDialog):
    def __init__(self,parent=None,*,session=None,workspace_callback=None,
                 computer_callback=None,stop_callback=None):
        super().__init__(parent)
        self.session=session or UnifiedWorkflow()
        self.workspace_callback=workspace_callback or (lambda:"default")
        self.computer_callback=computer_callback
        self.stop_callback=stop_callback
        self.setWindowTitle("Webbie · Unified Workflow")
        self.setObjectName("webbieUnifiedWorkflow")
        self.resize(615,530)
        self.setStyleSheet("""
            QDialog {background:#120d18;color:#f5eff8}
            QLabel {color:#f5eff8}
            QTextEdit {background:#20162b;color:#f5eff8;
                       border:1px solid #6d28d9;padding:10px}
            QPushButton {background:#5b21b6;color:white;padding:10px;
                         border-radius:7px}
            QPushButton:disabled {background:#35253d;color:#aa9db5}
        """)
        layout=QVBoxLayout(self)
        heading=QLabel("WEBBIE · BRAIN + EYES + HANDS + AUTOPILOT")
        heading.setStyleSheet("font-size:17px;font-weight:bold;color:#c4b5fd")
        layout.addWidget(heading)
        intro=QLabel(
            "A guided workflow, not autonomous PC control. "
            "Select an existing task, inspect an authorized window, review "
            "an action, and verify the result. STOP revokes the workflow.")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.report=QTextEdit()
        self.report.setObjectName("webbieWorkflowReport")
        self.report.setReadOnly(True)
        layout.addWidget(self.report)
        first=QHBoxLayout();layout.addLayout(first)
        self.start_button=QPushButton("Start current focus task")
        self.start_button.setObjectName("webbieWorkflowStart")
        self.start_button.clicked.connect(self.start_task)
        first.addWidget(self.start_button)
        self.open_button=QPushButton("Open Computer Control")
        self.open_button.setObjectName("webbieWorkflowComputer")
        self.open_button.clicked.connect(self.open_computer)
        first.addWidget(self.open_button)
        second=QHBoxLayout();layout.addLayout(second)
        self.confirm_button=QPushButton("I verified the result")
        self.confirm_button.setObjectName("webbieWorkflowVerify")
        self.confirm_button.clicked.connect(self.confirm)
        second.addWidget(self.confirm_button)
        self.retry_button=QPushButton("Review again")
        self.retry_button.clicked.connect(self.retry)
        second.addWidget(self.retry_button)
        self.stop_button=QPushButton("STOP workflow")
        self.stop_button.setObjectName("webbieWorkflowStop")
        self.stop_button.clicked.connect(self.cancel)
        second.addWidget(self.stop_button)
        self.timer=QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1000)
        self.refresh()

    def workspace(self):
        return self.workspace_callback()

    def start_task(self):
        work=self.workspace()
        try:
            item=current_focus(work)
            if not item:
                self.report.setPlainText(
                    "No active focus task for this workspace. "
                    "Create one using My Focus Tasks first.")
                return
            # Starting a new session discards all previous action outcomes.
            self.session.begin(item,workspace=work)
        except (OSError,ValueError,PermissionError):
            self.report.setPlainText(
                "Could not start an active owner-created focus task.")
            return
        self.refresh()

    def open_computer(self):
        state=self.session.snapshot(workspace=self.workspace())
        if state["phase"] not in ("observe","review_action"):
            self.refresh()
            return
        if callable(self.computer_callback):
            self.computer_callback()
        self.refresh()

    def confirm(self):
        state=self.session.snapshot(workspace=self.workspace())
        if state["phase"]!="verify":
            self.refresh()
            return
        choice=QMessageBox.question(
            self,"Confirm completed work?",
            "Did YOU inspect the actual result in the application and "
            "confirm the requested change worked? Webbie cannot infer "
            "completion from a dispatched command or model description.",
            QMessageBox.Yes|QMessageBox.No,QMessageBox.No)
        if choice==QMessageBox.Yes:
            self.session.confirm_result(
                owner_confirmed=True,workspace=self.workspace())
        self.refresh()

    def retry(self):
        self.session.retry(owner_clicked=True,workspace=self.workspace())
        self.refresh()

    def cancel(self):
        self.session.stop()
        if callable(self.stop_callback):
            self.stop_callback()
        self.refresh()

    def refresh(self):
        state=self.session.snapshot(workspace=self.workspace())
        lines=[
            "Workspace: "+self.workspace(),
            "Task: "+(state["task_title"] or "No active unified task"),
            "Stage: "+state["phase"].replace("_"," ").upper(),
            "Next: "+state["next_step"],
            "Screen observation (consented): "+
                ("reported" if state["observation_reported"] else "not reported"),
            "Desktop operation: "+(state["last_action"] or "none"),
            "Last outcome: "+(state["last_outcome"] or "none"),
            "Owner confirmed completion: "+("YES" if state["completed"] else "NO"),
            "",
            "No workspace, model, webcam, browser or page can authorize an action.",
            "Computer Control requires its own task grant and window permission.",
            "STOP revokes desktop approvals. Closing this panel also stops active control.",
        ]
        self.report.setPlainText("\n".join(lines))
        self.open_button.setEnabled(state["phase"] in ("observe","review_action"))
        self.confirm_button.setEnabled(state["phase"]=="verify")
        self.retry_button.setEnabled(state["phase"]=="verify")
        self.start_button.setEnabled(True)

    def showEvent(self,event):
        if not self.timer.isActive():
            self.timer.start(1000)
        super().showEvent(event)

    def closeEvent(self,event):
        self.timer.stop()
        self.session.stop()
        if callable(self.stop_callback):
            self.stop_callback()
        super().closeEvent(event)
