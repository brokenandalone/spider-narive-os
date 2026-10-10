"""Manual school OneDrive access; never share Webbie personal OneDrive credentials."""
import shutil
import subprocess
from pathlib import Path
from PyQt5.QtCore import Qt, QProcess, QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QMessageBox, QFileDialog, QInputDialog

REMOTE = 'school_onedrive'

def remote_ready():
    if not shutil.which('rclone'):
        return False
    try:
        run = subprocess.run(['rclone', 'listremotes'], capture_output=True,
                             text=True, timeout=8)
        return run.returncode == 0 and REMOTE + ':' in run.stdout.splitlines()
    except (OSError, subprocess.TimeoutExpired):
        return False

class SchoolOneDriveDialog(QDialog):
    def __init__(self, parent, course_folder):
        super().__init__(parent)
        self.setWindowTitle('School OneDrive | Study')
        self.resize(510, 330)
        self.course_folder = Path(course_folder)
        self.process = None
        layout = QVBoxLayout(self)
        note = QLabel('Connect your school Microsoft account separately from personal OneDrive. '
                      'No files are transferred without your choosing them.')
        note.setWordWrap(True)
        layout.addWidget(note)
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.PlainText)
        layout.addWidget(self.status)
        for title, handler in [
            ('Open Microsoft 365 school account', self.open_school),
            ('Configure school OneDrive', self.configure),
            ('Download a school file', self.download),
            ('Upload a course file', self.upload),
            ('Open course folder', self.open_folder)
        ]:
            button = QPushButton(title)
            button.clicked.connect(handler)
            layout.addWidget(button)
        self.status.setText('School remote configured.' if remote_ready() else
                            'School remote not configured. Existing coursework remains local.')

    def open_school(self):
        QDesktopServices.openUrl(QUrl('https://www.microsoft365.com/'))

    def configure(self):
        if not shutil.which('rclone'):
            QMessageBox.warning(self, 'School OneDrive', 'Install rclone first.')
            return
        terminal = shutil.which('x-terminal-emulator')
        if terminal:
            subprocess.Popen([terminal, '-e', 'rclone', 'config'],
                             stdin=subprocess.DEVNULL, start_new_session=True)
        self.status.setText('In rclone config, create a Microsoft OneDrive remote named '
                            'school_onedrive using your school account. '
                            'If no terminal opened, run rclone config manually.')

    def open_folder(self):
        self.course_folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.course_folder)))

    def remote_path(self, proposed=''):
        value, ok = QInputDialog.getText(self, 'School cloud file',
                                         'File path in the school OneDrive:', text=proposed)
        value = value.strip().replace('\\', '/')
        if not ok or not value or value.startswith('/') or any(
                x in ('', '.', '..') for x in value.split('/')):
            return None
        return value

    def download(self):
        if not remote_ready():
            self.status.setText('Configure school_onedrive first.')
            return
        cloud = self.remote_path()
        if not cloud:
            return
        folder = self.course_folder / 'Downloads'
        folder.mkdir(parents=True, exist_ok=True)
        local, _ = QFileDialog.getSaveFileName(self, 'Save school file',
                                               str(folder / Path(cloud).name))
        if local:
            self.transfer(REMOTE + ':' + cloud, local)

    def upload(self):
        if not remote_ready():
            self.status.setText('Configure school_onedrive first.')
            return
        local, _ = QFileDialog.getOpenFileName(self, 'Choose school file',
                                               str(self.course_folder))
        if not local:
            return
        cloud = self.remote_path(Path(local).name)
        if cloud:
            self.transfer(local, REMOTE + ':' + cloud)

    def transfer(self, source, target):
        if self.process is not None:
            self.status.setText('A transfer is already running.')
            return
        self.process = QProcess(self)
        self.process.setProgram('rclone')
        self.process.setArguments(['copyto', source, target, '--ignore-existing',
                                   '--transfers', '1', '--max-duration', '3m'])
        self.process.finished.connect(self.finished_transfer)
        self.process.errorOccurred.connect(self.failed_transfer)
        self.status.setText('Transferring without replacing existing files.')
        self.process.start()

    def finished_transfer(self, code, status):
        self.status.setText('Transfer completed.' if code == 0
                            else 'Transfer failed; verify account and file path.')
        self.process.deleteLater()
        self.process = None

    def failed_transfer(self, error):
        self.status.setText('Could not start school OneDrive transfer.')

    def closeEvent(self, event):
        if self.process is not None:
            self.status.setText('Keep this window open until the transfer finishes.')
            event.ignore()
            return
        super().closeEvent(event)
