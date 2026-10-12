"""Webbie Jarvis cognitive, model, focus and privacy control center.

Everything is local-only; sensitive changes come from deliberate GUI clicks.
No screenshot, voice transcript, prompt, browser or model can invoke controls.
"""
from pathlib import Path
import sys

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog, QLabel, QMessageBox, QPushButton, QTextEdit, QVBoxLayout,
    QHBoxLayout,
)

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"webbie/brain"))
sys.path.insert(0,str(ROOT/"webbie/agent"))
sys.path.insert(0,str(ROOT/"webbie/voice"))
from focus_tasks import current_focus, focus_answer
from privacy_controls import private_session_active, set_private_session, privacy_explanation
from local_models import configured_choice
from local_model_inventory import inspect_local_models, report_lines
from proactive_checks import status_message
from runtime_readiness import inspect_readiness, render_report
from voice_trust import trust_status
from voice_lab import inspect_voice_lab, voice_lab_report
from hearing_test import run_hearing_test
from webbie_focus_dialog import WebbieFocusDialog


class ModelInventoryWorker(QThread):
    finishedReport=pyqtSignal(str)

    def run(self):
        try:
            brain=configured_choice("brain")
            vision=configured_choice("vision")
            result=inspect_local_models(brain_preference=brain,
                                        vision_preference=vision)
            self.finishedReport.emit(report_lines(result))
        except Exception:
            self.finishedReport.emit(
                "Local model inventory is unavailable. No model was changed.")


class HearingTestWorker(QThread):
    heard=pyqtSignal(str)

    def run(self):
        try:
            # GUI already obtained explicit consent before starting this thread.
            self.heard.emit(run_hearing_test(approved=True))
        except Exception:
            self.heard.emit(
                "Unable to complete local microphone test. No recording retained.")


