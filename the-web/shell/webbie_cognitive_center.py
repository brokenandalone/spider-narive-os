"""Webbie Jarvis cognitive, model, focus and privacy control center.

Everything is local-only; sensitive changes come from deliberate GUI clicks.
No screenshot, voice transcript, prompt, browser or model can invoke controls.
"""
from pathlib import Path
import sys

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog, QLabel, QMessageBox, QPushButton, QTextEdit, QVBoxLayout,
    QHBoxLayout, QComboBox,
)

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"webbie/brain"))
sys.path.insert(0,str(ROOT/"webbie/agent"))
sys.path.insert(0,str(ROOT/"webbie/voice"))
from focus_tasks import current_focus, focus_answer
from privacy_controls import private_session_active, set_private_session, privacy_explanation
from local_models import configured_choice
from local_model_inventory import inspect_local_models, report_lines
from local_models import installed_models
from resident_model_choice import (read_choice, select_installed_model,
                                   restore_default)
from heretic_lab import (inspect_heretic, plan_experiment, launch_experiment,
                         launch_lab_setup, EXPERIMENT_MODELS)
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
                 emergency_callback=None,workflow_callback=None,
                 mission_callback=None):
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
        self.mission_callback=mission_callback
        self.focus_dialog=None
        self.model_worker=None
        self.hearing_worker=None
        self.heretic_dialog=None
        self.resident_model_dialog=None
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
        mission=QPushButton("JARVIS missions")
        mission.setObjectName("webbieJarvisMissionCognitiveButton")
        mission.clicked.connect(self.open_missions)
        actions.addWidget(mission)
        inspect=QPushButton("Inspect local AI models")
        inspect.setObjectName("webbieInspectModelsButton")
        inspect.clicked.connect(self.inspect_models)
        actions.addWidget(inspect)
        choose_brain=QPushButton("My everyday AI brain")
        choose_brain.setObjectName("webbiePersistentBrainButton")
        choose_brain.clicked.connect(self.choose_brain)
        actions.addWidget(choose_brain)
        readiness=QPushButton("Inspect Webbie readiness")
        readiness.setObjectName("webbieReadinessButton")
        readiness.clicked.connect(self.inspect_readiness)
        actions.addWidget(readiness)
        lab_row=QHBoxLayout(); root.addLayout(lab_row)
        voice_lab=QPushButton("Voice Lab diagnostics")
        voice_lab.setObjectName("webbieVoiceLabButton")
        voice_lab.clicked.connect(self.inspect_voice_lab)
        lab_row.addWidget(voice_lab)
        heretic=QPushButton("Heretic model lab")
        heretic.setObjectName("webbieHereticResearchLabButton")
        heretic.clicked.connect(self.open_heretic_lab)
        lab_row.addWidget(heretic)
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
        chosen=read_choice()
        lines=[f"Workspace: {workspace}",
               "Everyday AI brain: "+(chosen or configured_choice("brain") or "default")
               + (" (owner-selected across restarts)" if chosen else " (Spider OS default)"),
               "Active focus: "+(
                   item["title"]+" | Next: "+item["next_step"]
                   if item else "No owner-created task selected"),
               "SYSTEM CHECKS",status_message(),
               "PRIVACY",privacy_explanation(),
               "SPEAKER TRUST",trust_status(),
               "This is advisory status. No PC task has been executed."]
        self.report.setPlainText("\n".join(lines))

    def choose_brain(self):
        if self.resident_model_dialog is None:
            self.resident_model_dialog=ResidentBrainDialog(self)
        self.resident_model_dialog.refresh()
        self.resident_model_dialog.show()
        self.resident_model_dialog.raise_()
        self.resident_model_dialog.activateWindow()

    def open_missions(self):
        if callable(self.mission_callback):
            self.mission_callback()
        else:
            self.report.setPlainText(
                "Open JARVIS Mission Center from The Web's Webbie panel.")

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

    def open_heretic_lab(self):
        # Existing cognitive-center owner button only, never a voice/model command.
        if self.heretic_dialog is None:
            self.heretic_dialog=HereticExperimentDialog(self)
        self.heretic_dialog.refresh()
        self.heretic_dialog.show()
        self.heretic_dialog.raise_()
        self.heretic_dialog.activateWindow()

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


