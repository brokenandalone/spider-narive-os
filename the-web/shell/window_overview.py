"""Discoverable all-windows overview for The Web's X11 session.

Uses standard window-manager requests. Closing sends WM_DELETE_WINDOW so apps
can request saving work. Never force-kills a program or inspects its content.
"""
import re
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QListWidget, QListWidgetItem, QPushButton)
from desktop import list_tasks, wm_command, minimize_window, maximize_window, close_window

_ID = re.compile(r'0x[0-9a-fA-F]+\Z')

def valid_id(ident):
    return isinstance(ident, str) and _ID.fullmatch(ident) is not None and int(ident, 16) > 0

class WindowWorker(QThread):
    ready = pyqtSignal(object)
    def __init__(self, excluded, parent=None):
        super().__init__(parent)
        self.excluded = tuple(excluded)
    def run(self):
        try:
            self.ready.emit(list_tasks(self.excluded))
        except Exception:
            self.ready.emit([])

class WindowOverview(QWidget):
    def __init__(self, parent=None, excluded=None):
        super().__init__(parent)
        self.setWindowTitle('Spider OS · Open Windows')
        self.setObjectName('spiderWindowOverview')
        self._exclude = excluded or (lambda: ())
        self.windows = []
        self.worker = None
        layout = QVBoxLayout(self)
        header = QLabel('Open Windows')
        header.setStyleSheet('font-weight:bold;font-size:17px')
        layout.addWidget(header)
        self.search = QLineEdit()
        self.search.setPlaceholderText('Find an open application…')
        layout.addWidget(self.search)
        self.search.textChanged.connect(self.apply_filter)
        self.list = QListWidget()
        self.list.setAccessibleName('Open X11 application windows')
        self.list.itemDoubleClicked.connect(lambda _: self.activate())
        layout.addWidget(self.list, 1)
        self.status = QLabel('Checking running windows…')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        row = QHBoxLayout()
        for label, callback in (
            ('Activate', self.activate),
            ('Minimize', self.minimize),
            ('Maximize / Restore', self.maximize),
            ('Close', self.close_selected),
        ):
            control = QPushButton(label)
            control.clicked.connect(callback)
            row.addWidget(control)
        layout.addLayout(row)
        self.refresh_button = QPushButton('Refresh windows')
        self.refresh_button.clicked.connect(self.refresh)
        layout.addWidget(self.refresh_button)
        self.refresh()

    def refresh(self):
        if self.worker and self.worker.isRunning():
            return
        self.status.setText('Checking open X11 windows…')
        self.refresh_button.setEnabled(False)
        self.worker = WindowWorker(self._exclude(), self)
        self.worker.ready.connect(self.show_windows)
        self.worker.finished.connect(lambda: self.refresh_button.setEnabled(True))
        self.worker.start()

    def show_windows(self, result):
        self.windows = [(w.ident, str(w.title)[:180]) for w in result
                        if valid_id(getattr(w,'ident',None))]
        self.apply_filter()
        self.status.setText(f'{len(self.windows)} windows found.' if self.windows
                            else 'No regular X11 application windows detected. Check wmctrl.')

    def apply_filter(self):
        query = self.search.text().casefold()
        previous = self.selected_id()
        self.list.clear()
        for ident, title in self.windows:
            if query and query not in title.casefold():
                continue
            item = QListWidgetItem(title or ('Window '+ident))
            item.setData(Qt.UserRole, ident)
            item.setToolTip('Window '+ident+'\nClose requests normal unsaved-document prompts.')
            self.list.addItem(item)
            if ident == previous:
                self.list.setCurrentItem(item)
        if self.list.count() and self.list.currentItem() is None:
            self.list.setCurrentRow(0)

    def selected_id(self):
        item = self.list.currentItem()
        candidate = item.data(Qt.UserRole) if item else None
        return candidate if valid_id(candidate) else None

    def activate(self):
        ident = self.selected_id()
        if ident is not None:
            wm_command('-i','-a',ident)

    def minimize(self):
        ident = self.selected_id()
        if ident is not None and not minimize_window(ident):
            self.status.setText('Unable to minimize this window using X11.')

    def maximize(self):
        ident = self.selected_id()
        if ident is not None:
            maximize_window(ident)

    def close_selected(self):
        ident = self.selected_id()
        if ident is not None:
            # The application may reject closing to prompt the user to save.
            close_window(ident)
            self.status.setText('Close requested. The application may ask you to save.')

    def closeEvent(self,event):
        if self.worker and self.worker.isRunning():
            event.ignore()
        else:
            event.accept()
