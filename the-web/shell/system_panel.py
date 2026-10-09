"""Native System/Recovery inspection using the existing desktop widget style."""
from PyQt5.QtCore import QThread, pyqtSignal
import json
from pathlib import Path
from PyQt5.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QTabWidget, QTextEdit, QVBoxLayout, QWidget
from system_status import collect, file_snapshot, health_summary, service_states
from audio_controls import adjust_audio


class StatusWorker(QThread):
    result = pyqtSignal(object)
    failed = pyqtSignal()

    def __init__(self, root, parent=None, services_only=False):
        super().__init__(parent)
        self.root, self.services_only = root, services_only

    def run(self):
        try: self.result.emit(service_states() if self.services_only else collect(self.root))
        except Exception: self.failed.emit()


class AudioWorker(StatusWorker):
    error = pyqtSignal(str)

    def __init__(self, root, action, parent):
        super().__init__(root, parent); self.action = action

    def run(self):
        try:
            adjust_audio(self.action); self.result.emit(collect(self.root))
        except (RuntimeError, ValueError) as error:
            self.error.emit(str(error))


class SystemPanel(QWidget):
    def __init__(self, root, recovery=False):
        super().__init__()
        self.root, self.worker = root, None
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Recovery and backups' if recovery else 'System overview'))
        self.status = QLabel('Read-only inspection. Refresh to check services and audio.')
        self.status.setWordWrap(True); layout.addWidget(self.status)
        self.refresh_button = QPushButton('Refresh system status'); self.refresh_button.setMinimumHeight(44)
        self.refresh_button.clicked.connect(self.refresh); layout.addWidget(self.refresh_button)
        self.export_button = QPushButton('Export health report'); self.export_button.setMinimumHeight(44)
        self.export_button.clicked.connect(self.export_report); layout.addWidget(self.export_button)
        self.tabs = QTabWidget(); layout.addWidget(self.tabs)
        self.tables = {}
        for key, title, headings in [('health', 'Health', ['Component', 'Finding', 'Next step']),
                                    ('overview', 'Overview', ['Property', 'Value']),
                                    ('services', 'Services', ['Service', 'Unit', 'State', 'Detail', 'Startup']),
                                    ('storage', 'Storage', ['Location', 'Path', 'Total', 'Free', 'Used']),
                                    ('backups', 'Recovery', ['Type', 'Backup', 'Location'])]:
            table = QTableWidget(0, len(headings)); table.setHorizontalHeaderLabels(headings)
            table.setEditTriggers(QTableWidget.NoEditTriggers); table.horizontalHeader().setStretchLastSection(True)
            self.tables[key] = table; self.tabs.addTab(table, title)
        self.audio_page = QWidget(); audio_layout = QVBoxLayout(self.audio_page)
        self.volume = QLabel('Refresh to read output volume.'); audio_layout.addWidget(self.volume)
        controls = QHBoxLayout(); audio_layout.addLayout(controls); self.audio_buttons = []
        for text, action in [('Volume −', 'Down'), ('Mute / Unmute', 'Mute'), ('Volume +', 'Up')]:
            button = QPushButton(text); button.setMinimumHeight(44)
            button.clicked.connect(lambda checked=False, name=action: self.change_audio(name)); controls.addWidget(button); self.audio_buttons.append(button)
        self.audio = QTextEdit(); self.audio.setReadOnly(True); audio_layout.addWidget(self.audio)
        self.tabs.addTab(self.audio_page, 'Audio')
        layout.addWidget(QLabel('Backups listed here are available copies, not proof that rollback has been tested.'))
        self.render(file_snapshot(root))
        if recovery: self.tabs.setCurrentWidget(self.tables['backups'])

    def refresh(self):
        if self.worker and self.worker.isRunning(): return
        if self.worker: self.worker.deleteLater()
        self.refresh_button.setEnabled(False); self.status.setText('Checking services and audio…')
        self.worker = StatusWorker(self.root, self)
        self.worker.result.connect(self.render)
        self.worker.failed.connect(lambda: self.status.setText('Status check failed. Refresh to retry.'))
        self.worker.finished.connect(lambda: self.refresh_button.setEnabled(True))
        self.worker.start()

    def render(self, report):
        self.report = dict(report)
        self.report.setdefault('health', health_summary(report))
        report = self.report
        for key, table in self.tables.items():
            if key not in report: continue
            rows = report[key]; table.setRowCount(len(rows))
            for row, values in enumerate(rows):
                for column, value in enumerate(values): table.setItem(row, column, QTableWidgetItem(str(value)))
            table.resizeColumnsToContents()
        self.audio.setPlainText(report.get('audio', 'Refresh to inspect the current audio stack.'))
        self.volume.setText(report.get('volume', 'Refresh to read output volume.'))
        if 'checkedAt' in report: self.status.setText('Status checked at ' + report['checkedAt'] + '. No settings or services changed.')

    def change_audio(self, action):
        if self.worker and self.worker.isRunning(): return
        if self.worker: self.worker.deleteLater()
        self.refresh_button.setEnabled(False)
        for button in self.audio_buttons: button.setEnabled(False)
        self.status.setText('Changing output audio…')
        self.worker = AudioWorker(self.root, action, self)
        self.worker.result.connect(self.render_audio); self.worker.error.connect(self.status.setText)
        self.worker.finished.connect(lambda: self.refresh_button.setEnabled(True))
        self.worker.finished.connect(lambda: [button.setEnabled(True) for button in self.audio_buttons])
        self.worker.start()

    def render_audio(self, report):
        self.render(report)
        self.status.setText('Output audio updated. ' + report.get('volume', 'Refresh to read volume.'))

    def export_report(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Save health report', str(Path.home() / 'Spider-Health-Report.json'), 'JSON report (*.json)')
        if not path: return
        try:
            Path(path).write_text(json.dumps(self.report, indent=2) + '\n')
            self.status.setText('Health report saved. It contains system/device names and backup paths; review it before sharing.')
        except OSError as error:
            self.status.setText('Could not save report: ' + str(error))

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning(): event.ignore()
        else: event.accept()