class HereticExperimentDialog(QDialog):
    """Native opt-in model workshop, not another daemon or Webbie persona."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Webbie AI Lab · Heretic experiments")
        self.setObjectName("webbieHereticExperimentDialog")
        self.resize(670, 460)
        layout = QVBoxLayout(self)
        heading = QLabel("HERETIC · MODEL RESEARCH")
        heading.setStyleSheet("font-size:17px;font-weight:bold;color:#c4b5fd")
        layout.addWidget(heading)
        note = QLabel(
            "Experiment with a separate Hugging Face language model using the "
            "official Heretic CLI. Heretic changes refusal behavior; it is not "
            "a memory, autonomy or intelligence upgrade. Nothing here swaps "
            "Webbie's qwen3:8b brain, Natasha voice or authorization policy.")
        note.setWordWrap(True)
        layout.addWidget(note)
        self.model = QComboBox()
        self.model.setObjectName("webbieHereticModelChoice")
        for name in EXPERIMENT_MODELS:
            self.model.addItem(name)
        layout.addWidget(self.model)
        self.model.currentIndexChanged.connect(self.refresh)
        self.report = QTextEdit()
        self.report.setReadOnly(True)
        self.report.setObjectName("webbieHereticReadinessReport")
        layout.addWidget(self.report)
        actions = QHBoxLayout()
        layout.addLayout(actions)
        self.check_button = QPushButton("Check local readiness")
        self.check_button.clicked.connect(self.refresh)
        actions.addWidget(self.check_button)
        self.setup_button = QPushButton("Install isolated Heretic lab")
        self.setup_button.setObjectName("webbieHereticSetupButton")
        self.setup_button.clicked.connect(self.install_setup)
        actions.addWidget(self.setup_button)
        self.use_brain_button = QPushButton("Use installed model as Webbie's everyday brain")
        self.use_brain_button.setObjectName("webbieHereticEverydayBrainButton")
        self.use_brain_button.clicked.connect(self.open_resident_brain)
        actions.addWidget(self.use_brain_button)
        self.run_button = QPushButton("Start supervised experiment in Konsole")
        self.run_button.setObjectName("webbieHereticStartButton")
        self.run_button.clicked.connect(self.start)
        actions.addWidget(self.run_button)
        done = QPushButton("Close")
        done.clicked.connect(self.close)
        actions.addWidget(done)
        self.refresh()

    def refresh(self):
        # Read local readiness only, no model fetch/install or process execution.
        status = inspect_heretic()
        ready, explanation = plan_experiment(self.model.currentText(), status)
        self.run_button.setEnabled(ready)
        self.setup_button.setEnabled(
            (not status.installed) and status.console_available
            and status.free_disk_gib >= 25)
        self.report.setPlainText(
            status.explanation + "\n\n" + explanation + "\n\n"
            "Upstream: https://github.com/p-e-w/heretic (AGPL-3.0-or-later). "
            "Install separately into Webbie's isolated venv when you choose. "
            "Heretic can download model weights, use substantial memory, "
            "and offer optional online publishing inside its CLI. "
            "The interactive Konsole run is managed there; press Ctrl+C in "
            "that Konsole to stop it.")


    def open_resident_brain(self):
        """Switch her normal conversation model, not Heretic's training CLI."""
        parent=self.parent()
        if isinstance(parent, WebbieCognitiveDialog):
            parent.choose_brain()
        else:
            self.report.setPlainText("Choose everyday AI brain in Webbie's Cognitive Center.")

    def install_setup(self):
        """Only a deliberate GUI button plus in-terminal consent installs."""
        status = inspect_heretic()
        if status.installed:
            self.report.setPlainText("Heretic is already present in the private lab.")
            return
        question = (
            "Open the optional Heretic setup in Konsole?\n\n"
            "This installs heavyweight Python/PyTorch research dependencies in "
            "your home directory, not in the Spider OS system environment. "
            "It may download several gigabytes. Webbie's running qwen3:8b, "
            "Natasha voice, memory and permissions are not changed.\n\n"
            "The installer also requires you to type INSTALL HERETIC in Konsole. "
            "Nothing is downloaded until you do. Continue?")
        if QMessageBox.question(
            self, "Install Heretic research environment?", question,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        ) != QMessageBox.Yes:
            return
        try:
            launch_lab_setup(approved=True, status=status)
            self.report.setPlainText(
                "Heretic setup Konsole requested. Review the optional installation "
                "details and type INSTALL HERETIC only if you approve. "
                "Refresh readiness after it completes. No Webbie service changed.")
        except (OSError, RuntimeError, ValueError, PermissionError) as error:
            self.report.setPlainText(
                "No Heretic installation started: " + str(error)[:500])
        self.refresh()

    def start(self):
        status = inspect_heretic()
        model = self.model.currentText()
        ready, report = plan_experiment(model, status)
        if not ready:
            self.report.setPlainText(status.explanation + "\n\n" + report)
            return
        question = (
            "Start the upstream Heretic research CLI for\n\n" + model + "\n\n"
            "It can fetch large files and stress your CPU/RAM. Its prompts "
            "may offer to upload an altered model to a public service; "
            "do not select upload without reviewing it yourself. "
            "It will NOT replace Webbie's active Ollama model.\n\n"
            "An interactive Konsole window opens. Press Ctrl+C there "
            "to stop the experiment.\n\nContinue?")
        if QMessageBox.question(
                self, "Start an isolated Heretic experiment?", question,
                QMessageBox.Yes|QMessageBox.No, QMessageBox.No
        ) != QMessageBox.Yes:
            return
        try:
            launch_experiment(model, approved=True, status=status)
            self.report.setPlainText(
                "Interactive Heretic CLI launch requested in Konsole.\n"
                "The model is NOT installed into Ollama or attached to Webbie.\n"
                "Verify the new window; stop with Ctrl+C there.")
        except (OSError, RuntimeError, ValueError, PermissionError) as error:
            self.report.setPlainText(
                "Heretic did not start: " + str(error)[:500] +
                "\nNo Webbie production model was changed.")


