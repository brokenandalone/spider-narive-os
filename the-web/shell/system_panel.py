"""Native System/Recovery inspection using the existing desktop widget style."""
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QLabel, QPushButton, QTableWidget, QTableWidgetItem, QTabWidget, QTextEdit, QVBoxLayout, QWidget
from system_status import collect, file_snapshot, service_states


class StatusWorker(QThread):
    result = pyqtSignal(object)
    failed = pyqtSignal()

    def __init__(self, root, parent=None, services_only=False):
        super().__init__(parent)
        self.root, self.services_only = root, services_only

    def run(self):
        try: self.result.emit(service_states() if self.services_only else collect(self.root))
        except Exception: self.failed.emit()


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
        self.tabs = QTabWidget(); layout.addWidget(self.tabs)
        self.tables = {}
        for key, title, headings in [('overview', 'Overview', ['Property', 'Value']),
                                    ('services', 'Services', ['Service', 'Unit', 'State', 'Detail', 'Startup']),
                                    ('storage', 'Storage', ['Location', 'Path', 'Total', 'Free', 'Used']),
                                    ('backups', 'Recovery', ['Type', 'Backup', 'Location'])]:
            table = QTableWidget(0, len(headings)); table.setHorizontalHeaderLabels(headings)
            table.setEditTriggers(QTableWidget.NoEditTriggers); table.horizontalHeader().setStretchLastSection(True)
            self.tables[key] = table; self.tabs.addTab(table, title)
        self.audio = QTextEdit(); self.audio.setReadOnly(True); self.tabs.addTab(self.audio, 'Audio')
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
        for key, table in self.tables.items():
            if key not in report: continue
            rows = report[key]; table.setRowCount(len(rows))
            for row, values in enumerate(rows):
                for column, value in enumerate(values): table.setItem(row, column, QTableWidgetItem(str(value)))
            table.resizeColumnsToContents()
        self.audio.setPlainText(report.get('audio', 'Refresh to inspect the current audio stack.'))
        if 'checkedAt' in report: self.status.setText('Status checked at ' + report['checkedAt'] + '. No settings or services changed.')

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning(): event.ignore()
        else: event.accept()
