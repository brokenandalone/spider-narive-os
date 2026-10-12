"""Native Webbie Workflow Board. Manual workspace navigation only.

No model, spoken command, room observation or webpage can click the controls.
A selected fixed template is a suggested sequence, not executable automation.
"""
from pathlib import Path
import sys

from PyQt5.QtWidgets import (
    QComboBox, QDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QTextEdit, QVBoxLayout,
)

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "webbie/agent"))
from workflow_board import BLUEPRINTS, WorkflowSession, blueprint_for


class WebbieWorkflowDialog(QDialog):
    def __init__(self, parent=None, *, workspace_opener=None, clock=None):
        super().__init__(parent)
        self.setWindowTitle("Webbie · JARVIS Workflow Board")
        self.setMinimumSize(610, 480)
        self.setObjectName("webbieWorkflowDialog")
        self.workspace_opener = workspace_opener
        self.session = WorkflowSession(clock=clock)
        self.setStyleSheet("""
            QDialog { background:#120d18; color:#f5eff8; }
            QLabel { color:#f5eff8; }
            QTextEdit, QComboBox {
                background:#211529; color:#f5eff8;
                border:1px solid #735098; padding:7px;
            }
            QPushButton { background:#6234a2; color:white; padding:9px; }
            QPushButton:disabled { background:#33273b; color:#ad9fbb; }
        """)
        layout = QVBoxLayout(self)
        title = QLabel("JARVIS · CROSS-WORKSPACE WORKFLOW BOARD")
        title.setStyleSheet("font-weight:bold; font-size:18px; color:#c4b5fd;")
        layout.addWidget(title)
        info = QLabel(
            "Choose a reviewed workflow. Each workspace opens only when you "
            "click its button. No AI action, service change, file edit, "
            "broadcast or automatic browser navigation is performed.")
        info.setWordWrap(True)
        layout.addWidget(info)
        self.templates = QComboBox()
        self.templates.setObjectName("webbieWorkflowTemplate")
        for p in BLUEPRINTS:
            self.templates.addItem(p.title, p.key)
        self.templates.currentIndexChanged.connect(self.preview)
        layout.addWidget(self.templates)
        self.details = QTextEdit()
        self.details.setObjectName("webbieWorkflowPreview")
        self.details.setReadOnly(True)
        layout.addWidget(self.details)
        self.state_label = QLabel("Nothing authorized. Preview only.")
        self.state_label.setObjectName("webbieWorkflowStatus")
        self.state_label.setWordWrap(True)
        layout.addWidget(self.state_label)
        controls = QHBoxLayout()
        layout.addLayout(controls)
        self.start_button = QPushButton("Start approved checklist")
        self.start_button.setObjectName("webbieWorkflowStart")
        self.start_button.clicked.connect(self.begin)
        controls.addWidget(self.start_button)
        self.open_button = QPushButton("Open current workspace")
        self.open_button.setObjectName("webbieWorkflowOpenWorkspace")
        self.open_button.clicked.connect(self.open_current)
        controls.addWidget(self.open_button)
        self.complete_button = QPushButton("I completed this step")
        self.complete_button.setObjectName("webbieWorkflowComplete")
        self.complete_button.clicked.connect(self.complete_current)
        controls.addWidget(self.complete_button)
        final_row = QHBoxLayout()
        layout.addLayout(final_row)
        self.stop_button = QPushButton("STOP workflow")
        self.stop_button.setObjectName("webbieWorkflowStop")
        self.stop_button.clicked.connect(self.stop)
        final_row.addWidget(self.stop_button)
        close = QPushButton("Close")
        close.clicked.connect(self.close)
        final_row.addWidget(close)
        self.preview()

    def choose_template(self, key):
        """GUI may stage one known plan; running checklist is never overwritten."""
        blueprint_for(key)
        if self.session.current() is not None:
            return False
        index = self.templates.findData(key)
        if index < 0:
            return False
        self.templates.setCurrentIndex(index)
        self.preview()
        return True

    def preview(self):
        # Switching a template revokes any previous session. No implicit start.
        self.session.cancel()
        blueprint = blueprint_for(self.templates.currentData())
        lines = [blueprint.title, ""]
        for index, step in enumerate(blueprint.steps, start=1):
            lines.append(f"{index}. {step.title} [{step.workspace}]")
            lines.append("    " + step.instruction)
        lines.extend(("", "Preview only. Openings and completion require owner clicks."))
        self.details.setPlainText("\n".join(lines))
        self.state_label.setText("Not started. No workspace opened.")
        self._sync_controls()

    def _sync_controls(self):
        active = self.session.current() is not None
        self.open_button.setEnabled(active and callable(self.workspace_opener))
        self.complete_button.setEnabled(active)
        self.stop_button.setEnabled(active)
        self.templates.setEnabled(not active)

    def begin(self):
        if self.session.current() is not None:
            return
        blueprint = blueprint_for(self.templates.currentData())
        answer = QMessageBox.question(
            self, "Start Webbie checklist?",
            f"Start '{blueprint.title}' for up to ten minutes? "
            "Nothing opens automatically. You must click for each step, "
            "and Webbie cannot use this as a desktop task permission.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        self.session.begin(blueprint.key, owner_approved=True, seconds=600)
        self._show_current()

    def _show_current(self):
        step = self.session.current()
        if step is None:
            self.state_label.setText(
                "Checklist complete, cancelled, or expired. No further actions.")
        else:
            state = self.session.status()
            self.state_label.setText(
                f"Step {state['step']} of {state['total']}: {step.title} "
                f"({step.workspace}). Open this workspace yourself, review, "
                "then click completion. No action performed automatically.")
        self._sync_controls()

    def open_current(self):
        step = self.session.current()
        if step is None or not callable(self.workspace_opener):
            self._show_current()
            return
        # Exact workspace key from the compiled constant, never user input.
        try:
            self.workspace_opener(step.workspace)
        except (KeyError, ValueError, RuntimeError, OSError, TypeError):
            self.state_label.setText(
                "Could not request the selected workspace. Nothing was "
                "marked complete. Inspect the desktop.")
            return
        # A request is not evidence of successful application launch.
        self.state_label.setText(
            f"Requested the {step.workspace} workspace. Verify it opened "
            "before marking the step complete.")

    def complete_current(self):
        step = self.session.current()
        if step is None:
            return
        position = self.session.position
        self.session.complete(owner_confirmed=True, expected_position=position)
        self._show_current()

    def stop(self):
        self.session.cancel()
        self.state_label.setText(
            "Workflow stopped. This does not revoke separate computer-control "
            "grants. Use STOP computer control for those permissions.")
        self._sync_controls()

    def closeEvent(self, event):
        self.session.cancel()
        event.accept()
