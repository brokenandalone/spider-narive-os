#!/usr/bin/env python3
"""Owner-controlled graphical first-run setup for native Spider Audio Studio.

Never runs an installation on launch. The user must explicitly choose Install.
The preview package remains independently runnable without installing at all.
"""
from __future__ import annotations
from pathlib import Path
import subprocess
import sys
from PyQt5.QtCore import Qt, QProcess
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QApplication,QCheckBox,QDialog,QHBoxLayout,QLabel,QPushButton,QTextEdit,
    QVBoxLayout,QWidget,QMessageBox)

try:
    from .install_for_user import verify,install
    from .remove_beta import remove_version
except ImportError:
    from install_for_user import verify,install
    from remove_beta import remove_version

BUNDLE=Path(__file__).resolve().parent


class SpiderAudioSetup(QDialog):
    def __init__(self,bundle=BUNDLE,parent=None):
        super().__init__(parent)
        self.bundle=Path(bundle)
        self.installed=None
        self.computer_ready=False
        self.self_test_process=None
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
        tag=QLabel("0.16 PRIVATE BETA • Native music recording and production")
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
        self.ack.toggled.connect(self._update_install_permission)
        buttons.addWidget(self.install_button)
        self.audio_button=QPushButton("Test music engine")
        self.audio_button.clicked.connect(self.test_audio_engine)
        buttons.addWidget(self.audio_button)
        self.launch_button=QPushButton("Run Studio")
        self.launch_button.clicked.connect(self.launch)
        buttons.addWidget(self.launch_button)
        root.addLayout(buttons)
        self.remove_button=QPushButton("Remove this installed beta")
        self.remove_button.setEnabled(False)
        self.remove_button.clicked.connect(self.remove_installed_beta)
        root.addWidget(self.remove_button)
        self.result=QLabel("Nothing has been installed.")
        self.result.setWordWrap(True)
        root.addWidget(self.result)

    def _update_install_permission(self):
        self.install_button.setEnabled(
            self.installed is None and self.computer_ready and
            self.ack.isChecked())

    def check_computer(self):
        self.computer_ready=False
        self._update_install_permission()
        try:
            data=verify(self.bundle)
            result=subprocess.run(
                [sys.executable,str(self.bundle/"run_spider_audio_studio.py"),
                 "--doctor"],stdin=subprocess.DEVNULL,capture_output=True,
                text=True,timeout=25,check=False)
            self.log.setPlainText(
                "PACKAGE VERIFIED: "+data["version"]+"\n\n"+
                (result.stdout or result.stderr)[:6000])
            self.computer_ready=result.returncode==0
            self._update_install_permission()
            self.result.setText(
                "Required runtime available. You may now install this beta." 
                if self.computer_ready else
                "A required dependency is missing. Installation stays blocked; see the report.")
        except (OSError,ValueError,subprocess.SubprocessError) as error:
            self.log.setPlainText("Computer check failed:\n"+str(error)[:2000])
            self.result.setText("The beta cannot be verified here.")

    def install_beta(self):
        if not self.ack.isChecked() or not self.computer_ready:
            self.result.setText("Check the computer and acknowledge the beta before installing.")
            return
        try:
            location,desktop=install(self.bundle)
            self.installed=location
            self.remove_button.setEnabled(True)
            self.result.setText(
                "Installed. Open 'Spider Audio Studio (Beta)' from your "
                "application menu, or click Run Studio.")
            self.log.setPlainText(
                "New versioned application location:\n"+str(location)+
                "\n\nNew user desktop shortcut:\n"+str(desktop)+
                "\n\nYour recordings, previous Studio and OS are unchanged.")
            self._update_install_permission()
        except (OSError,ValueError,subprocess.SubprocessError) as error:
            self.result.setText("Install was not completed; source music was not altered.")
            self.log.setPlainText("Install blocked:\n"+str(error)[:2000])

    def remove_installed_beta(self):
        """Remove only this exact verified version after explicit confirmation."""
        if self.installed is None:
            return
        answer=QMessageBox.question(
            self,"Remove Spider Audio Studio Beta",
            "Remove only this installed beta version and its menu shortcut? "
            "Your songs, mixes, other versions and Spider OS will remain. "
            "Modified installations will be protected instead of deleted.",
            QMessageBox.Yes|QMessageBox.No,QMessageBox.No)
        if answer!=QMessageBox.Yes:
            return
        try:
            info=verify(self.installed)
            remove_version(info["version"])
            self.installed=None
            self.remove_button.setEnabled(False)
            self._update_install_permission()
            self.result.setText("This beta version was removed. Your songs remain untouched.")
        except (OSError,ValueError,subprocess.SubprocessError) as error:
            self.result.setText("Removal safely blocked: "+str(error)[:240])

    def test_audio_engine(self):
        """Background offline FFmpeg test; never activates audio input/output."""
        if self.self_test_process is not None:
            return
        try:
            verify(self.bundle)
        except (OSError,ValueError,subprocess.SubprocessError) as error:
            self.result.setText("Cannot test an unverified package: "+str(error)[:170])
            return
        process=QProcess(self)
        self.self_test_process=process
        self.audio_button.setEnabled(False)
        self.result.setText("Testing the actual Studio multitrack renderer with temporary tones...")
        process.setProgram(sys.executable)
        process.setArguments([
            str(self.bundle/"run_spider_audio_studio.py"),"--self-test"])
        process.finished.connect(self._engine_test_finished)
        process.start()

    def _engine_test_finished(self,*args):
        process=self.self_test_process
        self.self_test_process=None
        self.audio_button.setEnabled(True)
        if process is None:
            return
        report=bytes(process.readAllStandardOutput()).decode("utf-8","replace")
        error=bytes(process.readAllStandardError()).decode("utf-8","replace")
        passed=process.exitCode()==0 and '"result": "PASS"' in report
        self.log.setPlainText(
            (report or error or "No music-engine test results")[:6000])
        self.result.setText(
            "Offline music engine PASSED. Live device latency is not tested."
            if passed else "Offline music-engine test failed. See the report.")
        process.deleteLater()

    def closeEvent(self,event):
        process=self.self_test_process
        if process is not None and process.state()!=QProcess.NotRunning:
            process.terminate()
            if not process.waitForFinished(2000):
                process.kill()
                process.waitForFinished(2000)
        super().closeEvent(event)

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
