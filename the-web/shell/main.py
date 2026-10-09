#!/usr/bin/env python3
"""The Web desktop: native workspace tabs, installed applications and taskbar."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from PyQt5.QtCore import Qt, QTimer, QSize, QDateTime
from PyQt5.QtGui import QColor, QFont, QIcon, QKeySequence, QPainter, QPixmap
from PyQt5.QtWidgets import (QApplication, QComboBox, QDialog, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
    QMessageBox, QMenu, QPushButton, QScrollArea, QShortcut, QSplashScreen, QTabWidget, QDockWidget,
    QVBoxLayout, QWidget)

SPIDER_ROOT = Path('/usr/local/lib/spider-os')
if not SPIDER_ROOT.exists():
    SPIDER_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SPIDER_ROOT / 'system'))
from apps import AppUnavailable, media_command
from app_catalog import WORKSPACES, discover_apps, launch_command
from desktop import list_tasks, wm_command, close_window, minimize_window, maximize_window, x11_properties
from wallpapers import WallpaperCatalog
from workspaces import create_native
from workspace_files import workspace_folders, file_open_command
from system_panel import SystemPanel, StatusWorker
from webbie_panel import WebbiePanel
from webbie_overlay import WebbieOverlay
from media_panel import MediaPanel

WALLPAPER = SPIDER_ROOT / 'branding/wallpapers/spider-os-wallpaper.png'
STYLE = '''
QWidget { color:#f5eff8; font-family:'Sans Serif'; }
QWidget#root { background:transparent; }
QWidget#panel, QDialog, QTabWidget::pane { background:rgba(18,13,24,240); border:1px solid #3c2946; border-radius:10px; }
QTabWidget#workspaceTabs[home='true']::pane { background:transparent; border:none; }
QPushButton { font-size:14px; background:rgba(70,25,105,230); border:1px solid #7e22ce; border-radius:8px; padding:7px 12px; color:white; text-align:left; }
QPushButton:hover, QPushButton:checked { background:#6b21a8; border-color:#c084fc; }
QLineEdit, QComboBox, QListWidget { background:#17111f; color:#f5eff8; border:1px solid #5b21b6; border-radius:7px; padding:6px; }
QTextEdit, QTableWidget { background:#17111f; alternate-background-color:#24182f; color:#f5eff8; border:1px solid #5b21b6; selection-background-color:#6b21a8; }
QHeaderView::section { background:#2d193b; color:#f5eff8; padding:6px; border:1px solid #3c2946; }
QMenu { background:#17111f; color:#f5eff8; border:1px solid #7e22ce; }
QMenu::item { padding:8px 18px; }
QMenu::item:selected { background:#6b21a8; }
QToolTip { background:#24182f; color:#f5eff8; border:1px solid #7e22ce; }
QTabBar::tab { background:#17111f; padding:10px 14px; color:#c7b9d1; }
QTabBar::tab:selected { background:#6b21a8; color:white; }
QScrollArea { background:transparent; border:none; }
'''


class WallpaperWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._background = QPixmap()

    def set_background(self, pixmap):
        self._background = pixmap
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        if not self._background.isNull() and self.width() and self.height():
            image = self._background.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            x = (image.width() - self.width()) // 2; y = (image.height() - self.height()) // 2
            painter.drawPixmap(0, 0, image, x, y, self.width(), self.height())
        else:
            painter.fillRect(self.rect(), QColor(8, 6, 11))
        painter.fillRect(self.rect(), QColor(8, 6, 11, 95))


def button(label, callback):
    widget = QPushButton(label)
    widget.setMinimumHeight(44)
    widget.clicked.connect(callback)
    return widget


class StartMenu(QDialog):
    def __init__(self, shell):
        super().__init__(shell, Qt.Popup)
        self.shell = shell
        self.setObjectName('panel'); self.setStyleSheet(STYLE); self.resize(580, 650)
        layout = QVBoxLayout(self)
        heading = QLabel('SPIDER OS  /  Start'); heading.setFont(QFont('Sans Serif', 22, QFont.Bold)); layout.addWidget(heading)
        self.search = QLineEdit(); self.search.setPlaceholderText('Find a workspace or installed app'); layout.addWidget(self.search)
        self.results = QListWidget(); self.results.setIconSize(QSize(28, 28)); layout.addWidget(self.results, 1)
        self.search.textChanged.connect(self.populate); self.results.itemActivated.connect(self.activate)
        actions = QHBoxLayout(); layout.addLayout(actions)
        actions.addWidget(button('Refresh apps', shell.refresh_apps))
        actions.addWidget(button('Lock', shell.lock_session))
        actions.addWidget(button('Log out', shell.logout))
        self.populate()

    def populate(self):
        query = self.search.text().casefold(); self.results.clear()
        for workspace, label in WORKSPACES.items():
            if workspace != 'default' and query in label.casefold():
                item = QListWidgetItem('Workspace  /  ' + label); item.setData(Qt.UserRole, ('workspace', workspace)); self.results.addItem(item)
        for app in self.shell.installed_apps:
            if query in (app.name + ' ' + app.comment + ' ' + WORKSPACES[app.workspace]).casefold():
                item = QListWidgetItem(QIcon.fromTheme(app.icon), app.name + '  /  ' + WORKSPACES[app.workspace])
                item.setData(Qt.UserRole, ('app', app.desktop_id)); self.results.addItem(item)
        if self.results.count():
            self.results.setCurrentRow(0)

    def activate(self, item):
        kind, ident = item.data(Qt.UserRole); self.hide()
        if kind == 'workspace': self.shell.open_workspace(ident)
        else: self.shell.open_installed(ident)

    def show_menu(self, dock):
        if self.isVisible():
            self.hide(); return
        self.populate(); self.move(dock.x(), max(dock.screen().geometry().top(), dock.y() - self.height() - 8))
        self.show(); self.raise_(); self.search.setFocus()


class Taskbar(QWidget):
    def __init__(self, shell):
        super().__init__(None, Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.shell = shell; self.setObjectName('panel'); self.setStyleSheet(STYLE)
        self.setWindowTitle('The Web Taskbar')
        layout = QHBoxLayout(self); layout.setContentsMargins(8, 4, 8, 4)
        self.start = button('Start', lambda: shell.start_menu.show_menu(self)); self.start.setIcon(QIcon(str(SPIDER_ROOT / 'branding/icons/spider-os-logo.png'))); layout.addWidget(self.start)
        layout.addWidget(button('The Web', shell.show_desktop))
        webbie = button('Webbie', shell.open_webbie); webbie.setIcon(QIcon(str(SPIDER_ROOT / 'branding/webbie/webbie-face-v1.png'))); layout.addWidget(webbie)
        self.tasks = QHBoxLayout(); layout.addLayout(self.tasks, 1)
        layout.addWidget(button('Lock', shell.lock_session))
        layout.addWidget(button('Audio', shell.open_audio))
        self.clock = QLabel(); self.clock.setMinimumWidth(155); layout.addWidget(self.clock)
        self.timer = QTimer(self); self.timer.timeout.connect(self.refresh); self.timer.start(2000)
        self.last_tasks = None; self.refresh()

    def position(self):
        geometry = QApplication.primaryScreen().geometry()
        self.setGeometry(geometry.left(), geometry.bottom() - 55, geometry.width(), 56)
        if self.shell.desktop_mode: x11_properties(self, 'DOCK', QApplication.primaryScreen())

    def refresh(self):
        self.clock.setText(QDateTime.currentDateTime().toString('ddd d MMM  HH:mm'))
        excluded = {f'0x{int(self.winId()):08x}', f'0x{int(self.shell.winId()):08x}'}
        tasks = list_tasks(excluded) if self.shell.desktop_mode else []
        screen_width = QApplication.primaryScreen().geometry().width()
        visible_count = max(0, min(2, (screen_width - 800) // 210))
        signature = (screen_width, tuple((task.ident, task.title) for task in tasks))
        if signature == self.last_tasks: return
        self.last_tasks = signature
        while self.tasks.count():
            item = self.tasks.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        for task in tasks[:visible_count]:
            group = QWidget(); row = QHBoxLayout(group); row.setContentsMargins(0, 0, 0, 0); row.setSpacing(2)
            widget = button(task.title[:18], lambda checked=False, ident=task.ident: wm_command('-i', '-a', ident))
            widget.setMaximumWidth(150); widget.setToolTip(task.title + '\nRight-click for Minimize, Maximize / Restore and Close.'); row.addWidget(widget)
            widget.setContextMenuPolicy(Qt.CustomContextMenu)
            menu = QMenu(widget)
            action = menu.addAction('Minimize'); action.triggered.connect(lambda checked=False, ident=task.ident: self.minimize(ident))
            action = menu.addAction('Maximize / Restore'); action.triggered.connect(lambda checked=False, ident=task.ident: maximize_window(ident))
            action = menu.addAction('Close'); action.triggered.connect(lambda checked=False, ident=task.ident: close_window(ident))
            widget.customContextMenuRequested.connect(lambda point, target=widget, context=menu: context.exec_(target.mapToGlobal(point)))
            close = button('×', lambda checked=False, ident=task.ident: close_window(ident))
            close.setFixedWidth(44); close.setAccessibleName('Close ' + task.title)
            close.setToolTip('Close ' + task.title + ' (the app can ask to save)'); row.addWidget(close)
            self.tasks.addWidget(group)
        if len(tasks) > visible_count:
            more = button(f'Windows ({len(tasks) - visible_count})', lambda: None); menu = QMenu(more)
            for task in tasks[visible_count:]:
                window_menu = menu.addMenu(task.title)
                action = window_menu.addAction('Activate'); action.triggered.connect(lambda checked=False, ident=task.ident: wm_command('-i', '-a', ident))
                action = window_menu.addAction('Close'); action.triggered.connect(lambda checked=False, ident=task.ident: close_window(ident))
                action = window_menu.addAction('Minimize'); action.triggered.connect(lambda checked=False, ident=task.ident: self.minimize(ident))
                action = window_menu.addAction('Maximize / Restore'); action.triggered.connect(lambda checked=False, ident=task.ident: maximize_window(ident))
            more.setMenu(menu); self.tasks.addWidget(more)
        self.tasks.addStretch(1)

    def minimize(self, ident):
        if not minimize_window(ident): self.shell.status.setText('Minimize is unavailable for this display connection.')


class TheWeb(QMainWindow):
    def __init__(self, desktop_mode=False, restore=True):
        super().__init__()
        self.desktop_mode = desktop_mode; self.current_workspace = 'default'; self.workspace_widgets = {}; self.app_lists = {}
        self.wallpaper_catalog = WallpaperCatalog(SPIDER_ROOT); self.wallpaper = None
        self.state_path = self.wallpaper_catalog.config.parent / 'desktop.json'
        self.installed_apps = discover_apps(desktops='TheWeb:KDE')
        self.setWindowTitle('The Web | Spider OS'); self.resize(1280, 820); self.setMinimumSize(900, 600); self.setStyleSheet(STYLE)
        if desktop_mode: self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.build_ui(); self.setup_webbie_assistant(); self.webbie_overlay = WebbieOverlay(SPIDER_ROOT); self.face_button.setText('Wake Webbie face' if self.webbie_overlay.face_sleeping else 'Sleep Webbie face'); self.start_menu = StartMenu(self); self.taskbar = Taskbar(self)
        self._shortcut = QShortcut(QKeySequence('Ctrl+Esc'), self); self._shortcut.activated.connect(lambda: self.start_menu.show_menu(self.taskbar))
        self._close_shortcut = QShortcut(QKeySequence('Ctrl+W'), self); self._close_shortcut.activated.connect(lambda: self.close_tab(self.tabs.currentIndex()))
        self.tabs.currentChanged.connect(self.tab_changed); self.tabs.tabCloseRequested.connect(self.close_tab)
        self.set_workspace('default')
        if restore: self.restore_state()
        self.timer = QTimer(self); self.timer.timeout.connect(self.refresh_status); self.timer.start(15000)
        QTimer.singleShot(0, self.refresh_status)

    def build_ui(self):
        root = WallpaperWidget(); root.setObjectName('root'); self.background_surface = root; self.setCentralWidget(root)
        outer = QVBoxLayout(root); outer.setContentsMargins(20, 16, 20, 12)
        header = QHBoxLayout(); outer.addLayout(header)
        logo = QLabel(); logo.setPixmap(QPixmap(str(SPIDER_ROOT / 'branding/icons/spider-os-logo.png')).scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)); header.addWidget(logo)
        title = QLabel('THE WEB'); title.setStyleSheet('font-size:26px; font-weight:bold; color:#e9d5ff; letter-spacing:2px;'); header.addWidget(title)
        header.addWidget(QLabel('YOUR LIFE. ONE WEB.'), 1)
        header.addWidget(button('Ask Webbie', self.toggle_webbie_assistant))
        self.face_button = button('Sleep Webbie face', self.toggle_webbie_face)
        header.addWidget(self.face_button)
        header.addWidget(button('Workspaces', lambda: self.start_menu.show_menu(self.taskbar)))
        self.tabs = QTabWidget(); self.tabs.setObjectName('workspaceTabs'); self.tabs.setProperty('home', True); self.tabs.setTabsClosable(True); self.tabs.setMovable(False); outer.addWidget(self.tabs, 1)
        home = QWidget(); home.setObjectName('root'); home_layout = QVBoxLayout(home)
        welcome = QLabel('Your workspaces'); welcome.setFont(QFont('Sans Serif', 22, QFont.Bold)); home_layout.addWidget(welcome)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.viewport().setAutoFillBackground(False); home_layout.addWidget(scroll, 1)
        content = QWidget(); content.setObjectName('root'); scroll.setWidget(content); grid = QGridLayout(content); grid.setAlignment(Qt.AlignTop | Qt.AlignLeft); grid.setHorizontalSpacing(14); grid.setVerticalSpacing(14)
        for index, (workspace, label) in enumerate((k, v) for k, v in WORKSPACES.items() if k != 'default'):
            shortcut = button(label, lambda checked=False, name=workspace: self.open_workspace(name)); shortcut.setFixedWidth(175)
            grid.addWidget(shortcut, index // 4, index % 4)
        home.setProperty('workspace', 'default'); self.tabs.addTab(home, 'The Web'); self.workspace_widgets['default'] = home
        self.tabs.tabBar().setTabButton(0, self.tabs.tabBar().RightSide, None)
        wallpaper_row = QHBoxLayout(); outer.addLayout(wallpaper_row)
        self.background_picker = QComboBox()
        for name, label in WORKSPACES.items(): self.background_picker.addItem(label, name)
        self.background_picker.setMinimumHeight(40)
        self.background_picker.currentIndexChanged.connect(lambda index: self.open_workspace(self.background_picker.itemData(index)))
        wallpaper_row.addWidget(self.background_picker)
        self.wallpaper_picker = QComboBox(); self.wallpaper_picker.setMinimumHeight(40); self.wallpaper_picker.setIconSize(QSize(64, 36))
        self.wallpaper_picker.addItem('Original workspace background', 'original')
        for entry in self.wallpaper_catalog.entries:
            self.wallpaper_picker.addItem(QIcon(str(SPIDER_ROOT / entry['file'])), entry['group'] + ' / ' + entry['label'], entry['id'])
        self.wallpaper_picker.currentIndexChanged.connect(self.choose_wallpaper); wallpaper_row.addWidget(self.wallpaper_picker, 1)
        self.status = QLabel('Spider OS ready.'); self.service_status = QLabel(); outer.addWidget(self.status); outer.addWidget(self.service_status)


    # One persistent Webbie panel covers every native and generic workspace.
    # It reuses the existing user-owned UNIX socket with no daemon changes.
    WEBBIE_MODES = {
        'default': 'Normal', 'webbie': 'Normal',
        'author': 'Author Editor', 'studio': 'Studio Producer',
        'study': 'School Tutor', 'media': 'AI DJ',
        'forage': 'Researcher', 'deep-forage': 'Researcher',
        'dev-bay': 'Developer', 'art-lab': 'Creative Assistant',
        'communications': 'Communications Assistant',
        'kali-bay': 'Security Assistant', 'system': 'System Technician',
        'recovery': 'Recovery Assistant', 'games': 'Normal',
    }

    def setup_webbie_assistant(self):
        self.webbie_assistant = WebbiePanel(SPIDER_ROOT)
        self.webbie_dock = QDockWidget('WEBBIE | WORKSPACE ASSISTANT', self)
        self.webbie_dock.setObjectName('webbieWorkspaceDock')
        self.webbie_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.webbie_dock.setWidget(self.webbie_assistant)
        self.webbie_dock.setMinimumWidth(330)
        self.addDockWidget(Qt.RightDockWidgetArea, self.webbie_dock)
        self.webbie_dock.hide()
        self.webbie_dock.visibilityChanged.connect(
            lambda visible: self.update_webbie_context() if visible else None
        )
        self.update_webbie_context()

    def toggle_webbie_assistant(self):
        if self.webbie_dock.isVisible():
            self.webbie_dock.hide()
        else:
            self.update_webbie_context()
            self.webbie_dock.show()
            self.webbie_dock.raise_()
            self.webbie_assistant.entry.setFocus()

    def toggle_webbie_face(self):
        self.webbie_overlay.sleep(not self.webbie_overlay.face_sleeping)
        self.face_button.setText('Wake Webbie face' if self.webbie_overlay.face_sleeping else 'Sleep Webbie face')

    def show_author_review(self, passage):
        self.open_workspace('author')
        if self.webbie_assistant.pending:
            self.status.setText('Webbie is still answering. Review request was not sent.')
            return
        self.webbie_assistant.entry.setText(passage.replace('\\n', '  '))
        self.webbie_dock.show()
        self.webbie_dock.raise_()
        self.webbie_assistant.entry.setFocus()
        self.status.setText('Review request prepared for Webbie. Check the passage and press Send to share it.')

    def update_webbie_context(self):
        name = self.current_workspace
        label = WORKSPACES.get(name, 'The Web')
        summary = ''
        page = self.workspace_widgets.get(name)
        native = getattr(page, 'native', None) if page else None
        if native is not None and hasattr(native, 'webbie_context'):
            try:
                summary = str(native.webbie_context())[:600]
            except Exception:
                summary = ''
        self.webbie_assistant.set_workspace_context(
            label, mode=self.WEBBIE_MODES.get(name, 'Normal'), summary=summary
        )
        self.webbie_dock.setWindowTitle('WEBBIE | ' + label)

    def application_panel(self, workspace):
        panel = QWidget(); panel.setObjectName('panel'); layout = QVBoxLayout(panel)
        layout.addWidget(QLabel('Installed apps  /  ' + WORKSPACES[workspace]))
        apps = QListWidget(); apps.setMinimumWidth(230); apps.setMaximumWidth(340); apps.setIconSize(QSize(28, 28)); layout.addWidget(apps)
        apps.itemActivated.connect(lambda item: self.open_installed(item.data(Qt.UserRole)))
        self.app_lists[workspace] = apps; self.populate_app_list(workspace)
        layout.addWidget(button('Refresh installed apps', self.refresh_apps))
        folders = workspace_folders(workspace)
        if folders:
            layout.addWidget(QLabel('Workspace files'))
            locations = QComboBox()
            for title, location in folders:
                locations.addItem(title, str(location))
            layout.addWidget(locations)
            open_files = button('Open files in Dolphin', lambda checked=False, picker=locations: self.open_workspace_folder(picker.currentData(), workspace))
            open_files.setToolTip('Opens existing local files; never moves, replaces or uploads documents.')
            layout.addWidget(open_files)
        if workspace == 'media': layout.addWidget(button('Open Spider Media Center', self.launch_media))
        if workspace == 'system': layout.addWidget(button('System settings', self.open_settings))
        if workspace == 'dev-bay': layout.addWidget(button('Terminal', self.open_terminal))
        if workspace == 'recovery':
            for label, path in [('Guardian', 'system/bin/spider-guardian'), ('Vault', 'system/bin/spider-vault')]:
                if (SPIDER_ROOT / path).is_file(): layout.addWidget(button(label, lambda checked=False, p=path: self.launch([SPIDER_ROOT / p], workspace)))
        return panel

    def populate_app_list(self, workspace):
        apps = self.app_lists[workspace]; apps.clear()
        for app in self.installed_apps:
            if app.workspace == workspace:
                item = QListWidgetItem(QIcon.fromTheme(app.icon), app.name); item.setData(Qt.UserRole, app.desktop_id); item.setToolTip(app.comment); apps.addItem(item)
        if not apps.count():
            item = QListWidgetItem('No installed apps found.'); item.setToolTip('Refresh after installing an app in this workspace.'); item.setFlags(Qt.NoItemFlags); apps.addItem(item)

    def refresh_apps(self):
        self.installed_apps = discover_apps(desktops='TheWeb:KDE')
        for name in self.app_lists: self.populate_app_list(name)
        self.start_menu.populate(); self.status.setText(f'{len(self.installed_apps)} installed apps found.')

    def open_workspace(self, name):
        if name not in WORKSPACES: return
        if name not in self.workspace_widgets:
            page = QWidget(); page.setObjectName('root'); page.setProperty('workspace', name)
            layout = QHBoxLayout(page); layout.setContentsMargins(8, 8, 8, 8); layout.addWidget(self.application_panel(name))
            try:
                if name == 'webbie': native = WebbiePanel(SPIDER_ROOT)
                elif name == 'media': native = MediaPanel(self.launch_media)
                else: native = create_native(name, SPIDER_ROOT)
            except Exception as error:
                native = None; self.status.setText(f'Could not open {WORKSPACES[name]}: {error}')
            page.native = native
            if name == 'author' and native is not None and hasattr(native, 'show_webbie_review') is False:
                native.show_webbie_review = self.show_author_review
            if native:
                native.setParent(page); native.setWindowFlags(Qt.Widget)
                area = QScrollArea(); area.setWidgetResizable(True); area.setWidget(native); layout.addWidget(area, 1); native.show()
            else:
                if name in {'system', 'recovery'}:
                    surface = SystemPanel(SPIDER_ROOT, recovery=name == 'recovery'); page.native = surface
                else:
                    surface = QWidget(); surface.setObjectName('root'); body = QVBoxLayout(surface)
                    heading = QLabel(WORKSPACES[name]); heading.setFont(QFont('Sans Serif', 26, QFont.Bold)); body.addWidget(heading)
                    body.addWidget(QLabel('Open an installed app from this workspace.')); body.addStretch(1)
                layout.addWidget(surface, 1)
            self.workspace_widgets[name] = page; self.tabs.addTab(page, WORKSPACES[name])
        self.tabs.setCurrentWidget(self.workspace_widgets[name]); self.set_workspace(name); self.save_state()
        self.update_webbie_context()
        # Workspace navigation must never activate KDE Show Desktop, which hides
        # normal application windows, including Firefox and the file manager.
        self.raise_(); self.activateWindow()

    def open_workspace_folder(self, path, workspace):
        try:
            command = file_open_command(path)
            self.launch(command, workspace, 'Opened local workspace files.')
        except (FileNotFoundError, RuntimeError, OSError) as error:
            self.status.setText(str(error))

    def open_installed(self, ident):
        app = next((a for a in self.installed_apps if a.desktop_id == ident), None)
        if not app: return
        self.open_workspace(app.workspace)
        try: self.launch(launch_command(app), app.workspace, 'Opened ' + app.name + '.')
        except RuntimeError as error: self.status.setText(str(error))

    def can_close(self, page):
        native = getattr(page, 'native', None)
        worker = getattr(native, 'worker', None)
        if worker and worker.isRunning():
            self.status.setText('A workspace task is still running. Keep this tab open until it finishes.'); return False
        if hasattr(native, 'save_notes'):
            try: native.save_notes(quiet=True)
            except Exception as error:
                self.status.setText('Notes could not be saved: ' + str(error)); return False
        return native is None or native.close()

    def close_tab(self, index):
        page = self.tabs.widget(index)
        if page.property('workspace') == 'default' or not self.can_close(page): return
        name = page.property('workspace'); self.tabs.removeTab(index); self.workspace_widgets.pop(name); self.app_lists.pop(name, None); page.deleteLater(); self.save_state()

    def tab_changed(self, index):
        if index >= 0:
            self.set_workspace(self.tabs.widget(index).property('workspace')); self.save_state()

    def set_workspace(self, name):
        self.tabs.setProperty('home', name == 'default'); self.tabs.style().unpolish(self.tabs); self.tabs.style().polish(self.tabs)
        self.current_workspace = name; self.wallpaper = QPixmap(str(self.wallpaper_catalog.path(name))); self.background_surface.set_background(self.wallpaper)
        if hasattr(self, 'webbie_assistant'): self.update_webbie_context()
        for picker, ident in [(self.background_picker, name), (self.wallpaper_picker, self.wallpaper_catalog.selected_id(name))]:
            picker.blockSignals(True); picker.setCurrentIndex(max(0, picker.findData(ident))); picker.blockSignals(False)
        runtime = Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}')) / 'spider-os'
        try: runtime.mkdir(parents=True, exist_ok=True); (runtime / 'workspace').write_text(name)
        except OSError: pass

    def choose_wallpaper(self, index):
        try:
            self.wallpaper_catalog.select(self.current_workspace, self.wallpaper_picker.itemData(index)); self.set_workspace(self.current_workspace); self.status.setText('Wallpaper saved for this workspace.')
        except (OSError, ValueError) as error: self.status.setText('Could not save wallpaper: ' + str(error))

    def save_state(self):
        if getattr(self, '_restoring', False): return
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True); temporary = self.state_path.with_suffix('.tmp')
            temporary.write_text(json.dumps({'open': list(self.workspace_widgets), 'active': self.current_workspace})); temporary.replace(self.state_path)
        except OSError as error: self.status.setText('Could not save desktop state: ' + str(error))

    def restore_state(self):
        self._restoring = True
        try:
            data = json.loads(self.state_path.read_text())
            for name in data.get('open', []):
                if name in WORKSPACES and name != 'default': self.open_workspace(name)
            name = data.get('active', 'default')
            if name in self.workspace_widgets: self.open_workspace(name)
        except (OSError, ValueError, TypeError): pass
        finally: self._restoring = False

    def launch(self, command, workspace='default', message='Opened.'):
        self.set_workspace(workspace)
        try:
            subprocess.Popen([str(x) for x in command], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            # KWin already stacks normal application windows above the desktop.
            # Never race the application with a separate Show Desktop toggle.
            self.status.setText(message)
        except OSError as error: self.status.setText(str(error))

    def launch_media(self):
        try: self.launch(media_command(), 'media', 'Spider Media Center opened.')
        except AppUnavailable as error: self.status.setText(str(error))

    def open_media(self): self.open_workspace('media')
    def open_studio(self): self.open_workspace('studio')
    def open_author(self): self.open_workspace('author')
    def open_study(self): self.open_workspace('study')
    def open_webbie(self): self.toggle_webbie_assistant()

    def open_audio(self):
        self.open_workspace('system')
        panel = self.workspace_widgets['system'].native
        panel.tabs.setCurrentWidget(panel.audio_page)
    def open_forage(self): self.open_workspace('forage')
    def open_deep_forage(self): self.open_workspace('deep-forage')
    def open_kali(self): self.open_workspace('kali-bay')
    def open_terminal(self): self.launch(['konsole'], 'dev-bay', 'Terminal opened.')
    def open_settings(self): self.launch(['systemsettings'], 'system', 'System Settings opened.')
    def show_desktop(self): self.open_workspace('default')

    def lock_session(self):
        # Calls the secure KDE locker; the shell never receives passwords.
        try:
            result = subprocess.run(['dbus-send', '--session', '--print-reply', '--reply-timeout=3000', '--dest=org.freedesktop.ScreenSaver', '/ScreenSaver', 'org.freedesktop.ScreenSaver.Lock'], capture_output=True, text=True, timeout=4)
            self.status.setText('Session locked.' if result.returncode == 0 else 'Secure session locker is unavailable: ' + result.stderr.strip())
        except (OSError, subprocess.TimeoutExpired) as error: self.status.setText('Unable to lock: ' + str(error))

    def logout(self):
        if QMessageBox.question(self, 'Log out', 'Save your work and log out of The Web?', QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.close()

    def refresh_status(self):
        previous = getattr(self, 'status_worker', None)
        if previous and previous.isRunning(): return
        if previous: previous.deleteLater()
        self.status_worker = StatusWorker(SPIDER_ROOT, self, services_only=True)
        self.status_worker.result.connect(self.render_service_status)
        self.status_worker.failed.connect(lambda: self.service_status.setText('Service status unavailable.'))
        self.status_worker.start()

    def render_service_status(self, rows):
        self.service_status.setText('  ·  '.join(name + ': ' + state.upper() for name, unit, state, substate, startup in rows[:3]))

    def showEvent(self, event):
        super().showEvent(event)
        self.taskbar.show(); self.taskbar.position()
        if self.desktop_mode:
            geometry = QApplication.primaryScreen().geometry(); self.setGeometry(geometry.left(), geometry.top(), geometry.width(), geometry.height() - 56)
            x11_properties(self, 'DESKTOP'); self.lower()

    def closeEvent(self, event):
        assistant = getattr(self, 'webbie_assistant', None)
        if assistant is not None and assistant.worker and assistant.worker.isRunning():
            self.status.setText('Webbie is still replying. Wait before logging out.')
            event.ignore(); return
        # Save all editors before closing any of their stores.
        for page in self.workspace_widgets.values():
            native = getattr(page, 'native', None); worker = getattr(native, 'worker', None)
            if worker and worker.isRunning(): self.status.setText('A workspace task is still running.'); event.ignore(); return
            if hasattr(native, 'flush') and not native.flush(): event.ignore(); return
            if hasattr(native, 'save_notes'):
                try: native.save_notes(quiet=True)
                except Exception as error: self.status.setText('Notes could not be saved: ' + str(error)); event.ignore(); return
        self.save_state()
        for page in self.workspace_widgets.values():
            if not self.can_close(page): event.ignore(); return
        worker = getattr(self, 'status_worker', None)
        if worker and worker.isRunning(): worker.wait(3000)
        if worker and worker.isRunning(): event.ignore(); return
        self.timer.stop(); self.webbie_overlay.stop(); self.taskbar.timer.stop(); self.taskbar.close(); self.start_menu.close(); event.accept()


def main():
    app = QApplication(sys.argv); app.setApplicationName('The Web'); app.setQuitOnLastWindowClosed(True)
    splash = QSplashScreen(QPixmap(str(SPIDER_ROOT / 'branding/splash/spider-os-splash.png')).scaled(960, 540, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    splash.show(); splash.showMessage('Opening The Web…', Qt.AlignBottom | Qt.AlignHCenter, QColor('#e9d5ff')); app.processEvents()
    window = TheWeb(desktop_mode='--desktop-session' in sys.argv); window.showMaximized() if not window.desktop_mode else window.show()
    splash.finish(window); sys.exit(app.exec_())

if __name__ == '__main__': main()
