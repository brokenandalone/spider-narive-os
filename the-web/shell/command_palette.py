"""Fast keyboard navigation for existing workspaces and installed applications."""
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (QApplication, QDialog, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QVBoxLayout)

from navigation_core import display_text, find_items


class CommandPalette(QDialog):
    """Search known apps, existing workspaces, and explicitly listed actions.

    Search text is never interpreted as a shell command or sent to Webbie.
    Applications are launched through the shell's existing XDG catalog.
    """

    def __init__(self, shell):
        super().__init__(shell, Qt.Tool)
        self.shell = shell
        self.setWindowTitle('The Web · Quick Launch')
        self.setAccessibleName('The Web quick launcher')
        self.setObjectName('panel')
        self.resize(700, 520)
        self.setMinimumSize(420, 340)
        self.setStyleSheet(shell._appearance_style())
        layout = QVBoxLayout(self)
        title = QLabel('QUICK LAUNCH')
        title.setFont(QFont('Sans Serif', 20, QFont.Bold))
        layout.addWidget(title)
        help_text = QLabel('Find a workspace, installed application, or desktop action. Ctrl+K opens this launcher.')
        help_text.setWordWrap(True)
        layout.addWidget(help_text)
        self.search = QLineEdit()
        self.search.setPlaceholderText('Type an app, workspace, or action…')
        self.search.setAccessibleName('Quick Launch search')
        self.search.textChanged.connect(self.refresh)
        self.search.returnPressed.connect(self.activate_first)
        self.search.installEventFilter(self)
        layout.addWidget(self.search)
        self.matches = QListWidget()
        self.matches.setAccessibleName('Matching workspaces, applications and actions')
        self.matches.itemActivated.connect(self.activate)
        self.matches.currentItemChanged.connect(lambda current, previous: self.update_pin())
        layout.addWidget(self.matches, 1)
        controls = QHBoxLayout()
        self.pin_button = QPushButton('Pin selected')
        self.pin_button.clicked.connect(self.toggle_pin)
        controls.addWidget(self.pin_button)
        activate = QPushButton('Open selected')
        activate.clicked.connect(self.activate_first)
        controls.addWidget(activate)
        clear_recent = QPushButton('Clear recent')
        clear_recent.setToolTip('Clear launcher history from this user profile. Pinned items stay.')
        clear_recent.clicked.connect(self.clear_recent)
        controls.addWidget(clear_recent)
        close = QPushButton('Close')
        close.clicked.connect(self.hide)
        controls.addWidget(close)
        layout.addLayout(controls)
        foot = QLabel('↑ ↓ Navigate     Enter Open     Esc Close     Pin saves locally · windows from X11')
        foot.setWordWrap(True)
        layout.addWidget(foot)
        self.refresh()

    def eventFilter(self, watched, event):
        if watched is self.search and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Down, Qt.Key_Up):
                if self.matches.count():
                    row = self.matches.currentRow()
                    step = 1 if event.key() == Qt.Key_Down else -1
                    self.matches.setCurrentRow(min(max(row + step, 0), self.matches.count() - 1))
                return True
            if event.key() == Qt.Key_Escape:
                self.hide()
                return True
        return super().eventFilter(watched, event)

    def show_palette(self):
        if self.isVisible():
            self.hide()
            return
        self.setStyleSheet(self.shell._appearance_style())
        self.refresh()
        screen = self.shell.screen() or QApplication.primaryScreen()
        bounds = screen.availableGeometry()
        self.resize(min(720, max(420, bounds.width() - 32)),
                    min(560, max(340, bounds.height() - 32)))
        self.move(bounds.left() + (bounds.width() - self.width()) // 2,
                  bounds.top() + min(100, max(4, (bounds.height() - self.height()) // 4)))
        self.show()
        self.raise_()
        self.activateWindow()
        self.search.setFocus()
        self.search.selectAll()

    def refresh(self):
        selected = self.current_target()
        nav = self.shell.navigation_state
        self.matches.clear()
        favorites = [tuple(row) for row in nav.get('favorites', ())]
        recents = [tuple(row) for row in nav.get('recent', ())]
        results = find_items(self.search.text(),
                             self.shell.workspaces_for_navigation(),
                             self.shell.installed_apps, favorites, recents,
                             windows=self.shell.visible_launcher_windows())
        for result in results:
            entry = QListWidgetItem(display_text(
                result, (result.kind, result.ident) in favorites))
            entry.setData(Qt.UserRole, (result.kind, result.ident))
            entry.setToolTip(result.detail)
            self.matches.addItem(entry)
            if (result.kind, result.ident) == selected:
                self.matches.setCurrentItem(entry)
        if not results:
            empty = QListWidgetItem('Nothing matched. Try a different name.')
            empty.setFlags(Qt.NoItemFlags)
            self.matches.addItem(empty)
        if self.matches.count() and self.matches.currentItem() is None and results:
            self.matches.setCurrentRow(0)
        self.update_pin()

    def current_target(self):
        item = self.matches.currentItem()
        pair = item.data(Qt.UserRole) if item else None
        return tuple(pair) if isinstance(pair, (tuple, list)) and len(pair) == 2 else None

    def update_pin(self):
        choice = self.current_target()
        enabled = choice is not None and choice[0] in ('workspace', 'app')
        self.pin_button.setEnabled(enabled)
        if enabled and list(choice) in self.shell.navigation_state.get('favorites', []):
            self.pin_button.setText('Unpin selected')
        else:
            self.pin_button.setText('Pin selected')

    def toggle_pin(self):
        choice = self.current_target()
        if choice and choice[0] in ('workspace', 'app'):
            self.shell.toggle_navigation_pin(*choice)
            self.refresh()

    def clear_recent(self):
        if not self.shell.navigation_state.get('recent'):
            return
        answer = QMessageBox.question(
            self, 'Clear recent launcher history?',
            'Clear recently opened workspaces and applications?\n'
            'Pinned items and open tabs will stay unchanged.',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer == QMessageBox.Yes:
            self.shell.clear_recent_navigation()

    def activate_first(self):
        item = self.matches.currentItem()
        if item is not None:
            self.activate(item)

    def activate(self, item):
        choice = item.data(Qt.UserRole)
        if not isinstance(choice, (tuple, list)) or len(choice) != 2:
            return
        kind, ident = choice
        self.hide()
        if kind == 'workspace':
            self.shell.open_workspace(ident)
        elif kind == 'app':
            self.shell.open_installed(ident)
        elif kind == 'action':
            self.shell.execute_palette_action(ident)
        elif kind == 'window':
            self.shell.activate_launcher_window(ident)
