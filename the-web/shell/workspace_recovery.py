"""User-initiated recovery window for The Web's native workspace UI."""
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QVBoxLayout)

from workspaces import NATIVE
from workspace_health import check_workspaces
from desktop_diagnostics import build_safe_report, report_text
from desktop_service_health import (probe_user_services, health_totals,
                                    service_brief)

class ServiceHealthWorker(QThread):
    """Bounded read-only probe, never block Qt event handling."""
    result = pyqtSignal(object)

    def run(self):
        self.result.emit(probe_user_services())



class WorkspaceRecovery(QDialog):
    def __init__(self, shell):
        super().__init__(shell)
        self.shell = shell
        self.setWindowTitle('The Web · Workspace Recovery')
        self.setObjectName('spiderWorkspaceRecovery')
        self.resize(750, 670)
        self.setMinimumSize(500, 410)
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
        self.queue_status = QLabel('No workspace restoration in progress.')
        self.queue_status.setWordWrap(True)
        self.queue_status.setAccessibleName('Live workspace restore progress')
        layout.addWidget(self.queue_status)
        services_heading = QLabel('SYSTEM SERVICES  ·  READ ONLY')
        services_heading.setAccessibleName('Spider OS user-service status')
        layout.addWidget(services_heading)
        self.service_health = QListWidget()
        self.service_health.setAccessibleName('Webbie and Spider service health')
        self.service_health.setMaximumHeight(155)
        layout.addWidget(self.service_health)
        service_actions = QHBoxLayout()
        self.service_check = QPushButton('Check user services')
        self.service_check.clicked.connect(self.check_services)
        service_actions.addWidget(self.service_check)
        self.webbie_health = QPushButton('Ask Webbie about status')
        self.webbie_health.clicked.connect(self.prepare_webbie_status)
        self.webbie_health.setToolTip(
            'Prepare a status-only question. You review and send it yourself.')
        service_actions.addWidget(self.webbie_health)
        layout.addLayout(service_actions)
        self.service_worker = None
        self.service_rows = []
        queue_row = QHBoxLayout()
        self.pause_restore = QPushButton('Pause restoring')
        self.pause_restore.clicked.connect(self.toggle_restore_pause)
        queue_row.addWidget(self.pause_restore)
        self.next_restore = QPushButton('Load selected next')
        self.next_restore.clicked.connect(self.prioritize_selected)
        queue_row.addWidget(self.next_restore)
        self.skip_restore = QPushButton('Skip selected for now')
        self.skip_restore.clicked.connect(self.skip_selected)
        queue_row.addWidget(self.skip_restore)
        layout.addLayout(queue_row)
        interrupt_row = QHBoxLayout()
        self.stop_restore = QPushButton('Stop restoring')
        self.stop_restore.clicked.connect(self.stop_restoring)
        interrupt_row.addWidget(self.stop_restore)
        self.adopt_layout = QPushButton('Save current layout as default')
        self.adopt_layout.clicked.connect(self.adopt_current_layout)
        interrupt_row.addWidget(self.adopt_layout)
        layout.addLayout(interrupt_row)
        self.saved_restore = QPushButton('Resume last saved session (safe-start)')
        self.saved_restore.clicked.connect(self.resume_saved_session)
        layout.addWidget(self.saved_restore)
        copy_diagnostics = QPushButton('Copy safe diagnostic report')
        copy_diagnostics.setToolTip('Copy workspace names, status and timings only. No private files, windows or clipboard history are read.')
        copy_diagnostics.clicked.connect(self.copy_safe_diagnostics)
        layout.addWidget(copy_diagnostics)
        foot = QLabel('Safe-start from terminal: python3 the-web/shell/main.py --safe-workspaces')
        foot.setWordWrap(True)
        layout.addWidget(foot)
        self.refresh()
        self.restore_timer = QTimer(self)
        self.restore_timer.timeout.connect(self.update_restore_controls)
        self.restore_timer.start(700)
        self.service_timer = QTimer(self)
        self.service_timer.timeout.connect(self.check_services_if_visible)
        self.service_timer.start(60000)

    def refresh(self):
        rows = check_workspaces(
            self.shell.spider_root(), self.shell.workspaces_for_navigation(),
            NATIVE, loaded=self.shell.workspace_widgets,
            failures=self.shell.workspace_load_errors)
        current = self.list.currentItem()
        selected = current.data(Qt.UserRole) if current else None
        self.list.clear()
        plan = self.shell._restore_plan
        queued = set(plan.pending) if plan is not None else set()
        for row in rows:
            label = 'queued' if row.ident in queued else row.status
            item = QListWidgetItem(f'{row.label}    [{label}]    {row.detail}')
            item.setData(Qt.UserRole, row.ident)
            item.setToolTip(row.detail)
            self.list.addItem(item)
            if row.ident == selected:
                self.list.setCurrentItem(item)
        issues = sum(row.status in ('needs-attention', 'missing') for row in rows)
        timings = self.shell.workspace_load_seconds
        measured = sorted(((elapsed, ident) for ident, elapsed in timings.items()
                           if isinstance(elapsed, (int, float))), reverse=True)
        slow = ', '.join(f'{self.shell.workspaces_for_navigation().get(ident, ident)} '
                         f'{elapsed:.2f}s' for elapsed, ident in measured[:3])
        note = 'Slowest loaded: ' + slow + '. ' if measured else ''
        if self.shell.is_staged_restoring():
            done, count = self.shell._restore_plan.progress()
            note = f'Background restore {done}/{count}. ' + note
        self.status.setText(f'{len(rows)} workspaces checked · {issues} require attention. '
                            + note + 'No private document data collected.')
        self.update_restore_controls()

    def update_restore_controls(self):
        report = self.shell.staged_restore_status()
        active = report is not None
        paused = active and report['paused']
        if active:
            next_id = report['next']
            next_label = self.shell.workspaces_for_navigation().get(next_id, 'None')
            phase = 'Paused' if paused else 'Restoring'
            self.queue_status.setText(
                f"{phase}: {report['processed']}/{report['total']} processed; "
                f"{report['remaining']} queued; "
                f"{len(report['skipped'])} skipped. Next: {next_label}.")
        elif self.shell._preserve_saved_session:
            self.queue_status.setText(
                'Restoration stopped or partly skipped. The saved normal '
                'session remains unchanged until you explicitly save a new layout.')
        else:
            self.queue_status.setText('No workspace restoration in progress.')
        self.pause_restore.setEnabled(active and (paused or report['remaining'] > 0))
        self.pause_restore.setText('Resume restoring' if paused else 'Pause restoring')
        self.stop_restore.setEnabled(active)
        pending = set(self.shell._restore_plan.pending) if active else set()
        item = self.list.currentItem()
        selected = item.data(Qt.UserRole) if item is not None else None
        self.next_restore.setEnabled(active and selected in pending)
        self.skip_restore.setEnabled(active and selected in pending)
        self.adopt_layout.setEnabled(not active)
        self.saved_restore.setEnabled(self.shell.safe_mode and not active)

    def toggle_restore_pause(self):
        report = self.shell.staged_restore_status()
        if report is None:
            self.status.setText('No workspace restoration is currently running.')
            return
        changed = (self.shell.resume_staged_restore() if report['paused']
                   else self.shell.pause_staged_restore())
        if changed:
            self.status.setText('Workspace restoration resumed.' if report['paused']
                                else 'Workspace restoration paused.')
        self.update_restore_controls()

    def prioritize_selected(self):
        item = self.list.currentItem()
        name = item.data(Qt.UserRole) if item is not None else None
        if name and self.shell.prioritize_staged_workspace(name):
            self.status.setText('Selected workspace moved to the front of the queue.')
        self.update_restore_controls()

    def skip_selected(self):
        item = self.list.currentItem()
        name = item.data(Qt.UserRole) if item is not None else None
        if name and self.shell.skip_staged_workspace(name):
            self.status.setText('Workspace skipped for this startup. '
                                'The previous saved layout is preserved.')
            self.refresh()

    def stop_restoring(self):
        if not self.shell.is_staged_restoring():
            return
        answer = QMessageBox.question(
            self, 'Stop restoring workspace tabs?',
            'Stop reopening the remaining saved workspace tabs? Already open '
            'tabs and unsaved work are not closed. The previous saved layout '
            'will be preserved until you explicitly save a new one.',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer == QMessageBox.Yes:
            self.shell.stop_staged_restore()
            self.status.setText('Restoration stopped. The saved layout was preserved.')
            self.refresh()

    def adopt_current_layout(self):
        if self.shell.is_staged_restoring():
            return
        answer = QMessageBox.question(
            self, 'Save this as the default workspace layout?',
            'Replace the saved workspace tab arrangement with the tabs '
            'currently open? This will not change document contents.',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer == QMessageBox.Yes and self.shell.adopt_current_layout():
            self.status.setText('Current tabs are now the saved startup layout.')
        self.update_restore_controls()

    def copy_safe_diagnostics(self):
        """Never send/upload diagnostics; clipboard copy requires a click."""
        rows = check_workspaces(
            self.shell.spider_root(), self.shell.workspaces_for_navigation(),
            NATIVE, loaded=self.shell.workspace_widgets,
            failures=self.shell.workspace_load_errors)
        report = build_safe_report(
            self.shell.workspaces_for_navigation(),
            [self.shell.tabs.widget(i).property('workspace')
             for i in range(self.shell.tabs.count())],
            self.shell.current_workspace, health=rows,
            load_seconds=self.shell.workspace_load_seconds,
            restore=self.shell.staged_restore_status(),
            applications=len(self.shell.installed_apps),
            open_windows=len(self.shell.visible_launcher_windows()),
            safe_mode=self.shell.safe_mode)
        QApplication.clipboard().setText(report_text(report))
        self.status.setText(
            'Safe diagnostics copied locally. The report contains workspace '
            'identifiers, status, counts and load timings only. Review before sharing.')

    def showEvent(self, event):
        super().showEvent(event)
        self.check_services()

    def check_services_if_visible(self):
        if self.isVisible():
            self.check_services()

    def check_services(self):
        worker = self.service_worker
        if worker is not None and worker.isRunning():
            return
        self.service_check.setEnabled(False)
        self.service_health.clear()
        self.service_health.addItem('Checking user services (read only)…')
        worker = ServiceHealthWorker(self)
        self.service_worker = worker
        worker.result.connect(self.show_service_results)
        worker.finished.connect(self.finish_service_check)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def show_service_results(self, rows):
        self.service_rows = list(rows)[:8]
        self.service_health.clear()
        for item in self.service_rows:
            self.service_health.addItem(f'{item.label}: {item.status}  ·  {item.detail}')
        counts = health_totals(self.service_rows)
        problematic = sum(counts.get(name, 0) for name in
                          ('failed', 'stopped', 'masked', 'not-installed'))
        self.webbie_health.setEnabled(bool(self.service_rows))
        self.status.setText(
            f'Checked {len(self.service_rows)} allowed user services; '
            f'{problematic} may require attention. No changes made.')

    def finish_service_check(self):
        self.service_check.setEnabled(True)
        self.service_worker = None

    def prepare_webbie_status(self):
        if not self.service_rows:
            self.status.setText('Check user services before asking Webbie.')
            return
        brief = service_brief(self.service_rows)
        if self.shell.prepare_webbie_service_question(brief):
            self.status.setText('Webbie draft prepared. Review it and press Send.')
        else:
            self.status.setText('Webbie already has a draft or is busy. Nothing changed.')

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

    def resume_saved_session(self):
        if not self.shell.safe_mode or self.shell.is_staged_restoring():
            self.status.setText('Saved session resume is available only during safe-start.')
            return
        answer = QMessageBox.question(
            self, 'Resume the saved workspace session?',
            'Resume reopening the tabs saved before safe-start? '
            'The Web will load each workspace in turn. Your documents '
            'will not be overwritten.',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer == QMessageBox.Yes:
            if self.shell.restore_last_saved_session():
                self.status.setText('Resuming saved workspace tabs. Use Recovery if one fails.')
            else:
                self.status.setText('No saved session was resumed.')
        self.saved_restore.setEnabled(self.shell.safe_mode)

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