class ResidentBrainDialog(QDialog):
    """Choose one existing local Ollama model to answer Webbie ALL THE TIME."""

    def __init__(self,parent=None):
        super().__init__(parent)
        self.setWindowTitle("Webbie · Everyday AI brain")
        self.setObjectName("webbieResidentBrainDialog")
        self.resize(640, 440)
        layout=QVBoxLayout(self)
        intro=QLabel(
            "Choose a locally installed Ollama model as Webbie's ongoing "
            "conversational brain. A Heretic-derived model is eligible once "
            "it's compatible with Ollama and installed here. The choice "
            "persists across computer restarts and Webbie conversations. "
            "Natasha, memories, existing services and all native bay tools stay "
            "part of the SAME resident Webbie. No model downloads occur here.")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.models=QComboBox()
        self.models.setObjectName("webbieInstalledBrainChoices")
        layout.addWidget(self.models)
        self.status=QTextEdit()
        self.status.setReadOnly(True)
        layout.addWidget(self.status)
        row=QHBoxLayout()
        layout.addLayout(row)
        self.activate=QPushButton("Make this Webbie's everyday brain")
        self.activate.setObjectName("webbieActivatePermanentBrain")
        self.activate.clicked.connect(self.select)
        row.addWidget(self.activate)
        reset=QPushButton("Use original Qwen3 brain")
        reset.setObjectName("webbieRestoreOriginalBrain")
        reset.clicked.connect(self.reset)
        row.addWidget(reset)
        close=QPushButton("Close")
        close.clicked.connect(self.close)
        row.addWidget(close)
        self.refresh()

    def refresh(self):
        # Only the installed Ollama model inventory; no pulls, cloud calls,
        # process launches or changes to any resident service.
        installed=installed_models(timeout=2)
        chosen=read_choice()
        self.models.blockSignals(True)
        self.models.clear()
        for name in installed:
            label=name+(" · HERETIC" if "heretic" in name.casefold() else "")
            self.models.addItem(label, name)
        if chosen and chosen in installed:
            self.models.setCurrentIndex(installed.index(chosen))
        self.models.blockSignals(False)
        self.activate.setEnabled(bool(installed))
        state=("Current owner selection: "+(chosen or "Original Spider OS model")
               + "\nAvailable local Ollama models: "+str(len(installed))
               + "\n\nThis changes NORMAL conversation replies immediately, "
               "and remains in effect after restart. The full memory-aware "
               "brain and native tool authorization stay in place.\n"
               "Heretic model processing itself is never continuously run. "
               "Only its finished model can be used as the resident brain.")
        if chosen and chosen not in installed:
            state+="\n\nThe saved model is not installed. Restore the original model below."
        self.status.setPlainText(state)

    def select(self):
        name=self.models.currentData()
        if not isinstance(name,str):
            return
        message=(
            "Use "+name+" as Webbie's EVERYDAY conversation model, including "
            "future chats and restarts?\n\n"
            "This model stays local to Ollama. Webbie's long-term memory, "
            "Natasha voice, native workspaces and owner control are unchanged.\n\n"
            "The original Qwen3 8B remains installed and selectable."
        )
        if QMessageBox.question(
            self,"Choose Webbie's permanent brain",message,
            QMessageBox.Yes|QMessageBox.No,QMessageBox.No
        )!=QMessageBox.Yes:
            return
        try:
            select_installed_model(name,owner_clicked=True)
        except (OSError,ValueError,PermissionError) as error:
            self.status.setPlainText(
                "The model was NOT selected: "+str(error)[:400])
            return
        self.refresh()
        self.status.append(
            "\nActive preference saved. Webbie will use this model for "
            "subsequent normal conversational turns without another prompt.")

    def reset(self):
        if QMessageBox.question(
            self,"Restore original Webbie brain",
            "Return everyday conversations to the installed Spider OS "
            "Qwen3 model? This keeps other downloaded models available.",
            QMessageBox.Yes|QMessageBox.No,QMessageBox.No
        )!=QMessageBox.Yes:
            return
        try:
            restore_default(owner_clicked=True)
        except (OSError,ValueError,PermissionError) as error:
            self.status.setPlainText("Could not restore model: "+str(error)[:400])
            return
        self.refresh()
