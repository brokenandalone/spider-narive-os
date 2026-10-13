"""Native JARVIS Mission Center: one place to use local evidence tools.

Owners select a folder, choose a bounded operation and click RUN. There is
no hidden background action, shell prompt execution or cloud credential
handoff. Results are shown as untrusted evidence, not reinterpreted as jobs.
"""
from __future__ import annotations
from pathlib import Path
import sys

from PyQt5.QtCore import QThread,pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox,QDialog,QFileDialog,QHBoxLayout,QLabel,QLineEdit,QPushButton,
    QTextEdit,QVBoxLayout,
)

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"webbie/actions"))
from jarvis_orchestrator import JarvisCore

CHOICES=(
    ("Search selected folder","local.evidence"),
    ("Audit a website project","site.audit"),
    ("Check Spider OS health","system.health"),
    ("Find project TODOs","project.overview"),
    ("Research the public web with Forage","forage.web"),
)


class JarvisMissionWorker(QThread):
    finished_report=pyqtSignal(object)

    def __init__(self,core,action,folder,query,parent=None):
        super().__init__(parent)
        self.core=core
        self.action=action
        self.folder=folder
        self.query=query

    def run(self):
        self.finished_report.emit(self.core.run(
            self.action,source="owner_gui",
            folder=self.folder,query=self.query))


class JarvisMissionCenter(QDialog):
    def __init__(self,parent=None,*,core=None,stop_callback=None):
        super().__init__(parent)
        self.core=core or JarvisCore()
        self.stop_callback=stop_callback
        self.worker=None
        self.folder=None
        self.setWindowTitle("Webbie · JARVIS Mission Center")
        self.setObjectName("webbieJarvisMissionCenter")
        self.resize(780,650)
        self.setStyleSheet("""
            QDialog {background:#130e1b;color:#f7f4fb}
            QLabel {color:#f7f4fb}
            QTextEdit,QLineEdit,QComboBox {
                color:#f7f4fb;background:#221729;border:1px solid #7443ba;
                padding:8px; }
            QPushButton {background:#6332ac;color:white;border-radius:6px;
                         padding:9px}
            QPushButton:disabled {background:#30283a;color:#a39bad}
        """)
        layout=QVBoxLayout(self)
        heading=QLabel("WEBBIE · JARVIS OPERATIONS")
        heading.setStyleSheet("font-size:19px;font-weight:bold;color:#c4b5fd")
        layout.addWidget(heading)
        description=QLabel(
            "Your permanent permission authorizes supported operations. "
            "Choose the project scope and action here. Nothing runs simply "
            "because a model, browser, or terminal suggests it.")
        description.setWordWrap(True)
        layout.addWidget(description)
        row=QHBoxLayout();layout.addLayout(row)
        self.action=QComboBox()
        self.action.setObjectName("webbieJarvisOperation")
        for label,key in CHOICES:
            self.action.addItem(label,key)
        self.action.currentIndexChanged.connect(self.refresh)
        row.addWidget(self.action)
        self.choose=QPushButton("Choose project folder")
        self.choose.setObjectName("webbieJarvisChooseFolder")
        self.choose.clicked.connect(self.pick_folder)
        row.addWidget(self.choose)
        self.root_label=QLabel("No project folder selected")
        self.root_label.setWordWrap(True)
        layout.addWidget(self.root_label)
        self.query=QLineEdit()
        self.query.setObjectName("webbieJarvisEvidenceQuery")
        self.query.setPlaceholderText("Search phrase, e.g. Broken City, TODO, radio")
        layout.addWidget(self.query)
        actions=QHBoxLayout();layout.addLayout(actions)
        self.run_button=QPushButton("Run approved mission")
        self.run_button.setObjectName("webbieJarvisRun")
        self.run_button.clicked.connect(self.launch)
        actions.addWidget(self.run_button)
        self.stop_button=QPushButton("STOP this mission")
        self.stop_button.setObjectName("webbieJarvisMissionStop")
        self.stop_button.clicked.connect(self.stop_mission)
        actions.addWidget(self.stop_button)
        self.pause_button=QPushButton("STOP all Webbie control")
        self.pause_button.setObjectName("webbieJarvisGlobalStop")
        self.pause_button.clicked.connect(self.stop_all)
        actions.addWidget(self.pause_button)
        self.report=QTextEdit()
        self.report.setObjectName("webbieJarvisMissionReport")
        self.report.setReadOnly(True)
        layout.addWidget(self.report)
        self.report.setPlainText(
            "Mission center ready. Nothing has run yet.\n\n"
            "Available today: local project text search, missing website "
            "assets, Forage public web search, project TODO search "
            "and shell-free system checks.\n"
            "Not available here yet: website deployment, arbitrary terminal "
            "commands, privileged upgrades, browser form submissions, "
            "or security scans. Those require connected tool adapters.")
        self.refresh()

    def pick_folder(self):
        chosen=QFileDialog.getExistingDirectory(
            self,"Choose an owner-controlled project folder",str(Path.home()))
        if chosen:
            self.folder=chosen
            self.root_label.setText("Selected folder: "+chosen)
            self.refresh()

    def refresh(self):
        action=self.action.currentData()
        needs_folder=action in ("local.evidence","site.audit",
                                "project.overview")
        self.choose.setEnabled(needs_folder)
        self.query.setEnabled(action in (
            "local.evidence","project.overview","forage.web"))
        running=self.worker is not None and self.worker.isRunning()
        self.run_button.setEnabled(not running and
                                   (not needs_folder or bool(self.folder)))
        self.stop_button.setEnabled(running)

    def launch(self):
        if self.worker is not None and self.worker.isRunning():
            return
        selected=self.action.currentData()
        if selected in ("local.evidence","site.audit","project.overview") and not self.folder:
            self.report.setPlainText("Select a project folder first.")
            return
        self.worker=JarvisMissionWorker(
            self.core,selected,self.folder,self.query.text(),self)
        self.worker.finished_report.connect(self.deliver)
        self.worker.finished.connect(self.refresh)
        self.run_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.report.setPlainText(
            "Inspecting the selected owner scope. No changes requested.")
        self.worker.start()

    def deliver(self,result):
        self.report.setPlainText(
            "Operation: "+result.action+"\n"
            "Status: "+result.status+"\n"
            "Read-only: YES\n\n"+result.report)
        self.refresh()

    def stop_mission(self):
        self.core.stop()
        self.report.setPlainText(
            "STOP requested. Results will be discarded on completion.")

    def stop_all(self):
        self.stop_mission()
        if callable(self.stop_callback):
            self.stop_callback()

    def closeEvent(self,event):
        self.core.stop()
        if self.worker is not None and self.worker.isRunning():
            # Keep the worker's QObject and owned dialog alive until it
            # finishes, rather than QThread destruction during active I/O.
            event.ignore()
            self.report.setPlainText(
                "Mission canceled; close again after the worker exits.")
            return
        super().closeEvent(event)