class WebbieCognitiveDialog(QDialog):
    def __init__(self,parent=None,*,workspace_callback=None,
                 emergency_callback=None,workflow_callback=None):
        super().__init__(parent)
        self.setWindowTitle("Webbie · Jarvis Control Center")
        self.setMinimumWidth(600)
        self.setMinimumHeight(540)
        self.setStyleSheet("""
            QDialog { background:#120d18; color:#f5eff8; }
            QLabel { color:#f5eff8; }
            QTextEdit { background:#22162b; color:#f5eff8;
                border:1px solid #8555b7; padding:8px; }
            QPushButton { color:white; background:#6d28d9; padding:10px;
                border-radius:6px; }
        """)
        self.workspace_callback=workspace_callback or (lambda:"default")
        self.emergency_callback=emergency_callback
        self.workflow_callback=workflow_callback
        self.focus_dialog=None
        self.model_worker=None
        self.hearing_worker=None
        root=QVBoxLayout(self)
        title=QLabel("WEBBIE · COGNITIVE CONTROL CENTER")
        title.setStyleSheet("font-size:19px; font-weight:bold; color:#c4b5fd")
        root.addWidget(title)
        intro=QLabel(
            "Local brain readiness, workspace focus, and direct privacy controls. "
            "No model downloads, remote access, unrestricted desktop operation "
            "or voice identity enrollment happen here.")
        intro.setWordWrap(True)
        root.addWidget(intro)
        self.status=QLabel()
        self.status.setWordWrap(True)
        self.status.setAccessibleName("Webbie privacy session status")
        root.addWidget(self.status)
        actions=QHBoxLayout(); root.addLayout(actions)
        focus=QPushButton("My focus tasks")
        focus.setObjectName("webbieFocusTaskButton")
        focus.clicked.connect(self.open_focus)
        actions.addWidget(focus)
        flow=QPushButton("Unified guided workflow")
        flow.setObjectName("webbieUnifiedWorkflowCognitiveButton")
        flow.clicked.connect(self.open_workflow)
        actions.addWidget(flow)
        inspect=QPushButton("Inspect local AI models")
        inspect.setObjectName("webbieInspectModelsButton")
        inspect.clicked.connect(self.inspect_models)
        actions.addWidget(inspect)
        readiness=QPushButton("Inspect Webbie readiness")
        readiness.setObjectName("webbieReadinessButton")
        readiness.clicked.connect(self.inspect_readiness)
        actions.addWidget(readiness)
        lab_row=QHBoxLayout(); root.addLayout(lab_row)
        voice_lab=QPushButton("Voice Lab diagnostics")
        voice_lab.setObjectName("webbieVoiceLabButton")
        voice_lab.clicked.connect(self.inspect_voice_lab)
        lab_row.addWidget(voice_lab)
        hear=QPushButton("Test Webbie hearing (3 sec)")
        hear.setObjectName("webbieHearingTestButton")
        hear.clicked.connect(self.test_hearing)
        lab_row.addWidget(hear)
        privacy=QHBoxLayout(); root.addLayout(privacy)
        self.private_button=QPushButton()
        self.private_button.setObjectName("webbiePrivateSessionButton")
        self.private_button.clicked.connect(self.toggle_private)
        privacy.addWidget(self.private_button)
        clear=QPushButton("Clear recent conversation")
        clear.setObjectName("webbieClearRecentChatButton")
        clear.clicked.connect(self.clear_recent)
        privacy.addWidget(clear)
        cancel_row=QHBoxLayout(); root.addLayout(cancel_row)
        shutdown=QPushButton("STOP computer control and camera")
        shutdown.setObjectName("webbieSensitiveStopButton")
        shutdown.clicked.connect(self.stop_sensitive)
        cancel_row.addWidget(shutdown)
        close=QPushButton("Close")
        close.clicked.connect(self.close)
        cancel_row.addWidget(close)
        self.report=QTextEdit()
        self.report.setObjectName("webbieCognitiveReport")
        self.report.setReadOnly(True)
        root.addWidget(self.report)
        self.refresh()

    def refresh(self):
        self.status.setText(privacy_explanation())
        private=private_session_active()
        self.private_button.setText(
            "End private session" if private else "Start private session")
        workspace=self.workspace_callback()
        try:
            item=current_focus(workspace)
        except (ValueError,OSError):
            item=None
        lines=[f"Workspace: {workspace}",
               "Active focus: "+(
                   item["title"]+" | Next: "+item["next_step"]
                   if item else "No owner-created task selected"),
               "SYSTEM CHECKS",status_message(),
               "PRIVACY",privacy_explanation(),
               "SPEAKER TRUST",trust_status(),
               "This is advisory status. No PC task has been executed."]
        self.report.setPlainText("\n".join(lines))

    def open_workflow(self):
        if callable(self.workflow_callback):
            self.workflow_callback()
        else:
            self.report.setPlainText(
                "Open the guided workflow from the resident Webbie panel.")

    def open_focus(self):
        if self.focus_dialog is None:
            self.focus_dialog=WebbieFocusDialog(
                self,workspace=self.workspace_callback())
        self.focus_dialog.choose_workspace(self.workspace_callback())
        self.focus_dialog.refresh()
        self.focus_dialog.show()
        self.focus_dialog.raise_()
        self.focus_dialog.activateWindow()

    def test_hearing(self):
        """Explicit owner's choice, not triggered by model/voice or startup."""
        if self.hearing_worker and self.hearing_worker.isRunning():
            self.report.setPlainText("A manual hearing test is already running.")
            return
        if QMessageBox.question(
                self, "Test Webbie hearing?",
                "Capture three seconds of microphone audio and transcribe it "
                "using local Whisper? The sample and transcript will be erased "
                "after testing. This does not verify who is speaking or grant "
                "commands. If the resident listener owns the device, the test "
                "may report the microphone is busy.",
                QMessageBox.Yes|QMessageBox.No,
                QMessageBox.No)!=QMessageBox.Yes:
            return
        self.report.setPlainText(
            "Manual local hearing test requested. No voice control authorized.")
        self.hearing_worker=HearingTestWorker(self)
        self.hearing_worker.heard.connect(self.report.setPlainText)
        self.hearing_worker.finished.connect(self.hearing_finished)
        self.hearing_worker.start()

    def hearing_finished(self):
        done=self.hearing_worker
        self.hearing_worker=None
        if done is not None:
            done.deleteLater()

    def inspect_voice_lab(self):
        """Owner click: static local files only, no microphone access."""
        try:
            self.report.setPlainText(voice_lab_report(inspect_voice_lab()))
        except (OSError, ValueError):
            self.report.setPlainText(
                "Voice Lab unavailable. No microphone or model was changed.")

    def inspect_readiness(self):
        """Read owner-local status files; never start a service/device."""
        try:
            self.report.setPlainText(render_report(inspect_readiness()))
        except (OSError, ValueError, TypeError):
            self.report.setPlainText(
                "Read-only Webbie readiness report unavailable. "
                "No service was changed.")

    def inspect_models(self):
        if self.model_worker and self.model_worker.isRunning():
            self.report.setPlainText("Local model inspection already running.")
            return
        self.report.setPlainText(
            "Checking Ollama on this PC only. No model downloads or changes.")
        self.model_worker=ModelInventoryWorker(self)
        self.model_worker.finishedReport.connect(self.report.setPlainText)
        self.model_worker.finished.connect(self.model_finished)
        self.model_worker.start()

    def model_finished(self):
        # Dispose of the old Qt worker before another inventory request.
        done=self.model_worker
        self.model_worker=None
        if done is not None:
            done.deleteLater()

    def toggle_private(self):
        wanted=not private_session_active()
        if wanted:
            question=("Start private session? New chats will avoid Webbie's "
                      "saved conversation and long-term memory. Existing "
                      "records are not erased.")
        else:
            question=("End private session and resume the existing local "
                      "conversation/memory behavior?")
        if QMessageBox.question(
                self,"Webbie private session",question,
                QMessageBox.Yes|QMessageBox.No,
                QMessageBox.No)!=QMessageBox.Yes:
            return
        try:
            set_private_session(wanted)
        except (OSError,ValueError,PermissionError) as error:
            QMessageBox.warning(self,"Privacy preference not saved",str(error))
        self.refresh()

    def clear_recent(self):
        if QMessageBox.question(
                self,"Clear Webbie recent conversation?",
                "Delete Webbie's locally saved recent chat turns? This "
                "does not delete long-term memories, other logs or linked apps.",
                QMessageBox.Yes|QMessageBox.No,
                QMessageBox.No)!=QMessageBox.Yes:
            return
        try:
            from brain import clear_conversation
            success=clear_conversation()
        except (ImportError,OSError):
            success=False
        self.report.setPlainText(
            "Recent conversation file cleared." if success else
            "Could not clear Webbie's recent conversation; inspect its permissions.")

    def stop_sensitive(self):
        if QMessageBox.question(
                self,"Stop Webbie computer and camera access?",
                "Revoke current desktop task approval and turn off the Webbie "
                "camera? Background system checks stay running.",
                QMessageBox.Yes|QMessageBox.No,
                QMessageBox.No)!=QMessageBox.Yes:
            return
        if self.emergency_callback is not None:
            self.emergency_callback()
        self.report.setPlainText(
            "Sensitive controls stop was requested in the parent Webbie panel.")

    def closeEvent(self,event):
        if ((self.model_worker and self.model_worker.isRunning()) or
                (self.hearing_worker and self.hearing_worker.isRunning())):
            # Keep Qt threads alive while their bounded checks exit.
            self.hide(); event.ignore()
        else:
            event.accept()
