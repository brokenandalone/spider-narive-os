"""User-initiated recovery window for The Web's native workspace UI."""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QVBoxLayout)

from workspaces import NATIVE
from workspace_health import check_workspaces

class WorkspaceRecovery(QDialog):
    def __init__(self, shell):
        super().__init__(shell)
        self.shell = shell
        self.setWindowTitle('The Web · Workspace Recovery')
        self.setObjectName('spiderWorkspaceRecovery')
        self.resize(660, 570)
        self.setMinimumSize(460, 360)
        layout = QVBoxLayout(self)
        heading = QLabel('WORKSPACE DIAGNOSTICS & RECOVERY')
        heading.setStyleSheet('font-size:19px;font-weight:bold')
        layout.addWidget(heading)
        note = QLabel('Read-only source checks. Fix or retry a workspace without '
                      'replacing files. Checkpoints save tab layout only, not manuscripts or documents.')
        note.setWordWrap(True)
        layout.addWidget(note)
        self.list = QListWidget()
        self.list.setAccessibleName('Spider OS workspace health')
        self.list.itemDoubleClicked.connect(lambda _: self.retry_selected())
        layout.addWidget(self.list, 1)
        self.status = QLabel('Inspecting workspaces…')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        first = QHBoxLayout()
        refresh = QPushButton('Refresh diagnostics')
        refresh.clicked.connect(self.refresh)
        first.addWidget(refresh)
        retry = QPushButton('Retry selected workspace')
        retry.clicked.connect(self.retry_selected)
        first.addWidget(retry)
        layout.addLayout(first)
        second = QHBoxLayout()
        checkpoint = QPushButton('Save layout checkpoint')
        checkpoint.clicked.connect(self.create_checkpoint)
        second.addWidget(checkpoint)
        restore = QPushButton('Restore checkpoint')
        restore.clicked.connect(self.restore_checkpoint)
        second.addWidget(restore)
        layout.addLayout(second)
        foot = QLabel('Safe-start from terminal: python3 the-web/shell/main.py --safe-workspaces')
        foot.setWordWrap(True)
        layout.addWidget(foot)
        self.refresh()

    def refresh(self):
        rows = check_workspaces(
            self.shell.spider_root(), self.shell.workspaces_for_navigation(),
            NATIVE, loaded=self.shell.workspace_widgets,
            failures=self.shell.workspace_load_errors)
        current = self.list.currentItem()
        selected = current.data(Qt.UserRole) if current else None
        self.list.clear()
        for row in rows:
            item = QListWidgetItem(f'{row.label}    [{row.status}]    {row.detail}')
            item.setData(Qt.UserRole, row.ident)
            item.setToolTip(row.detail)
            self.list.addItem(item)
            if row.ident == selected:
                self.list.setCurrentItem(item)
        issues = sum(row.status in ('needs-attention', 'missing') for row in rows)
        self.status.setText(f'{len(rows)} workspaces checked · {issues} require attention. '
                            'File contents and private settings were not read.')

    def retry_selected(self):
        item = self.list.currentItem()
        if item is None:
            self.status.setText('Select a workspace to open or retry.')
            return
        name = item.data(Qt.UserRole)
        if name not in self.shell.workspaces_for_navigation():
            return
        self.shell.retry_workspace(name)
        self.refresh()
        if name in self.shell.workspace_load_errors:
            self.status.setText('Retry failed. The workspace source may require repair.')
        else:
            self.status.setText('Workspace open request completed.')

    def create_checkpoint(self):
        try:
            self.shell.save_layout_checkpoint()
        except (OSError, ValueError) as error:
            self.status.setText('Unable to save layout checkpoint: ' + str(error))
        else:
            self.status.setText('Workspace tab layout checkpoint saved privately.')

    def restore_checkpoint(self):
        answer = QMessageBox.question(
            self, 'Restore workspace layout?',
            'Restore previously saved workspace tabs? Existing editors will '
            'remain open. This does not undo document changes.',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        if self.shell.restore_layout_checkpoint():
            self.status.setText('Checkpoint layout restored. Existing work remains open.')
        else:
            self.status.setText('No valid checkpoint found, or recovery was blocked.')
        self.refresh()
