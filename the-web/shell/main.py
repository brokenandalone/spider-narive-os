#!/usr/bin/env python3
"""The Web desktop: native workspace tabs, installed applications and taskbar."""
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys

from PyQt5.QtCore import Qt, QTimer, QSize, QDateTime, QThread, pyqtSignal
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
# Only the separate X11 floating overlay draws Webbie on the desktop.
# The historical panel overlay remains for source compatibility tests.
sys.path.insert(0, str(SPIDER_ROOT / 'the-web/overlay'))
from webbie_face import (asleep as face_asleep, set_sleep as set_face_sleep,
                         full_screen_display, set_display_mode)
from media_panel import MediaPanel
from immersive_bays import ImmersiveBay, SCENES
from bay_mission_panel import BayMissionPanel
from app_catalog import VISIBLE_WORKSPACES
from workspace_max_native import NativeWorkspaceTools, WORKSPACE_TO_MAX
from volume_panel import VolumePanel
from quick_settings import QuickSettingsPanel
from window_overview import WindowOverview
from appearance import LIGHT_STYLE, appearance_file, load_theme, save_theme
from readability import load_menu_size, save_menu_size, readability_css
from navigation_core import INTERNAL_ACTIONS
from navigation_state import (navigation_file, load_navigation, save_navigation,
                              record_recent, toggle_favorite)
from desktop_state import read_desktop_state, write_desktop_state
from command_palette import CommandPalette
from notification_center import NotificationCenter
from notification_toast import NotificationToast
from tray_panel import TrayPanel

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


class AppCatalogWorker(QThread):
    """Scan user/system XDG launchers without blocking input or painting."""
    found = pyqtSignal(object)
    failed = pyqtSignal(str)

    def run(self):
        try:
            self.found.emit(discover_apps(desktops='TheWeb:KDE'))
        except (OSError, RuntimeError, ValueError) as error:
            self.failed.emit(str(error)[:160])


class WindowScanWorker(QThread):
    """Fetch wmctrl window titles without stalling the desktop taskbar."""
    found = pyqtSignal(object)

    def __init__(self, excluded, parent=None):
        super().__init__(parent)
        self.excluded = tuple(excluded)

    def run(self):
        try:
            self.found.emit(list_tasks(self.excluded))
        except (OSError, RuntimeError, ValueError):
            self.found.emit([])


class WallpaperWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._background = QPixmap()
        self.appearance = 'dark'

    def set_background(self, pixmap):
        self._background = pixmap
        self.update()

    def set_appearance(self, mode):
        self.appearance = mode
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        if not self._background.isNull() and self.width() and self.height():
            image = self._background.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            x = (image.width() - self.width()) // 2; y = (image.height() - self.height()) // 2
            painter.drawPixmap(0, 0, image, x, y, self.width(), self.height())
        else:
            painter.fillRect(self.rect(), QColor(8, 6, 11) if self.appearance == 'dark' else QColor(250, 245, 255))
        # The actual image file is never changed. Light mode needs a brighter
        # tint so dark labels remain visible over the same purple wallpaper.
        if self.appearance == 'light':
            painter.fillRect(self.rect(), QColor(253, 250, 255, 192))
        else:
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
        self.setObjectName('panel'); self.setStyleSheet(shell._appearance_style()); self.resize(580, 650)
        layout = QVBoxLayout(self)
        heading = QLabel('SPIDER OS  /  Start'); heading.setFont(QFont('Sans Serif', 22, QFont.Bold)); layout.addWidget(heading)
        self.search = QLineEdit(); self.search.setPlaceholderText('Find a workspace or installed app'); layout.addWidget(self.search)
        self.results = QListWidget(); self.results.setIconSize(QSize(28, 28)); layout.addWidget(self.results, 1)
        self.search.textChanged.connect(self.populate); self.results.itemActivated.connect(self.activate)
        self.search.returnPressed.connect(self.activate_first)
        self.search.setToolTip('Type a workspace or application name, then press Enter to open the first result.')
        actions = QHBoxLayout(); layout.addLayout(actions)
        actions.addWidget(button('Quick Launch', shell.toggle_command_palette))
        actions.addWidget(button('Refresh apps', shell.refresh_apps))
        actions.addWidget(button('Windows', shell.toggle_window_overview))
        actions.addWidget(button('Lock', shell.lock_session))
        actions.addWidget(button('Log out', shell.logout))
        self.populate()

    def populate(self):
        query = self.search.text().casefold(); self.results.clear()
        for workspace, label in VISIBLE_WORKSPACES.items():
            if workspace != 'default' and query in label.casefold():
                item = QListWidgetItem('Workspace  /  ' + label); item.setData(Qt.UserRole, ('workspace', workspace)); self.results.addItem(item)
        for app in self.shell.installed_apps:
            if query in (app.name + ' ' + app.comment + ' ' + WORKSPACES[app.workspace]).casefold():
                item = QListWidgetItem(QIcon.fromTheme(app.icon), app.name + '  /  ' + WORKSPACES[app.workspace])
                item.setData(Qt.UserRole, ('app', app.desktop_id)); self.results.addItem(item)
        if self.results.count():
            self.results.setCurrentRow(0)
        else:
            empty = QListWidgetItem('No matching workspaces or installed apps.')
            empty.setFlags(Qt.NoItemFlags)
            self.results.addItem(empty)

    def activate_first(self):
        item = self.results.currentItem()
        if item is not None and item.flags() & Qt.ItemIsEnabled:
            self.activate(item)

    def activate(self, item):
        kind, ident = item.data(Qt.UserRole); self.hide()
        if kind == 'workspace': self.shell.open_workspace(ident)
        else: self.shell.open_installed(ident)

    def show_menu(self, dock):
        if self.isVisible():
            self.hide(); return
        self.populate()
        bounds = dock.screen().availableGeometry()
        width = min(self.width(), max(320, bounds.width() - 16))
        height = min(self.height(), max(280, bounds.height() - 16))
        self.resize(width, height)
        xpos = min(max(dock.x(), bounds.left() + 8), bounds.right() - width - 8)
        ypos = min(max(dock.y() - height - 8, bounds.top() + 8), bounds.bottom() - height - 8)
        self.move(xpos, ypos)
        self.show(); self.raise_(); self.search.setFocus()


