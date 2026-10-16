#!/usr/bin/env python3
"""Owner-controlled graphical first-run setup for native Spider Audio Studio.

Never runs an installation on launch. The user must explicitly choose Install.
The preview package remains independently runnable without installing at all.
"""
from __future__ import annotations
from pathlib import Path
import subprocess
import sys
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QApplication,QCheckBox,QDialog,QHBoxLayout,QLabel,QPushButton,QTextEdit,
    QVBoxLayout,QWidget)

try:
    from .install_for_user import verify,install
except ImportError:
    from install_for_user import verify,install

BUNDLE=Path(__file__).resolve().parent


class SpiderAudioSetup(QDialog):
    def __init__(self,bundle=BUNDLE,parent=None):
        super().__init__(parent)
        self.bundle=Path(bundle)
        self.installed=None
        self.setObjectName("spiderAudioBetaSetup")
        self.setWindowTitle("Spider Audio Studio · Beta Setup")
        self.setMinimumSize(610,450)
        self.setStyleSheet("""
            #spiderAudioBetaSetup {background:#161025;color:#f7eeff}
            QLabel {color:#eee5fa}
            QPushButton {background:#30224c;color:#f8f0ff;
                border:1px solid #9a80c9;border-radius:8px;padding:10px}
            QPushButton:disabled {color:#90859d;border-color:#554561}
            QTextEdit {background:#201830;color:#e3d8f1;border:1px solid #5f4a83}
        """)
        root=QVBoxLayout(self)
        title=QLabel("SPIDER AUDIO STUDIO")
        title.setStyleSheet("font-size:26px;font-weight:800;color:#c6a4ff")
        root.addWidget(title)
        tag=QLabel("0.14 PRIVATE BETA • Native music recording and production")
        tag.setStyleSheet("color:#d0b7f5")
        root.addWidget(tag)
        paragraph=QLabel(
            "Check your desktop, then install Spider Audio Studio for this "
            "user account. It creates a separate application-menu shortcut. "
            "No sudo, OS replacement or modification of existing songs.")
        paragraph.setWordWrap(True)
        root.addWidget(paragraph)
        self.log=QTextEdit(self)
        self.log.setReadOnly(True)
        self.log.setPlainText(
            "Welcome. This is a beta software preview, not yet approved for "
            "commercial distribution.\n\n"
            "1. Check computer requirements.\n"
            "2. Review the beta disclaimer.\n"
            "3. Choose Install for this user or run without installing.")
        root.addWidget(self.log,1)
        self.ack=QCheckBox(
            "I understand this is an unfinished beta and I will back up my recordings.")
        self.ack.setChecked(False)
        root.addWidget(self.ack)
        buttons=QHBoxLayout()
        self.check=QPushButton("Check computer")
        self.check.clicked.connect(self.check_computer)
        buttons.addWidget(self.check)
        self.install_button=QPushButton("Install for this user")
        self.install_button.setEnabled(False)
        self.install_button.clicked.connect(self.install_beta)
        self.ack.toggled.connect(self.install_button.setEnabled)
        buttons.addWidget(self.install_button)
        self.launch_button=QPushButton("Run Studio")
        self.launch_button.clicked.connect(self.launch)
        buttons.addWidget(self.launch_button)
        root.addLayout(buttons)
        self.result=QLabel("Nothing has been installed.")
        self.result.setWordWrap(True)
        root.addWidget(self.result)

    def check_computer(self):
        try:
            data=verify(self.bundle)
            result=subprocess.run(
                [sys.executable,str(self.bundle/"run_spider_audio_studio.py"),
                 "--doctor"],stdin=subprocess.DEVNULL,capture_output=True,
                text=True,timeout=25,check=False)
            self.log.setPlainText(
                "PACKAGE VERIFIED: "+data["version"]+"\n\n"+
                (result.stdout or result.stderr)[:6000])
            self.result.setText(
                "Required runtime available." if result.returncode==0 else
                "Some dependencies are missing. See the report; you may need to install them.")
        except (OSError,ValueError,subprocess.SubprocessError) as error:
            self.log.setPlainText("Computer check failed:\n"+str(error)[:2000])
            self.result.setText("The beta cannot be verified here.")

    def install_beta(self):
        if not self.ack.isChecked():
            return
        try:
            location,desktop=install(self.bundle)
            self.installed=location
            self.result.setText(
                "Installed. Open 'Spider Audio Studio (Beta)' from your "
                "application menu, or click Run Studio.")
            self.log.setPlainText(
                "New versioned application location:\n"+str(location)+
                "\n\nNew user desktop shortcut:\n"+str(desktop)+
                "\n\nYour recordings, previous Studio and OS are unchanged.")
            self.install_button.setEnabled(False)
        except (OSError,ValueError,subprocess.SubprocessError) as error:
            self.result.setText("Install was not completed; source music was not altered.")
            self.log.setPlainText("Install blocked:\n"+str(error)[:2000])

    def launch(self):
        folder=self.installed or self.bundle
        launcher=folder/"run_spider_audio_studio.py"
        try:
            verify(folder)
            subprocess.Popen(
                [sys.executable,str(launcher)],
                stdin=subprocess.DEVNULL,start_new_session=True)
            self.result.setText(
                "Starting the original Spider Audio Studio application.")
        except (OSError,ValueError,subprocess.SubprocessError) as error:
            self.result.setText("Cannot start Studio: "+str(error)[:230])

def main():
    app=QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Spider Audio Studio Beta Setup")
    wizard=SpiderAudioSetup()
    wizard.show()
    return app.exec_()

if __name__=="__main__":
    raise SystemExit(main())
