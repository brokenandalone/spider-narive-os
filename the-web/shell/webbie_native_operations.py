"""Webbie's existing JARVIS/Cognitive/Workflow controls, embedded in her bay.

Reuses the already-tested controls and resident agent. Does not create new
permissions, autonomous actions, camera or recording sessions. Removes the
need for a standalone "Intelligence Center" launcher.
"""
from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QLabel, QPushButton, QScrollArea

from webbie_cognitive_center import WebbieCognitiveDialog
from webbie_jarvis_mission_center import JarvisMissionCenter
from webbie_unified_workflow import WebbieUnifiedWorkflowDialog


class WebbieNativeOperations(QWidget):
    def __init__(self, assistant, workspace_callback, parent=None,
                 workspace_opener=None):
        super().__init__(parent)
        self.setObjectName("webbieNativeOperations")
        self.assistant = assistant
        body = QVBoxLayout(self)
        title = QLabel("WEBBIE / RESIDENT INTELLIGENCE + JARVIS")
        title.setStyleSheet("font-size:20px;font-weight:bold;color:#c4b5fd")
        body.addWidget(title)
        guidance = QLabel(
            "Manage Webbie inside the actual Webbie bay. The local model, "
            "speaker-trust diagnostics, privacy, project missions and guided "
            "computer workflows remain separate permissioned capabilities. "
            "No microphone, camera, desktop operation or network access starts "
            "merely because you open this panel.")
        guidance.setWordWrap(True)
        body.addWidget(guidance)
        tabs = QTabWidget(self)
        tabs.setObjectName("webbieNativeIntelligenceTabs")
        self.tabs = tabs
        body.addWidget(tabs, 1)

        cognitive = WebbieCognitiveDialog(
            self,
            workspace_callback=workspace_callback,
            workspace_opener=workspace_opener,
            emergency_callback=assistant.stop_sensitive_actions,
            workflow_callback=lambda: tabs.setCurrentIndex(2),
            mission_callback=lambda: tabs.setCurrentIndex(1),
        )
        cognitive.setWindowFlags(Qt.Widget)
        cognitive.setObjectName("webbieEmbeddedCognitive")
        # The standalone dialog's Close button is meaningless in a permanent bay.
        # Keep the original dialog class for backward compatibility elsewhere.
        for control in cognitive.findChildren(QPushButton):
            if control.text() == "Close":
                control.hide()
        self.cognitive = cognitive
        self._add_scroll_tab(cognitive, "Model · Voice · Privacy")

        missions = JarvisMissionCenter(
            self, core=assistant.jarvis_core,
            stop_callback=assistant.stop_sensitive_actions)
        missions.setWindowFlags(Qt.Widget)
        missions.setObjectName("webbieEmbeddedJarvisMissions")
        self.missions = missions
        self._add_scroll_tab(missions, "JARVIS missions")

        workflow = WebbieUnifiedWorkflowDialog(
            self, session=assistant.unified_workflow,
            workspace_callback=workspace_callback,
            computer_callback=assistant.open_computer_dialog,
            stop_callback=assistant.stop_sensitive_actions,
        )
        workflow.setWindowFlags(Qt.Widget)
        workflow.setObjectName("webbieEmbeddedGuidedWorkflow")
        self.workflow = workflow
        # One existing supervised workflow serves both candidate and preserved
        # owner-side Webbie controls. No duplicate dialog/authority is created.
        cognitive.workflow_dialog = workflow
        self._add_scroll_tab(workflow, "Guided workflows")

    def _add_scroll_tab(self, widget, title):
        scroll = QScrollArea(self.tabs)
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        self.tabs.addTab(scroll, title)

    def activate(self, name):
        for index in range(self.tabs.count()):
            if name.casefold() in self.tabs.tabText(index).casefold():
                self.tabs.setCurrentIndex(index)
                return True
        return False

    def can_close(self):
        """Protect active JARVIS and cognitive workers from premature disposal."""
        for worker in (self.missions.worker, self.cognitive.model_worker,
                       self.cognitive.hearing_worker):
            if worker is not None and worker.isRunning():
                return False
        return True
