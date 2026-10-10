"""Manual school OneDrive access; never share Webbie personal OneDrive credentials."""
import json
import shutil
import subprocess
from pathlib import Path
from PyQt5.QtCore import Qt, QProcess, QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QMessageBox, QFileDialog, QInputDialog, QListWidget, QListWidgetItem

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
        self.browse_process = None
        self.remote_folder = ''
        layout = QVBoxLayout(self)
        note = QLabel('Connect your school Microsoft account separately from personal OneDrive. '
                      'No files are transferred without your choosing them.')
        note.setWordWrap(True)
        layout.addWidget(note)
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.PlainText)
        layout.addWidget(self.status)
        self.files = QListWidget()
        self.files.itemDoubleClicked.connect(self.select_remote_item)
        layout.addWidget(self.files)
        for title, handler in [
            ('Open Microsoft 365 school account', self.open_school),
            ('Configure school OneDrive', self.configure),
            ('Browse school folders', self.browse),
            ('Parent folder', self.parent_folder),
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


    def browse(self):
        if not remote_ready():
            self.status.setText('Connect school OneDrive first.')
            return
        if self.browse_process is not None:
            return
        self.browse_process = QProcess(self)
        self.browse_process.setProgram('rclone')
        self.browse_process.setArguments(
            ['lsjson', REMOTE + ':' + self.remote_folder, '--max-depth', '1',
             '--max-duration', '20s'])
        self.browse_process.finished.connect(self.list_finished)
        self.browse_process.errorOccurred.connect(self.list_error)
        self.status.setText('Reading school folder...')
        self.browse_process.start()

    def list_finished(self, code, status):
        process = self.browse_process
        if process is None:
            return
        try:
            if code != 0:
                self.status.setText('School folder unavailable. Check sign-in and permissions.')
                return
            rows = json.loads(bytes(process.readAllStandardOutput()).decode('utf-8'))
            if not isinstance(rows, list):
                raise ValueError('Invalid file listing')
            self.files.clear()
            for row in sorted(rows, key=lambda x: (not x.get('IsDir', False), x.get('Name', ''))):
                name = row.get('Name')
                if not isinstance(name, str) or not name or '/' in name or name in ('.', '..'):
                    continue
                item = QListWidgetItem(('[Folder] ' if row.get('IsDir') else '[File] ') + name)
                item.setData(Qt.UserRole, (name, bool(row.get('IsDir'))))
                self.files.addItem(item)
            self.status.setText('School folder: /' + self.remote_folder)
        except (ValueError, UnicodeError, TypeError):
            self.status.setText('Invalid school drive listing.')
        finally:
            process.deleteLater()
            self.browse_process = None

    def list_error(self, error):
        self.status.setText('Unable to start OneDrive folder listing.')

    def select_remote_item(self, item):
        name, is_dir = item.data(Qt.UserRole)
        if is_dir:
            self.remote_folder = '/'.join(filter(None, (self.remote_folder, name)))
            self.browse()
        else:
            self.status.setText('Selected ' + name + '. Choose Download to save it.')

    def parent_folder(self):
        self.remote_folder = '/'.join(self.remote_folder.split('/')[:-1])
        self.browse()

    def download(self):
        if not remote_ready():
            self.status.setText('Configure school_onedrive first.')
            return
        item = self.files.currentItem()
        selected = item.data(Qt.UserRole) if item is not None else None
        proposed = ('/'.join(filter(None, (self.remote_folder, selected[0])))
                    if selected and not selected[1] else '')
        cloud = self.remote_path(proposed)
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
        cloud = self.remote_path('/'.join(filter(None, (self.remote_folder, Path(local).name))))
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
        if self.process is not None or self.browse_process is not None:
            self.status.setText('Keep this window open until the operation finishes.')
            event.ignore()
            return
        super().closeEvent(event)