class Taskbar(QWidget):
    def __init__(self, shell):
        super().__init__(None, Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.shell = shell; self.setObjectName('panel'); self.setStyleSheet(shell._appearance_style())
        self.setWindowTitle('The Web Taskbar')
        layout = QHBoxLayout(self); layout.setContentsMargins(8, 4, 8, 4)
        self.start = button('Start', lambda: shell.start_menu.show_menu(self)); self.start.setIcon(QIcon(str(SPIDER_ROOT / 'branding/icons/spider-os-logo.png'))); layout.addWidget(self.start)
        layout.addWidget(button('The Web', shell.show_desktop))
        launch_button = button('Find', shell.toggle_command_palette)
        launch_button.setToolTip('Quick Launch: Ctrl+K when The Web has focus')
        layout.addWidget(launch_button)
        webbie = button('Webbie', shell.open_webbie); webbie.setIcon(QIcon(str(SPIDER_ROOT / 'branding/webbie/webbie-face-v1.png'))); layout.addWidget(webbie)
        self.tasks = QHBoxLayout(); layout.addLayout(self.tasks, 1)
        layout.addWidget(button('Quick', shell.toggle_quick_settings))
        layout.addWidget(button('Volume', shell.toggle_volume_panel))
        layout.addWidget(button('Alerts', shell.toggle_notifications))
        layout.addWidget(button('Tray', shell.toggle_tray))
        layout.addWidget(button('Audio', shell.open_audio))
        layout.addWidget(button('Lock', shell.lock_session))
        self.clock = QLabel(); self.clock.setMinimumWidth(155); layout.addWidget(self.clock)
        self.window_scan_worker = None
        self.timer = QTimer(self); self.timer.timeout.connect(self.refresh); self.timer.start(3000)
        self.last_tasks = None; self.refresh()

    def position(self):
        geometry = QApplication.primaryScreen().geometry()
        self.setGeometry(geometry.left(), geometry.bottom() - 55, geometry.width(), 56)
        if self.shell.desktop_mode: x11_properties(self, 'DOCK', QApplication.primaryScreen())

    def refresh(self):
        self.clock.setText(QDateTime.currentDateTime().toString('ddd d MMM  HH:mm'))
        if not self.shell.desktop_mode:
            self.render_tasks([])
            return
        if self.window_scan_worker is not None and self.window_scan_worker.isRunning():
            return
        excluded = {f'0x{int(self.winId()):08x}', f'0x{int(self.shell.winId()):08x}'}
        worker = WindowScanWorker(excluded, self)
        self.window_scan_worker = worker
        worker.found.connect(self.render_tasks)
        worker.finished.connect(self.window_scan_finished)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def window_scan_finished(self):
        self.window_scan_worker = None

    def render_tasks(self, tasks):
        screen_width = QApplication.primaryScreen().geometry().width()
        visible_count = max(0, min(5, (screen_width - 870) // 185))
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
        self.appearance_path = appearance_file()
        self.appearance = load_theme(self.appearance_path)
        self.menu_text_size = load_menu_size()
        self.navigation_path = navigation_file()
        self.navigation_state = load_navigation(self.navigation_path, WORKSPACES)
        self.installed_apps = []
        self.app_scan_worker = None
        self.setWindowTitle('The Web | Spider OS'); self.resize(1280, 820); self.setMinimumSize(900, 600); self.setStyleSheet(self._appearance_style())
        if desktop_mode: self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.build_ui(); self.background_surface.set_appearance(self.appearance); self.setup_webbie_assistant(); self.webbie_assistant.set_face_sleeping(face_asleep()); self.face_button.setText('Wake Webbie' if face_asleep() else 'Put Webbie to sleep'); self.start_menu = StartMenu(self); self.taskbar = Taskbar(self)
        self.start_menu.setStyleSheet(self._appearance_style())
        self.taskbar.setStyleSheet(self._appearance_style())
        self.command_palette = CommandPalette(self)
        self.launch_webbie_floating_face()
        self.notifications_process = self.start_notification_bridge()
        self.notification_toast = NotificationToast(self) if self.desktop_mode else None
        self._shortcut = QShortcut(QKeySequence('Ctrl+Esc'), self); self._shortcut.activated.connect(lambda: self.start_menu.show_menu(self.taskbar))
        self._close_shortcut = QShortcut(QKeySequence('Ctrl+W'), self); self._close_shortcut.activated.connect(lambda: self.close_tab(self.tabs.currentIndex()))
        self._palette_shortcut = QShortcut(QKeySequence('Ctrl+K'), self)
        self._palette_shortcut.activated.connect(self.toggle_command_palette)
        self._pinned_shortcuts = []
        for number in range(1, 9):
            shortcut = QShortcut(QKeySequence(f'Ctrl+Alt+{number}'), self)
            shortcut.activated.connect(
                lambda slot=number - 1: self.open_pinned_slot(slot))
            self._pinned_shortcuts.append(shortcut)
        self.tabs.currentChanged.connect(self.tab_changed); self.tabs.tabCloseRequested.connect(self.close_tab)
        self.set_workspace('default')
        if restore: self.restore_state()
        self.timer = QTimer(self); self.timer.timeout.connect(self.refresh_status); self.timer.start(15000)
        QTimer.singleShot(0, self.refresh_status)
        QTimer.singleShot(0, self.refresh_apps)

    def build_ui(self):
        root = WallpaperWidget(); root.setObjectName('root'); self.background_surface = root; self.setCentralWidget(root)
        outer = QVBoxLayout(root); outer.setContentsMargins(20, 16, 20, 12)
        header = QHBoxLayout(); outer.addLayout(header)
        logo = QLabel(); logo.setPixmap(QPixmap(str(SPIDER_ROOT / 'branding/icons/spider-os-logo.png')).scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)); header.addWidget(logo)
        self.brand_title = QLabel('THE WEB')
        self.brand_title.setStyleSheet(self._brand_style())
        header.addWidget(self.brand_title)
        header.addWidget(QLabel('YOUR LIFE. ONE WEB.'), 1)
        header.addWidget(button('Ask Webbie', self.toggle_webbie_assistant))
        self.face_button = button('Put Webbie to sleep', self.toggle_webbie_face)
        header.addWidget(self.face_button)
        self.face_display_button = button(
            'Webbie: Compact' if full_screen_display() else 'Webbie: Full Screen',
            self.toggle_webbie_display)
        header.addWidget(self.face_display_button)
        header.addWidget(button('Workspaces', lambda: self.start_menu.show_menu(self.taskbar)))
        header.addWidget(button('Quick Launch', self.toggle_command_palette))
        self.tabs = QTabWidget(); self.tabs.setObjectName('workspaceTabs'); self.tabs.setProperty('home', True); self.tabs.setTabsClosable(True); self.tabs.setMovable(True); outer.addWidget(self.tabs, 1)
        home = QWidget(); home.setObjectName('root'); home_layout = QVBoxLayout(home)
        welcome = QLabel('Your workspaces'); welcome.setFont(QFont('Sans Serif', 22, QFont.Bold)); home_layout.addWidget(welcome)
        self.pinned_title = QLabel('Pinned workspaces  ·  customize in Quick Launch')
        self.pinned_title.setAccessibleName('Pinned Spider OS workspaces')
        home_layout.addWidget(self.pinned_title)
        self.pinned_row = QGridLayout()
        home_layout.addLayout(self.pinned_row)
        self.render_pinned_workspaces()
        self.recent_title = QLabel('Recent workspaces and applications')
        home_layout.addWidget(self.recent_title)
        self.recent_grid = QGridLayout()
        home_layout.addLayout(self.recent_grid)
        self.render_recent_shortcuts()
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.viewport().setAutoFillBackground(False); home_layout.addWidget(scroll, 1)
        home_actions = button('The Web: advanced tools & tasks', self.toggle_home_tools)
        home_layout.addWidget(home_actions)
        self.home_max_tools = NativeWorkspaceTools('default', home)
        self.home_max_tools.setVisible(False)
        home_layout.addWidget(self.home_max_tools, 1)
        content = QWidget(); content.setObjectName('root'); scroll.setWidget(content); grid = QGridLayout(content); grid.setAlignment(Qt.AlignTop | Qt.AlignLeft); grid.setHorizontalSpacing(14); grid.setVerticalSpacing(14)
        for index, (workspace, label) in enumerate((k, v) for k, v in VISIBLE_WORKSPACES.items() if k != 'default'):
            shortcut = button(label, lambda checked=False, name=workspace: self.open_workspace(name)); shortcut.setFixedWidth(175)
            grid.addWidget(shortcut, index // 4, index % 4)
        home.setProperty('workspace', 'default'); self.tabs.addTab(home, 'The Web'); self.workspace_widgets['default'] = home
        self.tabs.tabBar().setTabButton(0, self.tabs.tabBar().RightSide, None)
        self._restoring_home_tab = False
        self.tabs.tabBar().tabMoved.connect(self.tab_moved)
        wallpaper_row = QHBoxLayout(); outer.addLayout(wallpaper_row)
        self.background_picker = QComboBox()
        for name, label in VISIBLE_WORKSPACES.items(): self.background_picker.addItem(label, name)
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
        # Owner-clicked workflow steps can navigate only registered workspaces.
        self.webbie_assistant.workspace_navigator = self.open_workspace
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

    def start_notification_bridge(self):
        if not self.desktop_mode:
            return None
        script=SPIDER_ROOT/'the-web/shell/notification_bridge.py'
        if not script.is_file(): return None
        try:
            return subprocess.Popen([sys.executable,str(script)],
                stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL)
        except OSError:
            return None

    def launch_webbie_floating_face(self):
        # At most one instance. The overlay uses a per-user X11 file lock.
        if os.environ.get('XDG_SESSION_TYPE', '').lower() != 'x11':
            return
        portrait = SPIDER_ROOT / 'the-web/overlay/webbie_face.py'
        if not portrait.is_file():
            return
        try:
            subprocess.Popen([sys.executable, str(portrait)],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, start_new_session=True)
        except OSError:
            pass  # Desktop and voice still work if the optional portrait fails.

    def toggle_webbie_face(self):
        next_mode = 'wake' if face_asleep() else 'sleep'
        try:
            set_face_sleep(next_mode)
        except OSError as error:
            self.status.setText('Cannot change Webbie sleep mode: ' + str(error))
            return
        self.webbie_assistant.set_face_sleeping(face_asleep())
        self.face_button.setText('Wake Webbie' if face_asleep() else 'Put Webbie to sleep')

    def toggle_webbie_display(self):
        try:
            active = set_display_mode('toggle-display')
        except OSError as error:
            self.status.setText('Unable to change Webbie face display: ' + str(error))
            return
        self.face_display_button.setText(
            'Webbie: Compact' if active else 'Webbie: Full Screen')
        self.status.setText(
            'Webbie full-screen face is click-through.' if active
            else 'Webbie face returned to compact mode.')

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
        # Give Webbie the currently OPEN workspace names, not document
        # contents, titles from other windows, or privileged screen data.
        open_names = [
            WORKSPACES.get(self.tabs.widget(index).property('workspace'), 'Workspace')
            for index in range(self.tabs.count())
            if self.tabs.widget(index) is not None
        ]
        tabs_context = 'Open workspace tabs: ' + ', '.join(open_names)
        summary = tabs_context + ('. Selected: ' + summary if summary else '')
        self.webbie_assistant.set_workspace_context(
            label, mode=self.WEBBIE_MODES.get(name, 'Normal'), summary=summary[:600]
        )
        self.webbie_dock.setWindowTitle('WEBBIE | ' + label)

    def application_panel(self, workspace):
        panel = QWidget(); panel.setObjectName('panel'); layout = QVBoxLayout(panel)
        help_label = QLabel('Optional installed programs for ' + WORKSPACES[workspace] + '.\nYour native bay works without adding a desktop launcher. Select a program only when its specialized tools are needed.')
        help_label.setWordWrap(True); layout.addWidget(help_label)
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
        """Discover potentially hundreds of XDG files off the UI thread."""
        if self.app_scan_worker is not None and self.app_scan_worker.isRunning():
            self.status.setText('Application discovery is already running.')
            return
        self.status.setText('Finding installed applications in the background…')
        worker = AppCatalogWorker(self)
        self.app_scan_worker = worker
        worker.found.connect(self.apps_discovered)
        worker.failed.connect(lambda detail: self.status.setText(
            'Application discovery failed: ' + detail))
        worker.finished.connect(self.app_scan_finished)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def apps_discovered(self, applications):
        self.installed_apps = applications
        for name in list(self.app_lists):
            self.populate_app_list(name)
        self.start_menu.populate()
        self.command_palette.refresh()
        self.render_recent_shortcuts()
        self.status.setText(f'{len(applications)} installed applications found.')

    def app_scan_finished(self):
        self.app_scan_worker = None

    def visible_launcher_windows(self):
        """Read-only snapshot of user-visible window IDs; no arbitrary targets."""
        try:
            tasks = list_tasks()
        except (OSError, RuntimeError, ValueError):
            return []
        return [
            task for task in tasks[:100]
            if re.fullmatch(r'0x[0-9a-fA-F]{1,16}', str(getattr(task, 'ident', '')))
            and int(task.ident, 16) != 0
            and str(getattr(task, 'title', '')).strip()
        ]

    def activate_launcher_window(self, ident):
        """Switch only to a window verified in a fresh X11 task snapshot."""
        if not isinstance(ident, str) or not re.fullmatch(r'0x[0-9a-fA-F]{1,16}', ident):
            return False
        available = {task.ident for task in self.visible_launcher_windows()}
        if ident not in available:
            return False
        wm_command('-i', '-a', ident)
        return True

    def workspaces_for_navigation(self):
        return VISIBLE_WORKSPACES

    def render_pinned_workspaces(self):
        """Keep quick access predictable without changing existing tabs."""
        row = getattr(self, 'pinned_row', None)
        if row is None:
            return
        while row.count():
            item = row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        shown = 0
        for kind, ident in self.navigation_state.get('favorites', []):
            if kind != 'workspace' or ident not in WORKSPACES:
                continue
            shortcut = button('★ ' + WORKSPACES[ident],
                              lambda checked=False, name=ident: self.open_workspace(name))
            shortcut.setAccessibleName('Pinned workspace ' + WORKSPACES[ident])
            shortcut.setToolTip('Ctrl+Alt+' + str(shown + 1) +
                                ' while The Web is focused, or click to open.')
            shortcut.setToolTip('Pinned workspace · use Quick Launch to unpin')
            row.addWidget(shortcut, shown // 4, shown % 4)
            shown += 1
            if shown >= 8:
                break
        if not shown:
            row.addWidget(QLabel('No pinned workspaces. Ctrl+K opens Quick Launch.'), 0, 0)

    def render_recent_shortcuts(self):
        grid = getattr(self, 'recent_grid', None)
        if grid is None:
            return
        while grid.count():
            item = grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        added = 0
        for kind, ident in self.navigation_state.get('recent', []):
            if kind == 'workspace' and ident in WORKSPACES:
                label = WORKSPACES[ident]
                callback = lambda checked=False, name=ident: self.open_workspace(name)
            elif kind == 'app':
                app = next((a for a in self.installed_apps if a.desktop_id == ident), None)
                if app is None:
                    continue
                label = app.name
                callback = lambda checked=False, name=ident: self.open_installed(name)
            else:
                continue
            shortcut = button(label, callback)
            shortcut.setToolTip(('App' if kind == 'app' else 'Workspace') + ' · ' + label)
            grid.addWidget(shortcut, added // 4, added % 4)
            added += 1
            if added >= 8:
                break
        if not added:
            grid.addWidget(QLabel('Open a workspace to build your recent list.'), 0, 0)

    def open_pinned_slot(self, slot):
        pinned = [ident for kind, ident in self.navigation_state.get('favorites', [])
                  if kind == 'workspace' and ident in WORKSPACES]
        if 0 <= slot < min(len(pinned), 8):
            self.open_workspace(pinned[slot])

    def toggle_navigation_pin(self, kind, ident):
        if not toggle_favorite(self.navigation_state, kind, ident, WORKSPACES):
            self.status.setText('Pin unavailable. You may have reached the 24-item limit.')
            return
        try:
            save_navigation(self.navigation_path, self.navigation_state, WORKSPACES)
        except OSError as error:
            self.status.setText('Could not save pinned items: ' + str(error))
        self.render_pinned_workspaces()

    def remember_navigation(self, kind, ident):
        if getattr(self, '_restoring', False):
            return
        if record_recent(self.navigation_state, kind, ident, WORKSPACES):
            self.render_recent_shortcuts()
            try:
                save_navigation(self.navigation_path, self.navigation_state, WORKSPACES)
            except OSError:
                # A read-only home should not prevent app and workspace launches.
                pass

    def clear_recent_navigation(self):
        """Owner-requested clearing of launcher history only.

        Favorites and installed apps remain untouched.  A settings write
        failure is reported instead of claiming the list was persisted.
        """
        self.navigation_state['recent'] = []
        self.render_recent_shortcuts()
        try:
            save_navigation(self.navigation_path, self.navigation_state, WORKSPACES)
        except OSError as error:
            self.status.setText('Recent launcher history not saved: ' + str(error))
            return False
        return True

    def toggle_command_palette(self):
        self.command_palette.show_palette()

    def execute_palette_action(self, ident):
        """Only explicitly registered desktop actions can be dispatched."""
        actions = {
            'windows': self.toggle_window_overview,
            'webbie': self.toggle_webbie_assistant,
            'quick-settings': self.toggle_quick_settings,
            'notifications': self.toggle_notifications,
            'tray': self.toggle_tray,
            'refresh-apps': self.refresh_apps,
            'desktop': self.show_desktop,
            'system-settings': self.open_settings,
            'lock': self.lock_session,
        }
        action = actions.get(ident)
        if action is not None and ident in {key for key, _, _ in INTERNAL_ACTIONS}:
            action()

    def toggle_home_tools(self):
        shown = not self.home_max_tools.isVisible()
        self.home_max_tools.setVisible(shown)
        if shown:
            self.home_max_tools.reload()

    def open_workspace(self, name):
        if name not in WORKSPACES: return
        if name not in self.workspace_widgets:
            page = QWidget(); page.setObjectName('root'); page.setProperty('workspace', name)
            layout = QVBoxLayout(page); layout.setContentsMargins(8, 8, 8, 8)
            if name in SCENES:
                layout.addWidget(ImmersiveBay(name, page))
            bay_row = QHBoxLayout(); layout.addLayout(bay_row, 1)
            workspace_tabs = QTabWidget(page)
            workspace_tabs.setObjectName('nativeBayToolsTabs')
            workspace_tabs.setDocumentMode(True)
            bay_row.addWidget(workspace_tabs, 1)
            try:
                if name == 'webbie': native = WebbiePanel(SPIDER_ROOT)
                elif name == 'media': native = MediaPanel(self.launch_media)
                else: native = create_native(name, SPIDER_ROOT)
            except Exception as error:
                native = None; page.native_error = str(error); self.status.setText(f'Could not open {WORKSPACES[name]}: {error}')
            page.native = native
            if name == 'author' and native is not None and hasattr(native, 'show_webbie_review') is False:
                native.show_webbie_review = self.show_author_review
            if native:
                native.setParent(page); native.setWindowFlags(Qt.Widget)
                area = QScrollArea(); area.setWidgetResizable(True); area.setWidget(native)
                if workspace_tabs is not None:
                    workspace_tabs.addTab(area, 'Native workspace')
                else:
                    bay_row.addWidget(area, 1)
                native.show()
            else:
                if name in {'system', 'recovery'}:
                    surface = SystemPanel(SPIDER_ROOT, recovery=name == 'recovery'); page.native = surface
                else:
                    surface = QWidget(); surface.setObjectName('root'); body = QVBoxLayout(surface)
                    heading = QLabel(WORKSPACES[name]); heading.setFont(QFont('Sans Serif', 26, QFont.Bold)); body.addWidget(heading)
                    body.addWidget(QLabel('This bay has its own projects and operations below.\nExternal applications are optional tools, not the bay itself.')); body.addStretch(1)
                if workspace_tabs is not None:
                    workspace_tabs.addTab(surface, 'Native workspace')
                else:
                    bay_row.addWidget(surface, 1)
            mission_desk = BayMissionPanel(name, workspace_tabs)
            page.mission_desk = mission_desk
            workspace_tabs.addTab(mission_desk, 'Projects & missions')
            if name in WORKSPACE_TO_MAX:
                advanced = NativeWorkspaceTools(name, workspace_tabs)
                page.advanced_tools = advanced
                workspace_tabs.addTab(advanced, 'Advanced tools & tasks')
                page.extra_max_tools = []
                if name == 'media':
                    extra = NativeWorkspaceTools('bcn-nova', workspace_tabs)
                    page.extra_max_tools.append(extra)
                    workspace_tabs.addTab(extra, 'BCN / Nova radio tools')
                elif name == 'system':
                    extra = NativeWorkspaceTools('backups', workspace_tabs)
                    page.extra_max_tools.append(extra)
                    workspace_tabs.addTab(extra, 'Backup & integrity tools')
            if name == 'system':
                recovery_panel = SystemPanel(SPIDER_ROOT, recovery=True)
                workspace_tabs.addTab(recovery_panel, 'Recovery & backups')
            workspace_tabs.addTab(self.application_panel(name), 'Optional installed tools')
            self.workspace_widgets[name] = page; self.tabs.addTab(page, WORKSPACES[name])
        self.tabs.setCurrentWidget(self.workspace_widgets[name]); self.set_workspace(name); self.save_state()
        if name != 'default':
            self.remember_navigation('workspace', name)
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
        try:
            self.launch(launch_command(app), app.workspace, 'Opened ' + app.name + '.')
            self.remember_navigation('app', app.desktop_id)
        except RuntimeError as error: self.status.setText(str(error))

    def can_close(self, page):
        native = getattr(page, 'native', None)
        live_tools = [getattr(page, 'advanced_tools', None)] + list(
            getattr(page, 'extra_max_tools', ()))
        live_tools.append(getattr(native, 'native_max_tools', None))
        for tool in live_tools:
            worker = getattr(tool, 'worker', None)
            if worker and worker.isRunning():
                self.status.setText('Finish workspace analysis before closing this bay.')
                return False
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
        if page is None:
            return
        if page.property('workspace') == 'default' or not self.can_close(page): return
        name = page.property('workspace'); self.tabs.removeTab(index); self.workspace_widgets.pop(name); self.app_lists.pop(name, None); page.deleteLater(); self.save_state()

    def tab_moved(self, old_index, new_index):
        """Allow workspace rearrangement, but always pin The Web home at zero."""
        if self._restoring_home_tab:
            return
        home = self.workspace_widgets.get('default')
        if home is None:
            return
        home_index = self.tabs.indexOf(home)
        if home_index > 0:
            self._restoring_home_tab = True
            try:
                # Let QTabWidget receive both Qt tabMoved signals so the tab
                # bar and stacked widgets remain in the same order.
                self.tabs.tabBar().moveTab(home_index, 0)
            finally:
                self._restoring_home_tab = False
        self.save_state()

    def cycle_tab(self, direction):
        """Cycle through displayed workspace tabs without changing their order."""
        count = self.tabs.count()
        if count and direction in (-1, 1):
            self.tabs.setCurrentIndex((self.tabs.currentIndex() + direction) % count)

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
        if getattr(self, '_restoring', False):
            return
        try:
            write_desktop_state(self.state_path, {
                'open': [self.tabs.widget(i).property('workspace')
                         for i in range(self.tabs.count())],
                'active': self.current_workspace,
            }, WORKSPACES)
        except OSError as error:
            self.status.setText('Could not save desktop state: ' + str(error))

    def restore_state(self):
        self._restoring = True
        try:
            data = read_desktop_state(self.state_path, WORKSPACES)
            for name in data['open']:
                if name != 'default':
                    self.open_workspace(name)
            name = data['active']
            if name in self.workspace_widgets:
                self.open_workspace(name)
        finally:
            self._restoring = False

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

    def toggle_tray(self):
        panel=getattr(self,'tray_panel',None)
        if panel is None:
            panel=TrayPanel(self)
            self.tray_panel=panel
        if panel.isVisible(): panel.hide()
        else:
            panel.refresh()
            panel.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
            panel.resize(350,300)
            panel.show()
            panel.raise_()

    def toggle_notifications(self):
        panel = getattr(self, 'notification_center', None)
        if panel is None:
            panel = NotificationCenter(self)
            self.notification_center = panel
        if panel.isVisible():
            panel.hide()
        else:
            panel.refresh()
            panel.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
            panel.resize(470, 360)
            panel.show()
            panel.raise_()

    def _appearance_style(self):
        base = LIGHT_STYLE if self.appearance == 'light' else STYLE
        return base + readability_css(self.appearance, self.menu_text_size)

    def _refresh_chrome_style(self):
        # Qt menus and combo drop-downs may live in their own popup windows.
        # Restyle The Web's windows explicitly, not KDE or GTK applications.
        sheet = self._appearance_style()
        self.setStyleSheet(sheet)
        self.start_menu.setStyleSheet(sheet)
        self.taskbar.setStyleSheet(sheet)
        for panel_name in ('command_palette', 'quick_settings_panel', 'window_overview',
                           'notification_center', 'tray_panel', 'quick_volume'):
            panel = getattr(self, panel_name, None)
            if panel is not None:
                panel.setStyleSheet(sheet)

    def choose_menu_text_size(self, size):
        if size == self.menu_text_size:
            return
        save_menu_size(size)
        self.menu_text_size = size
        self._refresh_chrome_style()
        self.status.setText('Menu text set to ' + size.replace('-', ' ') +
                            '. The setting will remain after sign-in.')

    def _brand_style(self):
        color = '#4c1674' if self.appearance == 'light' else '#e9d5ff'
        return 'font-size:26px; font-weight:bold; color:' + color + '; letter-spacing:2px;'

    def choose_appearance(self, theme):
        # This preference deliberately changes The Web, not KDE/GTK themes.
        # Never modify the preferred purple wallpapers or other applications.
        if theme not in ('dark', 'light'):
            raise ValueError('Invalid Spider OS appearance')
        if theme == self.appearance:
            return
        save_theme(theme, self.appearance_path)
        self.appearance = theme
        self._refresh_chrome_style()
        self.brand_title.setStyleSheet(self._brand_style())
        self.background_surface.set_appearance(theme)
        self.status.setText('The Web appearance: ' + theme + '. KDE/GTK applications unchanged.')

    def toggle_window_overview(self):
        panel=getattr(self,'window_overview',None)
        if panel is None:
            def ignored_windows():
                return (
                    f'0x{int(self.winId()):08x}',
                    f'0x{int(self.taskbar.winId()):08x}',
                )
            self.window_overview=WindowOverview(self,excluded=ignored_windows)
            panel=self.window_overview
        if panel.isVisible():
            panel.hide()
        else:
            panel.refresh()
            panel.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
            panel.resize(590,380)
            panel.show()
            panel.raise_()

    def toggle_quick_settings(self):
        panel=getattr(self, 'quick_settings_panel', None)
        if panel is None:
            self.quick_settings_panel=QuickSettingsPanel(
                self, appearance_reader=lambda: self.appearance,
                appearance_writer=self.choose_appearance,
                menu_size_reader=lambda: self.menu_text_size,
                menu_size_writer=self.choose_menu_text_size)
            panel=self.quick_settings_panel
        if panel.isVisible():
            panel.hide()
        else:
            panel.refresh()
            panel.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
            panel.resize(410,320)
            panel.show()
            panel.raise_()

    def toggle_volume_panel(self):
        panel = getattr(self, 'quick_volume', None)
        if panel is None:
            self.quick_volume = VolumePanel(self)
            panel = self.quick_volume
        if panel.isVisible():
            panel.hide()
        else:
            panel.refresh()
            panel.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
            panel.show()
            panel.raise_()

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
        task_worker = getattr(self.taskbar, 'window_scan_worker', None)
        app_worker = getattr(self, 'app_scan_worker', None)
        if (task_worker is not None and task_worker.isRunning()) or (
                app_worker is not None and app_worker.isRunning()):
            self.status.setText('A desktop refresh is still finishing. Close again afterward.')
            event.ignore()
            return
        assistant = getattr(self, 'webbie_assistant', None)
        if assistant is not None and ((assistant.worker and assistant.worker.isRunning()) or
                                      (assistant.camera_worker and assistant.camera_worker.isRunning()) or
                                      assistant.face_controls.active()):
            self.status.setText('Webbie is still finishing a request. Wait before logging out.')
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
        self.timer.stop()
        bridge=getattr(self,'notifications_process',None)
        if bridge is not None and bridge.poll() is None:
            bridge.terminate()
        if self.notification_toast is not None: self.notification_toast.close()
        self.taskbar.timer.stop()
        self.command_palette.close()
        self.taskbar.close()
        self.start_menu.close()
        event.accept()


def main():
    app = QApplication(sys.argv); app.setApplicationName('The Web'); app.setQuitOnLastWindowClosed(True)
    splash = QSplashScreen(QPixmap(str(SPIDER_ROOT / 'branding/splash/spider-os-splash.png')).scaled(960, 540, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    splash.show(); splash.showMessage('Opening The Web…', Qt.AlignBottom | Qt.AlignHCenter, QColor('#e9d5ff')); app.processEvents()
    window = TheWeb(desktop_mode='--desktop-session' in sys.argv); window.showMaximized() if not window.desktop_mode else window.show()
    splash.finish(window); sys.exit(app.exec_())

if __name__ == '__main__': main()
