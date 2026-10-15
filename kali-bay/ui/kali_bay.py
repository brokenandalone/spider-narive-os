#!/usr/bin/env python3

import os
import subprocess
import sys
import socket
import stat
from pathlib import Path

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPixmap,
    QKeySequence,
)
from PyQt5.QtWidgets import (
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QDockWidget,
    QPlainTextEdit,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QComboBox,
    QCheckBox,
    QFileDialog,
    QInputDialog,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QShortcut,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


SPIDER_ROOT = Path(
    "/usr/local/lib/spider-os"
)

if not SPIDER_ROOT.exists():
    SPIDER_ROOT = (
        Path(__file__)
        .resolve()
        .parents[2]
    )


# Local storage is intentionally isolated from the Kali Distrobox.
# It is only written by explicit favorite, create-lab or save-notes clicks.
sys.path.insert(0, str(SPIDER_ROOT / "kali-bay" / "runtime"))
import workspace_store as kali_store
import lab_reports as kali_reports
import evidence_fingerprint as kali_evidence
import evidence_ledger as kali_ledger


MANAGER = (
    SPIDER_ROOT
    / "kali-bay"
    / "bin"
    / "kali-bay"
)


WALLPAPER = (
    SPIDER_ROOT
    / "branding"
    / "workspaces"
    / "kali-bay.png"
)


OFFENSIVE_CATEGORIES = [
    (
        "INFORMATION GATHERING",
        "OSINT, discovery, enumeration",
        "kali-tools-information-gathering",
    ),
    (
        "VULNERABILITY ANALYSIS",
        "Assessment and vulnerability tools",
        "kali-tools-vulnerability",
    ),
    (
        "WEB APPLICATIONS",
        "Web assessment toolset",
        "kali-tools-web",
    ),
    (
        "PASSWORDS",
        "Password auditing and recovery",
        "kali-tools-passwords",
    ),
    (
        "WIRELESS",
        "802.11, Bluetooth, RFID and SDR",
        "kali-tools-wireless",
    ),
    (
        "EXPLOITATION",
        "Exploitation framework tools",
        "kali-tools-exploitation",
    ),
    (
        "SNIFFING & SPOOFING",
        "Traffic inspection and protocol tools",
        "kali-tools-sniffing-spoofing",
    ),
    (
        "POST EXPLOITATION",
        "Post-exploitation tool group",
        "kali-tools-post-exploitation",
    ),
    (
        "FORENSICS",
        "Digital forensics and recovery",
        "kali-tools-forensics",
    ),
    (
        "REVERSE ENGINEERING",
        "Binary analysis and reversing",
        "kali-tools-reverse-engineering",
    ),
    (
        "REPORTING",
        "Assessment reporting tools",
        "kali-tools-reporting",
    ),
    (
        "SOCIAL ENGINEERING",
        "Social-engineering assessment tools",
        "kali-tools-social-engineering",
    ),
]

PURPLE_CATEGORIES = [
    (
        "IDENTIFY",
        "Inventory, visibility and risk discovery",
        "kali-tools-identify",
    ),
    (
        "PROTECT",
        "Hardening and preventative controls",
        "kali-tools-protect",
    ),
    (
        "DETECT",
        "Threat monitoring and detection tools",
        "kali-tools-detect",
    ),
    (
        "RESPOND",
        "Incident investigation and containment",
        "kali-tools-respond",
    ),
    (
        "RECOVER",
        "Recovery and digital evidence workflows",
        "kali-tools-recover",
    ),
]


# Native Spider OS launcher labels mapped only to the already-audited Kali
# manager's hardcoded tool IDs. No shell input, targets or scans.
DESKTOP_TOOL_MENU = (
    ("Network", "Wireshark", "wireshark"),
    ("Network", "Nmap workbench", "nmap"),
    ("Web Security", "Burp Suite", "burpsuite"),
    ("Web Security", "OWASP ZAP", "zaproxy"),
    ("Reverse Engineering", "Ghidra", "ghidra"),
    ("Assessment", "Metasploit workbench", "msfconsole"),
    ("Detection", "Suricata workbench", "suricata"),
    ("Detection", "YARA workbench", "yara"),
    ("Hardening", "Lynis workbench", "lynis"),
    ("Malware Checks", "ClamTK", "clamtk"),
)

class WallpaperSurface(QWidget):
    """Paint the workspace artwork on the content surface itself.

    QMainWindow palette wallpapers disappear beneath the central QWidget.
    Keep the image untouched and paint it behind the dashboard widgets.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._image = QPixmap()
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)

    def set_wallpaper(self, image):
        self._image = image if image is not None else QPixmap()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        if not self._image.isNull():
            scaled = self._image.scaled(
                self.size(),
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation,
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
            # Gentle scrim keeps controls legible without burying the image.
            painter.fillRect(self.rect(), QColor(7, 5, 10, 75))
        else:
            painter.fillRect(self.rect(), QColor(7, 5, 10))
        painter.end()


class KaliWebbieReplyWorker(QThread):
    """Send typed Kali Bay questions to the EXISTING Webbie resident socket."""

    received = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, message, sock_path, parent=None):
        super().__init__(parent)
        self.message = message
        self.sock_path = Path(sock_path)

    def run(self):
        try:
            entry = self.sock_path.stat()
            if not stat.S_ISSOCK(entry.st_mode) or entry.st_uid != os.getuid():
                self.failed.emit("Webbie's private session socket is unavailable.")
                return
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.settimeout(110)
                client.connect(str(self.sock_path))
                client.sendall(self.message.encode("utf-8"))
                output = []
                size = 0
                while True:
                    part = client.recv(16384)
                    if not part:
                        break
                    size += len(part)
                    if size > 262144:
                        raise ValueError("Webbie response was too large.")
                    output.append(part)
            answer = b"".join(output).decode("utf-8", errors="replace").strip()
            if not answer:
                raise ValueError("Webbie did not send a reply.")
            self.received.emit(answer)
        except (OSError, ValueError) as error:
            self.failed.emit("Webbie connection: " + str(error))


class KaliCatalogWorker(QThread):
    """Read only the real Kali app catalog without freezing the main UI."""
    loaded = pyqtSignal(str)
    failed = pyqtSignal(str)

    def run(self):
        try:
            result = subprocess.run(
                [str(MANAGER), "apps-json"], text=True,
                capture_output=True, check=False, timeout=24,
            )
            if result.returncode:
                self.failed.emit(
                    (result.stderr or result.stdout).strip()[:220]
                    or "Kali catalog is unavailable."
                )
                return
            self.loaded.emit(result.stdout)
        except (OSError, subprocess.TimeoutExpired) as error:
            self.failed.emit(str(error)[:220])


class KaliEvidenceWorker(QThread):
    """Hash an explicitly selected file off the GUI thread; no file changes."""

    ready = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = path

    def run(self):
        try:
            self.ready.emit(kali_evidence.fingerprint(self.path))
        except (kali_evidence.EvidenceError, OSError) as error:
            self.failed.emit(str(error))


# The read-only MAX tools are embedded in the original Kali Bay window.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'the-web' / 'shell'))
from workspace_max_native import NativeWorkspaceTools

class KaliBayWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self._wallpaper = None
        try:
            self.favorites = kali_store.get_favorites()
            self.favorites_error = ""
        except kali_store.StorageError as error:
            self.favorites = set()
            self.favorites_error = str(error)
        self.active_lab = None
        self._switching_labs = False
        self.catalog_worker = None
        self.evidence_worker = None
        self.evidence_result = None
        self.evidence_lab_id = None

        self.setWindowTitle(
            "Kali Bay | Spider OS"
        )

        self.resize(
            1180,
            820,
        )

        self.setMinimumSize(
            900,
            650,
        )

        self.build_ui()
        self.build_webbie_dock()
        self.load_wallpaper()
        self.refresh_status()
        if "--purple" in sys.argv[1:]:
            self.security_tabs.setCurrentIndex(2)
        elif "--offensive" in sys.argv[1:]:
            self.security_tabs.setCurrentIndex(1)

    def build_ui(self):
        self.setStyleSheet(
            """
            QWidget {
                font-size: 15px;
            }
            QLineEdit, QComboBox, QPlainTextEdit {
                color: #ffffff;
                background: #160d27;
                selection-color: #ffffff;
                selection-background-color: #6b21a8;
                border: 1px solid #a78bfa;
                border-radius: 7px;
                padding: 8px;
                min-height: 25px;
            }
            QComboBox QAbstractItemView, QMenu {
                color: #ffffff;
                background: #160d27;
                selection-color: #ffffff;
                selection-background-color: #6b21a8;
                border: 1px solid #a78bfa;
                outline: 0;
            }
            QPushButton:focus, QLineEdit:focus, QComboBox:focus {
                border: 2px solid #e9d5ff;
            }
            QToolTip {
                color: #ffffff;
                background: #241335;
                border: 1px solid #c4b5fd;
                padding: 6px;
            }

            QLabel {
                color: #f3eef6;
            }

            QPushButton {
                background: rgba(
                    72,
                    27,
                    112,
                    220
                );

                border:
                    1px solid
                    #9333ea;

                border-radius:
                    9px;

                padding:
                    12px;

                color:
                    #ffffff;

                font-weight:
                    bold;
            }

            QPushButton:hover {
                background:
                    rgba(
                        107,
                        33,
                        168,
                        235
                    );

                border:
                    1px solid
                    #c084fc;
            }

            QScrollArea {
                background:
                    transparent;

                border:
                    none;
            }
            """
        )

        root = WallpaperSurface()
        self.wallpaper_surface = root
        root.setObjectName("root")
        self.setCentralWidget(root)

        outer = QVBoxLayout(
            root
        )

        outer.setContentsMargins(
            28,
            24,
            28,
            24,
        )

        header = QLabel(
            "KALI BAY"
        )

        header.setFont(
            QFont(
                "Sans Serif",
                34,
                QFont.Bold,
            )
        )

        header.setStyleSheet(
            "color:#c084fc;"
        )

        outer.addWidget(
            header
        )

        subtitle = QLabel(
            "SPIDER OS SECURITY WORKSPACE\n"
            "Full Kali toolset · Distrobox container with a shared host kernel"
        )

        subtitle.setStyleSheet(
            """
            color:#c7b9d2;
            font-size:14px;
            """
        )

        outer.addWidget(
            subtitle
        )

        self.status = QLabel()

        self.status.setStyleSheet(
            """
            color:#ddd0e7;
            padding:10px 0;
            font-weight:bold;
            """
        )

        outer.addWidget(
            self.status
        )

        controls = QHBoxLayout()

        setup = QPushButton(
            "INITIALIZE / REPAIR FULL KALI"
        )

        self.setup_button = setup
        setup.clicked.connect(
            self.setup_kali
        )

        controls.addWidget(
            setup
        )

        terminal = QPushButton(
            "KALI TERMINAL"
        )

        terminal.clicked.connect(
            self.open_terminal
        )

        controls.addWidget(
            terminal
        )

        update = QPushButton(
            "UPDATE KALI"
        )

        update.clicked.connect(
            self.update_kali
        )

        controls.addWidget(
            update
        )

        refresh = QPushButton(
            "REFRESH STATUS"
        )

        refresh.clicked.connect(
            self.refresh_status
        )

        controls.addWidget(
            refresh
        )

        outer.addLayout(
            controls
        )

        heading = QLabel("SECURITY SECTIONS")
        heading.setStyleSheet(
            "color:#a78bfa;font-size:18px;font-weight:bold;padding-top:12px;"
        )
        outer.addWidget(heading)

        # Tabs share the existing, fully configured Kali Bay container.
        # They do not start a second Kali environment or any SOC services.
        self.security_tabs = QTabWidget()
        self.security_tabs.setObjectName("securitySections")
        self.security_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #5b3376;
                border-radius: 10px;
                background: rgba(11, 8, 18, 70);
            }
            QTabBar::tab {
                background: #241335;
                color: #d6c9e2;
                border: 1px solid #5b3376;
                padding: 12px 14px;
                min-width: 115px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: #6b21a8;
                color: white;
                border-color: #c084fc;
            }
        """)
        self.security_tabs.addTab(
            self.build_desktop_page(),
            "DESKTOP HUB",
        )
        self.security_tabs.addTab(
            self.build_category_page(
                OFFENSIVE_CATEGORIES,
                "Assessment and penetration-testing tools for authorized labs.",
            ),
            "OFFENSIVE",
        )
        self.security_tabs.addTab(
            self.build_category_page(
                PURPLE_CATEGORIES,
                "Kali Purple: Identify • Protect • Detect • Respond • Recover. "
                "Tools are installed; SOC services require separate configuration.",
            ),
            "PURPLE DEFENSE",
        )
        self.security_tabs.addTab(
            self.build_lab_page(),
            "LAB NOTES",
        )
        self.security_tabs.addTab(
            self.build_guides_page(),
            "LAB GUIDES",
        )
        self.security_tabs.addTab(
            self.build_ledger_page(),
            "EVIDENCE LEDGER",
        )
        self._focus_search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self._focus_search_shortcut.activated.connect(self.focus_tool_search)
        self.native_max_tools = NativeWorkspaceTools('kali-bay', self)
        self.security_tabs.addTab(self.native_max_tools, 'EVIDENCE & LAB ANALYSIS')
        outer.addWidget(self.security_tabs, 1)

        warning = QLabel(
            "Kali Bay is intended for systems, networks, "
            "applications, and labs you are authorized to assess."
        )

        warning.setAlignment(
            Qt.AlignCenter
        )

        warning.setStyleSheet(
            """
            color:#93869c;
            padding-top:8px;
            """
        )

        outer.addWidget(
            warning
        )

        footer = QLabel(
            "YOUR LIFE. ONE WEB."
        )

        footer.setAlignment(
            Qt.AlignCenter
        )

        footer.setStyleSheet(
            """
            color:#6f6377;
            font-weight:bold;
            """
        )

        outer.addWidget(
            footer
        )

    def build_desktop_page(self):
        """Kali-style application launcher in the native Spider OS workspace.

        This is not a second Linux desktop, virtual machine, or new container.
        Actions delegate to the existing checked Kali Bay manager.
        """
        page = QWidget()
        page.setObjectName("kaliHybridDesktop")
        layout = QHBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(20)

        menu = QWidget()
        menu.setObjectName("kaliApplicationsMenu")
        menu.setMinimumWidth(310)
        left = QVBoxLayout(menu)
        title = QLabel("KALI APPLICATIONS")
        title.setStyleSheet("color:#c4b5fd;font-size:18px;font-weight:bold;")
        left.addWidget(title)
        left.addWidget(QLabel("Search the tools already in Kali Bay."))
        self.desktop_search = QLineEdit()
        self.desktop_search.setObjectName("kaliDesktopSearch")
        self.desktop_search.setPlaceholderText("Search tools or categories…")
        self.desktop_search.textChanged.connect(self.filter_desktop_tools)
        left.addWidget(self.desktop_search)
        self.desktop_category = QComboBox()
        self.desktop_category.setObjectName("kaliDesktopCategories")
        self.desktop_category.addItems(
            ["All categories"] + sorted({item[0] for item in DESKTOP_TOOL_MENU})
        )
        self.desktop_category.currentIndexChanged.connect(
            self.filter_desktop_tools
        )
        left.addWidget(self.desktop_category)
        self.favorite_only = QCheckBox("FAVORITES ONLY")
        self.favorite_only.setObjectName("kaliFavoritesOnly")
        self.favorite_only.setStyleSheet("color:#ffffff;font-weight:bold;")
        self.favorite_only.toggled.connect(self.filter_desktop_tools)
        left.addWidget(self.favorite_only)
        self.installed_desktop_apps = []
        load_apps = QPushButton("LOAD ALL INSTALLED KALI APPS")
        load_apps.setObjectName("kaliLoadInstalledApps")
        load_apps.setToolTip(
            "Read Kali's actual installed system .desktop menu. "
            "Does not install software, run scans or start the container."
        )
        load_apps.clicked.connect(self.start_catalog_load)
        left.addWidget(load_apps)
        self.desktop_apps_status = QLabel(
            "Ten featured tools. Load the installed Kali application catalog."
        )
        self.desktop_apps_status.setObjectName("kaliInstalledAppsStatus")
        self.desktop_apps_status.setWordWrap(True)
        left.addWidget(self.desktop_apps_status)
        self.desktop_list = QListWidget()
        self.desktop_list.setObjectName("kaliDesktopToolList")
        self.desktop_list.setStyleSheet(
            "QListWidget {background:rgba(12,7,24,215);color:#f3e8ff;"
            "border:1px solid #7645a6;border-radius:8px;}"
            "QListWidget::item {padding:9px;}"
            "QListWidget::item:selected {background:#5b21b6;}"
        )
        self.desktop_list.itemDoubleClicked.connect(self.open_desktop_item)
        self.desktop_list.currentItemChanged.connect(self.update_tool_details)
        left.addWidget(self.desktop_list, 1)
        save_favorite = QPushButton("☆ SAVE / REMOVE FAVORITE")
        save_favorite.setObjectName("kaliToggleFavorite")
        save_favorite.clicked.connect(self.toggle_selected_favorite)
        left.addWidget(save_favorite)
        launch = QPushButton("OPEN SELECTED TOOL")
        launch.setObjectName("kaliDesktopLaunchTool")
        launch.clicked.connect(self.open_selected_desktop_tool)
        left.addWidget(launch)
        layout.addWidget(menu, 2)

        actions = QWidget()
        actions.setObjectName("kaliDesktopQuickActions")
        right = QVBoxLayout(actions)
        right.setSpacing(12)
        hero = QLabel("KALI LINUX × SPIDER OS")
        hero.setStyleSheet("font-size:24px;font-weight:bold;color:#c084fc;")
        right.addWidget(hero)
        about = QLabel(
            "Use actual Kali Linux applications, the interactive Kali "
            "terminal and Kali's own apt repositories within your existing "
            "Distrobox installation. Spider OS provides the desktop workspace "
            "and Webbie. No separate VM is required for ordinary tool use."
        )
        about.setWordWrap(True)
        right.addWidget(about)
        self.readiness_summary = QLabel(
            "Readiness not checked. Select READINESS REPORT for a "
            "read-only check of the existing Kali environment."
        )
        self.readiness_summary.setObjectName("kaliReadinessSummary")
        self.readiness_summary.setWordWrap(True)
        self.readiness_summary.setStyleSheet(
            "background:#160d27;color:#f3e8ff;border:1px solid #a78bfa;"
            "border-radius:8px;padding:12px;"
        )
        right.addWidget(self.readiness_summary)
        self.tool_details = QLabel("Choose a tool to see its purpose. Only you launch it.")
        self.tool_details.setObjectName("kaliSelectedToolDetails")
        self.tool_details.setWordWrap(True)
        self.tool_details.setStyleSheet(
            "color:#ffffff;background:#1f1233;border:1px solid #6d42a1;"
            "border-radius:7px;padding:10px;"
        )
        right.addWidget(self.tool_details)
        for caption, operation in (
            ("START EXISTING KALI", self.start_existing_kali),
            ("KALI HEALTH CHECK", self.open_kali_health),
            ("READINESS REPORT", self.show_readiness_report),
            ("KALI TERMINAL", self.open_terminal),
            ("KALI PACKAGE MANAGER", self.open_packages),
            ("INSTALLED KALI PACKAGES", self.open_inventory),
            ("KALI FILES", self.open_kali_files),
            ("ASK WEBBIE · SECURITY ASSISTANT", self.open_webbie_security),
            ("OFFENSIVE SECURITY", lambda: self.security_tabs.setCurrentIndex(1)),
            ("PURPLE DEFENSE", lambda: self.security_tabs.setCurrentIndex(2)),
        ):
            button = QPushButton(caption)
            button.setMinimumHeight(49)
            button.clicked.connect(operation)
            right.addWidget(button)
        notice = QLabel(
            "Opening a workbench does not launch a scan. Kali files are "
            "the container's dedicated home folder; they are opened with "
            "the Spider OS file manager. Only use tools on authorized systems."
        )
        notice.setWordWrap(True)
        notice.setStyleSheet("color:#c4aedb;")
        right.addWidget(notice)
        right.addStretch(1)
        actions_scroll = QScrollArea()
        actions_scroll.setObjectName("kaliDesktopActionsScroll")
        actions_scroll.setWidgetResizable(True)
        actions_scroll.setWidget(actions)
        layout.addWidget(actions_scroll, 3)
        self.filter_desktop_tools()
        return page

    def filter_desktop_tools(self, *_args):
        query = self.desktop_search.text().strip().casefold()
        category = self.desktop_category.currentText()
        favorites_only = self.favorite_only.isChecked()
        self.desktop_list.clear()
        for group, label, tool_id in DESKTOP_TOOL_MENU:
            favorite = "builtin:" + tool_id
            if favorites_only and favorite not in self.favorites:
                continue
            if category != "All categories" and group != category:
                continue
            if query and query not in (group + " " + label).casefold():
                continue
            star = "★ " if favorite in self.favorites else ""
            item = QListWidgetItem(f"{star}{group}  /  {label}")
            item.setData(Qt.UserRole, tool_id)
            self.desktop_list.addItem(item)
        for app in self.installed_desktop_apps:
            favorite = "app:" + app["id"]
            if favorites_only and favorite not in self.favorites:
                continue
            group = app["category"]
            label = app["name"]
            if category != "All categories" and group != category:
                continue
            if query and query not in (
                group + " " + label + " " + app["description"]
            ).casefold():
                continue
            star = "★ " if favorite in self.favorites else ""
            item = QListWidgetItem(f"{star}{group}  /  {label}")
            item.setToolTip(app["description"])
            item.setData(Qt.UserRole, ("app", app["id"]))
            self.desktop_list.addItem(item)
        if self.desktop_list.count():
            self.desktop_list.setCurrentRow(0)

    def focus_tool_search(self):
        self.security_tabs.setCurrentIndex(0)
        self.desktop_search.setFocus()
        self.desktop_search.selectAll()

    def selected_favorite_key(self):
        item = self.desktop_list.currentItem()
        if item is None:
            return None
        value = item.data(Qt.UserRole)
        if isinstance(value, str):
            if value in {row[2] for row in DESKTOP_TOOL_MENU}:
                return "builtin:" + value
        elif isinstance(value, (list, tuple)) and len(value) == 2:
            if value[0] == "app" and value[1] in {
                app["id"] for app in self.installed_desktop_apps
            }:
                return "app:" + value[1]
        return None

    def toggle_selected_favorite(self):
        key = self.selected_favorite_key()
        if key is None:
            QMessageBox.information(self, "Kali Bay", "Select a valid Kali tool first.")
            return
        try:
            self.favorites = kali_store.set_favorite(
                key, key not in self.favorites
            )
            self.favorites_error = ""
            self.filter_desktop_tools()
        except kali_store.StorageError as error:
            QMessageBox.warning(self, "Kali Bay", str(error))

    def update_tool_details(self, item, _previous=None):
        if item is None or not hasattr(self, "tool_details"):
            return
        value = item.data(Qt.UserRole)
        explanations = {
            "wireshark": "Inspect packet captures for traffic analysis.",
            "nmap": "Open an interactive shell for authorized network inventory.",
            "burpsuite": "Examine authorized web application requests.",
            "zaproxy": "Review web application security in your own lab.",
            "ghidra": "Reverse engineer binary files in a controlled workspace.",
            "msfconsole": "Open a workbench for a pre-approved test lab.",
            "suricata": "Investigate detection rules and network evidence.",
            "yara": "Inspect files and malware signatures.",
            "lynis": "Review system hardening and audit guidance.",
            "clamtk": "Inspect local files using an antivirus interface.",
        }
        if isinstance(value, str):
            detail = explanations.get(value, "Approved Kali tool.")
        elif isinstance(value, (tuple, list)) and len(value) == 2:
            matches = [
                app for app in self.installed_desktop_apps
                if app["id"] == value[1] and value[0] == "app"
            ]
            detail = matches[0]["description"] if matches else "Kali application."
        else:
            detail = "Select an installed Kali application."
        self.tool_details.setText(
            f"{item.text()}\n{detail or 'Installed Kali application.'}\n"
            "Opening a tool does not run a scan automatically."
        )

    def open_selected_desktop_tool(self):
        item = self.desktop_list.currentItem()
        if item is None:
            QMessageBox.information(self, "Kali Bay", "Select an application first.")
            return
        self.open_desktop_item(item)

    def open_desktop_item(self, item):
        value = item.data(Qt.UserRole)
        if isinstance(value, (tuple, list)) and len(value) == 2:
            if value[0] == "app":
                self.open_installed_kali_app(value[1])
            return
        # Static featured tools retain the fixed legacy approved manager IDs.
        self.open_tool(value)

    def start_catalog_load(self):
        if self.catalog_worker is not None:
            return
        self.desktop_apps_status.setText(
            "Checking installed Kali apps in the background. No tool started."
        )
        worker = KaliCatalogWorker(self)
        self.catalog_worker = worker
        worker.loaded.connect(
            lambda result: self.load_installed_desktop_apps(payload=result)
        )
        worker.failed.connect(self.catalog_load_error)
        worker.finished.connect(self.catalog_load_finished)
        worker.start()

    def catalog_load_error(self, message):
        self.desktop_apps_status.setText(
            "Kali app discovery unavailable: " + str(message)[:180]
        )

    def catalog_load_finished(self):
        worker = self.catalog_worker
        self.catalog_worker = None
        if worker is not None:
            worker.deleteLater()

    def load_installed_desktop_apps(self, payload=None):
        """Inventory only. Never initialize/start Kali or run app Exec lines."""
        try:
            import json
            if payload is None:
                result = subprocess.run(
                    [str(MANAGER), "apps-json"],
                    capture_output=True, text=True, timeout=24, check=False,
                )
                if result.returncode:
                    raise ValueError(
                        (result.stderr or result.stdout).strip()[:220]
                        or "Kali isn't running or desktop apps are unavailable."
                    )
                payload = result.stdout
            document = json.loads(payload)
            if not isinstance(document, dict):
                raise ValueError("Unexpected Kali application inventory.")
            apps = document.get("applications", [])
            if not isinstance(apps, list):
                raise ValueError("Unexpected Kali application inventory.")
            import re
            id_pattern = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,100}\.desktop$")
            cleaned = []
            for app in apps[:1500]:
                if not isinstance(app, dict):
                    continue
                app_id = app.get("id")
                name = app.get("name")
                group = app.get("category", "Other")
                if not isinstance(app_id, str) or not id_pattern.fullmatch(app_id):
                    continue
                if not isinstance(name, str) or not name.strip():
                    continue
                if not isinstance(group, str):
                    group = "Other"
                description = app.get("description", "")
                if not isinstance(description, str):
                    description = ""
                cleaned.append({
                    "id": app_id,
                    "name": name[:95],
                    "category": (group.strip() or "Other")[:55],
                    "description": description[:200],
                })
            self.installed_desktop_apps = cleaned
            selected = self.desktop_category.currentText()
            all_groups = sorted(
                {item[0] for item in DESKTOP_TOOL_MENU}
                | {item["category"] for item in cleaned}
            )
            self.desktop_category.blockSignals(True)
            self.desktop_category.clear()
            self.desktop_category.addItems(["All categories"] + all_groups)
            index = self.desktop_category.findText(selected)
            self.desktop_category.setCurrentIndex(max(index, 0))
            self.desktop_category.blockSignals(False)
            self.desktop_apps_status.setText(
                f"{len(cleaned)} installed Kali applications loaded. "
                "Select one and click Open. No programs were started."
            )
            self.filter_desktop_tools()
        except (OSError, subprocess.TimeoutExpired, ValueError) as error:
            self.desktop_apps_status.setText("Application discovery unavailable.")
            QMessageBox.information(
                self, "Kali Bay", f"Could not list Kali applications: {error}"
            )

    def open_installed_kali_app(self, app_id):
        # Only manually selected inventory entries reach app-open.
        if app_id not in {app["id"] for app in self.installed_desktop_apps}:
            return
        try:
            preflight = subprocess.run(
                [str(MANAGER), "app-check", app_id],
                text=True, capture_output=True, check=False, timeout=12,
            )
            if preflight.returncode:
                QMessageBox.information(
                    self, "Kali Bay",
                    (preflight.stderr or preflight.stdout).strip()[:280]
                    or "Kali application is not available."
                )
                return
            subprocess.Popen(
                [str(MANAGER), "app-open", app_id], start_new_session=True,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            QMessageBox.warning(
                self, "Kali Bay", f"Could not launch Kali app: {error}"
            )

    def start_existing_kali(self):
        reply = QMessageBox.question(
            self, "Start Kali Bay",
            "Start your existing Kali Linux container? No packages are "
            "installed and no new container is created. You can run the "
            "health check afterward.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            result = subprocess.run(
                [str(MANAGER), "start"],
                text=True, capture_output=True, check=False, timeout=40,
            )
        except (OSError, subprocess.TimeoutExpired):
            QMessageBox.warning(self, "Kali Bay", "Kali start did not finish.")
            return
        if result.returncode:
            QMessageBox.warning(
                self, "Kali Bay",
                (result.stderr or result.stdout).strip()[:350]
                or "Kali could not start."
            )
            return
        QMessageBox.information(
            self, "Kali Bay",
            (result.stdout or "The existing Kali container has started.").strip()[:350]
        )
        self.refresh_status()

    def open_kali_health(self):
        # Read-only diagnostic terminal for the existing container.
        self.launch_terminal_command([MANAGER, "doctor"])

    def show_readiness_report(self):
        """Show a fixed, read-only snapshot without starting Kali or repairs."""
        try:
            import json
            result = subprocess.run(
                [str(MANAGER), "readiness-json"],
                text=True, capture_output=True, check=False, timeout=15,
            )
            if result.returncode:
                raise ValueError(
                    (result.stderr or result.stdout).strip()[:180]
                    or "Kali Bay readiness check is unavailable."
                )
            report = json.loads(result.stdout)
            if not isinstance(report, dict):
                raise ValueError("Unexpected Kali readiness response.")
            state = report.get("container_state", "unknown")
            if state not in ("running", "stopped", "missing", "unknown"):
                state = "unknown"
            def available(key):
                return "YES" if report.get(key) is True else "NO"
            next_step = report.get("next_step", "Review Kali health manually.")
            if not isinstance(next_step, str):
                next_step = "Review Kali health manually."
            next_step = next_step[:220]
            self.readiness_summary.setText(
                f"Podman: {available('podman')}    "
                f"Distrobox: {available('distrobox')}\n"
                f"Kali container: {state.upper()}    "
                f"Full toolkit verified: {available('toolkit_ready')}\n"
                f"GUI session: {available('gui_session')}    "
                f"App catalog source: {available('catalog_source')}\n"
                f"NEXT: {next_step}"
            )
        except (OSError, subprocess.TimeoutExpired, ValueError) as error:
            self.readiness_summary.setText(
                f"Readiness check unavailable: {str(error)[:180]}. "
                "No container or packages were changed."
            )

    def open_packages(self):
        # Explicit interactive shell in the existing Kali Distrobox.
        # No apt action runs until the user types it inside the terminal.
        self.launch_terminal_command([MANAGER, "packages"])

    def open_inventory(self):
        # Read-only installed package report with no container startup.
        self.launch_terminal_command([MANAGER, "inventory"])

    def open_kali_files(self):
        # This dedicated Distrobox home is already created by the Kali manager.
        # Do not browse arbitrary host folders or create/change any files here.
        path = Path.home() / ".local/share/spider-os/kali-bay/home"
        if not path.is_dir():
            QMessageBox.information(
                self, "Kali Bay", "Kali Bay's home directory is not available yet."
            )
            return
        command = "dolphin" if shutil_which("dolphin") else "xdg-open"
        if not shutil_which(command):
            QMessageBox.information(
                self, "Kali Bay", "No graphical file manager is available."
            )
            return
        try:
            subprocess.Popen([command, str(path)], start_new_session=True)
        except OSError as error:
            QMessageBox.warning(self, "Kali Bay", str(error))

    def open_webbie_security(self):
        # This is a lightweight second UI for the SAME resident Webbie socket,
        # not a duplicate listener, model, portrait or privileged service.
        self.webbie_dock.show()
        self.webbie_dock.raise_()
        self.webbie_chat_entry.setFocus()

    def build_webbie_dock(self):
        """One optional inline chat UI for the already-running Webbie agent.

        Not another LLM instance, voice listener, webcam or authentication
        service. The same strict Kali action bridge handles explicit messages.
        """
        self.webbie_worker = None
        self.webbie_dock = QDockWidget("WEBBIE | KALI BAY", self)
        self.webbie_dock.setObjectName("kaliWebbieAssistantDock")
        self.webbie_dock.setAllowedAreas(
            Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea
        )
        panel = QWidget()
        panel.setObjectName("kaliWebbieChatPanel")
        panel.setStyleSheet(
            "QWidget#kaliWebbieChatPanel {background:#170e27;color:#f3e8ff;}"
            "QPlainTextEdit, QLineEdit {background:#0c0718;color:#f3e8ff;"
            "border:1px solid #6842a0;border-radius:7px;padding:6px;}"
        )
        layout = QVBoxLayout(panel)
        title = QLabel("WEBBIE · SECURITY ASSISTANT")
        title.setStyleSheet("font-weight:bold;color:#c4b5fd;")
        layout.addWidget(title)
        hint = QLabel(
            "This chat uses the existing resident Webbie. "
            "No separate AI or camera is started. "
            "Dynamic Kali applications are still opened by you."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.webbie_chat_log = QPlainTextEdit()
        self.webbie_chat_log.setObjectName("kaliWebbieConversation")
        self.webbie_chat_log.setReadOnly(True)
        layout.addWidget(self.webbie_chat_log, 1)
        self.webbie_chat_entry = QLineEdit()
        self.webbie_chat_entry.setObjectName("kaliWebbieEntry")
        self.webbie_chat_entry.setPlaceholderText(
            "Ask Webbie about Kali or an installed tool…"
        )
        self.webbie_chat_entry.returnPressed.connect(self.send_webbie_chat)
        layout.addWidget(self.webbie_chat_entry)
        self.webbie_send_button = QPushButton("SEND TO WEBBIE")
        self.webbie_send_button.setObjectName("kaliWebbieSend")
        self.webbie_send_button.clicked.connect(self.send_webbie_chat)
        layout.addWidget(self.webbie_send_button)
        self.webbie_dock.setWidget(panel)
        self.addDockWidget(Qt.RightDockWidgetArea, self.webbie_dock)
        self.webbie_dock.hide()

    def send_webbie_chat(self):
        content = self.webbie_chat_entry.text().strip()
        if not content or (self.webbie_worker and self.webbie_worker.isRunning()):
            return
        if len(content.encode("utf-8")) > 8000:
            self.webbie_chat_log.appendPlainText("System: Shorten your question.")
            return
        base = os.environ.get(
            "XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"
        )
        sock = Path(base) / "spider-os" / "webbie.sock"
        request = (
            "[Spider OS workspace context; advisory only]\\n"
            "Workspace: Kali Bay\\n"
            "Mode: Security Assistant\\n"
            "Preferred address: Spider; this is not identity verification.\\n"
            "[User request]\\n" + content
        )
        self.webbie_chat_log.appendPlainText("You: " + content)
        self.webbie_chat_entry.clear()
        self.webbie_chat_entry.setEnabled(False)
        self.webbie_send_button.setEnabled(False)
        self.webbie_chat_log.appendPlainText("Webbie: thinking…")
        worker = KaliWebbieReplyWorker(request, sock, self)
        self.webbie_worker = worker
        worker.received.connect(self.webbie_answer)
        worker.failed.connect(self.webbie_error)
        worker.finished.connect(self.webbie_chat_finished)
        worker.start()

    def webbie_answer(self, answer):
        self.webbie_chat_log.appendPlainText("Webbie: " + answer)

    def webbie_error(self, message):
        self.webbie_chat_log.appendPlainText("System: " + message)

    def webbie_chat_finished(self):
        finished = self.webbie_worker
        self.webbie_worker = None
        if finished is not None:
            finished.deleteLater()
        self.webbie_chat_entry.setEnabled(True)
        self.webbie_send_button.setEnabled(True)
        self.webbie_chat_entry.setFocus()

    def closeEvent(self, event):
        if self.evidence_worker and self.evidence_worker.isRunning():
            event.ignore()
            self.lab_status.setText(
                "Selected-file fingerprint is finishing; no file was changed."
            )
            return
        if self.catalog_worker and self.catalog_worker.isRunning():
            event.ignore()
            self.desktop_apps_status.setText(
                "Catalog lookup is finishing; no Kali app was launched."
            )
            return
        if self.webbie_worker and self.webbie_worker.isRunning():
            event.ignore()
            self.webbie_chat_log.appendPlainText(
                "System: The current Webbie reply is finishing."
            )
            self.webbie_dock.show()
            return
        super().closeEvent(event)

    def build_lab_page(self):
        """Private lab notebook. No scans, network connections or auto-sharing."""
        page = QWidget()
        page.setObjectName("kaliLabWorkspace")
        layout = QHBoxLayout(page)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        sidebar = QWidget()
        sidebar.setMinimumWidth(245)
        left = QVBoxLayout(sidebar)
        heading = QLabel("MY AUTHORIZED LABS")
        heading.setStyleSheet("color:#e9d5ff;font-size:18px;font-weight:bold;")
        left.addWidget(heading)
        explanation = QLabel(
            "Keep local investigation notes and authorized lab plans. "
            "Nothing runs or gets sent to Webbie automatically."
        )
        explanation.setWordWrap(True)
        left.addWidget(explanation)
        self.lab_list = QListWidget()
        self.lab_list.setObjectName("kaliLabNotebookList")
        self.lab_list.setStyleSheet(
            "QListWidget {background:#160d27;color:#ffffff;"
            "border:1px solid #a78bfa;border-radius:7px;}"
            "QListWidget::item {padding:10px;}"
            "QListWidget::item:selected {background:#6b21a8;}"
        )
        self.lab_list.currentItemChanged.connect(self.load_selected_lab)
        left.addWidget(self.lab_list, 1)
        create = QPushButton("NEW LAB NOTEBOOK")
        create.setObjectName("kaliCreateLab")
        create.clicked.connect(self.create_new_lab)
        left.addWidget(create)
        refresh = QPushButton("REFRESH MY LABS")
        refresh.clicked.connect(self.refresh_labs)
        left.addWidget(refresh)
        layout.addWidget(sidebar, 1)

        editor_area = QWidget()
        right = QVBoxLayout(editor_area)
        self.lab_title = QLabel("Select a lab or create one.")
        self.lab_title.setObjectName("kaliLabTitle")
        self.lab_title.setStyleSheet(
            "color:#f5e9ff;font-size:20px;font-weight:bold;"
        )
        right.addWidget(self.lab_title)
        self.lab_editor = QPlainTextEdit()
        self.lab_editor.setObjectName("kaliLabNotesEditor")
        self.lab_editor.setPlaceholderText(
            "Scope and authorization\nObservation\nEvidence references\n"
            "Assessment notes\nNext steps\n\n"
            "Notes stay on this PC until you explicitly choose to share."
        )
        self.lab_editor.setEnabled(False)
        right.addWidget(self.lab_editor, 1)
        controls = QHBoxLayout()
        save = QPushButton("SAVE LOCAL NOTES")
        save.setObjectName("kaliSaveLabNotes")
        save.clicked.connect(self.save_active_lab)
        controls.addWidget(save)
        share = QPushButton("PREPARE NOTES FOR WEBBIE")
        share.setObjectName("kaliPrepareLabWebbie")
        share.clicked.connect(self.prepare_lab_for_webbie)
        controls.addWidget(share)
        export = QPushButton("EXPORT SAVED REPORT")
        export.setObjectName("kaliExportLabReport")
        export.setToolTip(
            "Creates a private Markdown report from the most recently "
            "saved revision. Unsaved editor text is never exported."
        )
        export.clicked.connect(self.export_active_lab_report)
        controls.addWidget(export)
        right.addLayout(controls)
        evidence_controls = QHBoxLayout()
        calculate = QPushButton("FINGERPRINT SELECTED FILE")
        calculate.setObjectName("kaliFingerprintFile")
        calculate.setToolTip(
            "Read SHA-256 of a file you select, up to 256 MiB. "
            "The file is not executed, copied or uploaded."
        )
        calculate.clicked.connect(self.select_evidence_file)
        evidence_controls.addWidget(calculate)
        append = QPushButton("ADD FINGERPRINT TO NOTES")
        append.setObjectName("kaliAppendFingerprint")
        append.clicked.connect(self.append_evidence_record)
        evidence_controls.addWidget(append)
        right.addLayout(evidence_controls)
        self.lab_status = QLabel("Locally stored in your private Spider OS home.")
        self.lab_status.setObjectName("kaliLabStatus")
        self.lab_status.setWordWrap(True)
        self.lab_status.setStyleSheet("color:#ddd6fe;")
        right.addWidget(self.lab_status)
        layout.addWidget(editor_area, 2)
        self.refresh_labs()
        return page

    def _lab_has_unsaved_changes(self):
        return bool(
            self.active_lab is not None
            and self.lab_editor.toPlainText() != self.active_lab["notes"]
        )

    def _confirm_discard_lab(self):
        if not self._lab_has_unsaved_changes():
            return True
        response = QMessageBox.question(
            self, "Unsaved Kali Bay notes",
            "Discard the unsaved edits in the current local lab notebook?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        return response == QMessageBox.Yes

    def refresh_labs(self, select_id=None):
        if not self._confirm_discard_lab():
            return
        try:
            labs = kali_store.list_labs()
        except (kali_store.StorageError, OSError) as error:
            self.lab_status.setText("Could not list local labs: " + str(error))
            return
        self._switching_labs = True
        self.lab_list.blockSignals(True)
        self.lab_list.clear()
        for lab in labs:
            item = QListWidgetItem(lab["title"])
            item.setData(Qt.UserRole, lab["id"])
            self.lab_list.addItem(item)
        self.lab_list.blockSignals(False)
        self._switching_labs = False
        self.active_lab = None
        self.lab_editor.setEnabled(False)
        self.lab_editor.clear()
        self.lab_title.setText("Select a lab or create one.")
        if hasattr(self, "ledger_events"):
            self.ledger_events = []
            self.ledger_list.clear()
            self.ledger_status.setText("Select a lab in LAB NOTES.")
        self.lab_status.setText(
            f"{len(labs)} private lab notebooks. "
            "Only explicit Save writes notes to your computer."
        )
        if select_id:
            for i in range(self.lab_list.count()):
                item = self.lab_list.item(i)
                if item.data(Qt.UserRole) == select_id:
                    self.lab_list.setCurrentRow(i)
                    break

    def load_selected_lab(self, item, previous=None):
        if self._switching_labs:
            return
        if not self._confirm_discard_lab():
            self.lab_list.blockSignals(True)
            if previous is not None:
                self.lab_list.setCurrentItem(previous)
            else:
                self.lab_list.setCurrentRow(-1)
            self.lab_list.blockSignals(False)
            return
        self.active_lab = None
        self.lab_editor.clear()
        self.lab_editor.setEnabled(False)
        if item is None:
            self.lab_title.setText("Select a lab or create one.")
            return
        try:
            lab = kali_store.get_lab(item.data(Qt.UserRole))
        except (kali_store.StorageError, OSError) as error:
            self.lab_status.setText("Lab is unavailable: " + str(error))
            return
        self.active_lab = lab
        if self.evidence_lab_id != lab["id"]:
            self.evidence_result = None
        self.lab_title.setText(lab["title"])
        self.lab_editor.setPlainText(lab["notes"])
        self.lab_editor.setEnabled(True)
        if hasattr(self, "ledger_list"):
            self.refresh_evidence_ledger()
        self.lab_status.setText(
            f"Private local notebook · revision {lab['revision']} · "
            "No automatic scanning or sharing."
        )

    def create_new_lab(self):
        if not self._confirm_discard_lab():
            return
        title, accepted = QInputDialog.getText(
            self, "New Kali Bay lab", "Lab or investigation name:"
        )
        if not accepted:
            return
        try:
            lab = kali_store.create_lab(title)
            self.active_lab = None
            self.refresh_labs(select_id=lab["id"])
        except (kali_store.StorageError, OSError) as error:
            QMessageBox.warning(self, "Kali Bay", str(error))

    def save_active_lab(self):
        if not self.active_lab:
            QMessageBox.information(self, "Kali Bay", "Choose a lab notebook first.")
            return
        try:
            lab = kali_store.save_lab(
                self.active_lab["id"], self.lab_editor.toPlainText(),
                expected_revision=self.active_lab["revision"],
            )
            self.active_lab = lab
            self.lab_status.setText(
                f"Saved locally · revision {lab['revision']} · no data shared."
            )
        except (kali_store.StorageError, OSError) as error:
            QMessageBox.warning(
                self, "Kali Bay",
                f"Notes were not overwritten: {error}"
            )

    def prepare_lab_for_webbie(self):
        if not self.active_lab:
            QMessageBox.information(self, "Kali Bay", "Choose a lab notebook first.")
            return
        confirm = QMessageBox.question(
            self, "Review before sharing",
            "Prepare up to 5,000 characters of these notes in Webbie's chat? "
            "Nothing is sent until you press SEND TO WEBBIE. "
            "Review sensitive details first.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        notes = self.lab_editor.toPlainText()[:5000]
        text = (
            "Help me review this authorized security lab. Offer defensive "
            "investigation guidance; do not run commands. "
            f"Lab: {self.active_lab['title']}\nNotes:\n{notes}"
        )
        self.open_webbie_security()
        self.webbie_chat_entry.setText(text)
        self.webbie_chat_entry.setFocus()
        self.lab_status.setText(
            "Notes prepared in Webbie's message box. Review and send manually."
        )

    def select_evidence_file(self):
        if not self.active_lab:
            QMessageBox.information(
                self, "Kali Bay", "Choose an authorized lab notebook first."
            )
            return
        if self.evidence_worker is not None:
            return
        filename, _filter = QFileDialog.getOpenFileName(
            self, "Choose evidence for read-only SHA-256", str(Path.home()),
            "All files (*)"
        )
        if not filename:
            return
        self.evidence_result = None
        self.evidence_lab_id = self.active_lab["id"]
        self.lab_status.setText(
            "Calculating a local fingerprint. No file is uploaded or executed."
        )
        worker = KaliEvidenceWorker(filename, self)
        self.evidence_worker = worker
        worker.ready.connect(self.evidence_ready)
        worker.failed.connect(self.evidence_failed)
        worker.finished.connect(self.evidence_finished)
        worker.start()

    def evidence_ready(self, result):
        self.evidence_result = result
        self.lab_status.setText(
            f"SHA-256 computed for {result['filename']} "
            f"({result['size_bytes']} bytes). Click ADD FINGERPRINT TO NOTES "
            "to include it. No data has been uploaded or saved to notes."
        )

    def evidence_failed(self, message):
        self.evidence_result = None
        self.lab_status.setText(
            "Evidence fingerprint unavailable: " + str(message)[:220]
        )

    def evidence_finished(self):
        worker = self.evidence_worker
        self.evidence_worker = None
        if worker is not None:
            worker.deleteLater()

    def append_evidence_record(self):
        if not self.active_lab or not self.evidence_result:
            QMessageBox.information(
                self, "Kali Bay", "Select a lab and fingerprint a file first."
            )
            return
        if self.evidence_lab_id != self.active_lab["id"]:
            self.evidence_result = None
            QMessageBox.warning(
                self, "Kali Bay",
                "You changed labs. Select the evidence file again."
            )
            return
        try:
            record = kali_evidence.note_entry(self.evidence_result)
        except kali_evidence.EvidenceError as error:
            QMessageBox.warning(self, "Kali Bay", str(error))
            return
        contents = self.lab_editor.toPlainText()
        if len(contents) + len(record) > kali_store.MAX_NOTE_CHARS:
            QMessageBox.warning(
                self, "Kali Bay", "Your notebook is too large for this record."
            )
            return
        self.lab_editor.setPlainText(contents + record)
        self.evidence_result = None
        self.lab_status.setText(
            "Fingerprint added to UNSAVED notes. Click SAVE LOCAL NOTES "
            "to retain it; no evidence file was modified or uploaded."
        )

    def export_active_lab_report(self):
        """Explicit file creation from SAVED notes, never hidden background export."""
        if not self.active_lab:
            QMessageBox.information(self, "Kali Bay", "Select a saved lab first.")
            return
        if self._lab_has_unsaved_changes():
            QMessageBox.information(
                self, "Save notes first",
                "Save your current edits before exporting a report. "
                "No report has been created."
            )
            return
        try:
            destination = kali_reports.export_saved_report(
                self.active_lab["id"]
            )
            self.lab_status.setText(
                "Private report saved locally: " + str(destination)
            )
        except (kali_store.StorageError, OSError) as error:
            QMessageBox.warning(
                self, "Kali Bay", "Report was not exported: " + str(error)
            )

    def build_guides_page(self):
        """Offline static learning workflows; no commands or generated targets."""
        page = QWidget()
        page.setObjectName("kaliLabGuides")
        layout = QHBoxLayout(page)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(16)
        sidebar = QWidget()
        left = QVBoxLayout(sidebar)
        heading = QLabel("DEFENSIVE LAB GUIDES")
        heading.setStyleSheet("font-size:18px;color:#f5e9ff;font-weight:bold;")
        left.addWidget(heading)
        info = QLabel(
            "Offline investigation checklists for your authorized labs. "
            "Selecting a guide never scans, installs or executes anything."
        )
        info.setWordWrap(True)
        left.addWidget(info)
        self.guide_search = QLineEdit()
        self.guide_search.setObjectName("kaliGuideSearch")
        self.guide_search.setPlaceholderText("Search workflows…")
        self.guide_search.textChanged.connect(self.filter_guides)
        left.addWidget(self.guide_search)
        self.guide_list = QListWidget()
        self.guide_list.setObjectName("kaliGuidesList")
        self.guide_list.setStyleSheet(
            "QListWidget {background:#160d27;color:#ffffff;"
            "border:1px solid #a78bfa;border-radius:7px;}"
            "QListWidget::item {padding:10px;}"
            "QListWidget::item:selected {background:#6b21a8;}"
        )
        self.guide_list.currentItemChanged.connect(self.preview_guide)
        left.addWidget(self.guide_list, 1)
        layout.addWidget(sidebar, 1)
        right_widget = QWidget()
        right = QVBoxLayout(right_widget)
        self.guide_title = QLabel("Choose a defensive workflow.")
        self.guide_title.setObjectName("kaliGuideTitle")
        self.guide_title.setStyleSheet(
            "font-size:19px;color:#e9d5ff;font-weight:bold;"
        )
        right.addWidget(self.guide_title)
        self.guide_preview = QPlainTextEdit()
        self.guide_preview.setObjectName("kaliGuidePreview")
        self.guide_preview.setReadOnly(True)
        right.addWidget(self.guide_preview, 1)
        create = QPushButton("CREATE NOTEBOOK FROM GUIDE")
        create.setObjectName("kaliCreateGuidedLab")
        create.clicked.connect(self.create_guided_lab)
        right.addWidget(create)
        disclosure = QLabel(
            "This creates a new PRIVATE local notebook with the guide "
            "template only after you confirm. It does not run Kali commands."
        )
        disclosure.setWordWrap(True)
        right.addWidget(disclosure)
        layout.addWidget(right_widget, 2)
        self.filter_guides()
        return page

    def filter_guides(self, *_args):
        previous = self.guide_list.currentItem()
        previous_id = previous.data(Qt.UserRole) if previous else None
        choices = kali_reports.list_guides(self.guide_search.text())
        self.guide_list.clear()
        for guide in choices:
            item = QListWidgetItem(
                f"{guide['category']}  /  {guide['title']}"
            )
            item.setData(Qt.UserRole, guide["id"])
            self.guide_list.addItem(item)
        selected = 0
        if previous_id:
            for index in range(self.guide_list.count()):
                if self.guide_list.item(index).data(Qt.UserRole) == previous_id:
                    selected = index
                    break
        if self.guide_list.count():
            self.guide_list.setCurrentRow(selected)
        else:
            self.guide_title.setText("No guide matches your search.")
            self.guide_preview.clear()

    def preview_guide(self, item, _previous=None):
        if item is None:
            return
        try:
            guide = kali_reports.guide_by_id(item.data(Qt.UserRole))
            self.guide_title.setText(guide["title"])
            self.guide_preview.setPlainText(
                kali_reports.guide_template(guide["id"])
            )
        except kali_store.StorageError:
            self.guide_title.setText("Unavailable guide")
            self.guide_preview.clear()

    def create_guided_lab(self):
        current = self.guide_list.currentItem()
        if current is None:
            QMessageBox.information(self, "Kali Bay", "Select a guide first.")
            return
        if not self._confirm_discard_lab():
            return
        try:
            guide = kali_reports.guide_by_id(current.data(Qt.UserRole))
            template = kali_reports.guide_template(guide["id"])
        except kali_store.StorageError as error:
            QMessageBox.warning(self, "Kali Bay", str(error))
            return
        reply = QMessageBox.question(
            self, "Create authorized lab",
            f"Create a private notebook based on {guide['title']}? "
            "No security tools will be executed.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            lab = kali_store.create_lab(guide["title"])
            saved = kali_store.save_lab(
                lab["id"], template, expected_revision=lab["revision"]
            )
            self.active_lab = None
            self.refresh_labs(select_id=saved["id"])
            self.security_tabs.setCurrentIndex(3)
        except (kali_store.StorageError, OSError) as error:
            QMessageBox.warning(self, "Kali Bay", str(error))

    def build_ledger_page(self):
        """Explicit local chain of custody actions, scoped to the selected lab."""
        page = QWidget()
        page.setObjectName("kaliEvidenceLedgerPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 14, 14, 14)
        heading = QLabel("PRIVATE EVIDENCE REGISTER")
        heading.setStyleSheet("color:#f3e8ff;font-size:19px;font-weight:bold;")
        layout.addWidget(heading)
        note = QLabel(
            "Select a lab in LAB NOTES and fingerprint a file you are permitted "
            "to handle. Record events only by clicking below. "
            "SHA-256 chains detect edits to local records; they cannot prove "
            "who handled evidence or whether its origin was authentic."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        self.ledger_status = QLabel("Select a lab in LAB NOTES.")
        self.ledger_status.setObjectName("kaliLedgerStatus")
        self.ledger_status.setWordWrap(True)
        self.ledger_status.setStyleSheet(
            "background:#160d27;color:#ffffff;border:1px solid #a78bfa;"
            "border-radius:8px;padding:10px;"
        )
        layout.addWidget(self.ledger_status)
        self.ledger_events = []
        self.ledger_list = QListWidget()
        self.ledger_list.setObjectName("kaliLedgerEvents")
        self.ledger_list.setStyleSheet(
            "QListWidget {background:#160d27;color:#ffffff;"
            "border:1px solid #a78bfa;border-radius:7px;}"
            "QListWidget::item {padding:8px;}"
            "QListWidget::item:selected {background:#6b21a8;}"
        )
        self.ledger_list.currentItemChanged.connect(self.show_ledger_event)
        layout.addWidget(self.ledger_list, 1)
        self.ledger_details = QLabel(
            "Select a ledger entry to inspect its saved metadata."
        )
        self.ledger_details.setObjectName("kaliLedgerDetails")
        self.ledger_details.setWordWrap(True)
        layout.addWidget(self.ledger_details)
        controls = QHBoxLayout()
        self.ledger_kind = QComboBox()
        self.ledger_kind.setObjectName("kaliLedgerEventKind")
        self.ledger_kind.addItems(
            ["registered", "reviewed", "transferred", "verified", "note"]
        )
        controls.addWidget(self.ledger_kind)
        self.ledger_note = QLineEdit()
        self.ledger_note.setObjectName("kaliLedgerEventNote")
        self.ledger_note.setMaxLength(kali_ledger.MAX_NOTE)
        self.ledger_note.setPlaceholderText(
            "Describe authority, source, recipient or review (required)"
        )
        controls.addWidget(self.ledger_note, 2)
        layout.addLayout(controls)
        actions = QHBoxLayout()
        record = QPushButton("RECORD EXPLICIT EVENT")
        record.setObjectName("kaliRecordEvidenceEvent")
        record.clicked.connect(self.record_evidence_event)
        actions.addWidget(record)
        verify = QPushButton("VERIFY LOCAL CHAIN")
        verify.setObjectName("kaliVerifyEvidenceChain")
        verify.clicked.connect(self.refresh_evidence_ledger)
        actions.addWidget(verify)
        layout.addLayout(actions)
        return page

    def show_ledger_event(self, item, _previous=None):
        if item is None:
            self.ledger_details.setText("No ledger entry selected.")
            return
        try:
            idx = int(item.data(Qt.UserRole))
            entry = self.ledger_events[idx]
        except (TypeError, ValueError, IndexError):
            self.ledger_details.setText("Unknown evidence record.")
            return
        self.ledger_details.setText(
            f"Event #{entry['number']}  {entry['kind'].upper()}\n"
            f"Evidence: {entry['name']}  ({entry['size_bytes']} bytes)\n"
            f"SHA-256: {entry['fingerprint']}\n"
            f"Recorded: {entry['time_utc']}\n"
            f"Note: {entry['note']}"
        )

    def refresh_evidence_ledger(self):
        if not self.active_lab:
            self.ledger_events = []
            self.ledger_list.clear()
            self.ledger_status.setText("Select a lab in LAB NOTES.")
            return
        try:
            ledger = kali_ledger.read_ledger(self.active_lab["id"])
            integrity = kali_ledger.verify_ledger(self.active_lab["id"])
        except (kali_store.StorageError, OSError) as error:
            self.ledger_events = []
            self.ledger_list.clear()
            self.ledger_status.setText(
                "WARNING: Evidence ledger could not be verified: "
                + str(error)[:240]
                + ". Do not use these records until reviewed."
            )
            return
        self.ledger_events = ledger["events"]
        self.ledger_list.clear()
        for pos, event in enumerate(self.ledger_events):
            item = QListWidgetItem(
                f"#{event['number']}  {event['kind'].upper()}  "
                f"{event['name']}  {event['time_utc']}"
            )
            item.setData(Qt.UserRole, pos)
            self.ledger_list.addItem(item)
        self.ledger_status.setText(
            f"Lab: {self.active_lab['title']} | "
            f"{integrity['count']} events | local chain VALID\n"
            f"Latest hash: {integrity['head']}\n"
            "This verifies local consistency, not real-world custody."
        )
        if self.ledger_list.count():
            self.ledger_list.setCurrentRow(self.ledger_list.count() - 1)

    def record_evidence_event(self):
        if not self.active_lab:
            QMessageBox.information(
                self, "Kali Bay", "Select an authorized lab notebook first."
            )
            return
        kind = self.ledger_kind.currentText()
        content = self.ledger_note.text().strip()
        if not content:
            QMessageBox.information(
                self, "Kali Bay", "Describe this evidence event first."
            )
            return
        if kind == "registered":
            if not self.evidence_result or \
                    self.evidence_lab_id != self.active_lab["id"]:
                QMessageBox.information(
                    self, "Kali Bay",
                    "In LAB NOTES, fingerprint an authorized file first."
                )
                return
            metadata = self.evidence_result
        else:
            current = self.ledger_list.currentItem()
            if current is None:
                QMessageBox.information(
                    self, "Kali Bay",
                    "Select an existing evidence record first."
                )
                return
            try:
                row = self.ledger_events[int(current.data(Qt.UserRole))]
                metadata = {
                    "filename": row["name"],
                    "sha256": row["fingerprint"],
                    "size_bytes": row["size_bytes"],
                    "checked_utc": row["checked_utc"],
                }
            except (IndexError, KeyError, TypeError, ValueError):
                return
        answer = QMessageBox.question(
            self, "Confirm evidence record",
            f"Record {kind.upper()} in lab {self.active_lab['title']}?\n"
            "The event will be appended to the local integrity chain. "
            "It will not be sent to Webbie.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        try:
            event = kali_ledger.append_event(
                self.active_lab["id"], kind, metadata, content,
            )
            self.ledger_note.clear()
            self.refresh_evidence_ledger()
            self.ledger_status.setText(
                f"Saved event #{event['number']} with local SHA-256 link. "
                "No evidence files were copied, opened as programs or shared."
            )
        except (kali_store.StorageError, OSError) as error:
            QMessageBox.warning(
                self, "Evidence integrity",
                "No event was saved: " + str(error)
            )

    def check_purple_defense_tools(self):
        """Show installed defensive binaries, never assume services are running."""
        try:
            import json
            result = subprocess.run(
                [str(MANAGER), "purple-json"], text=True,
                capture_output=True, check=False, timeout=18,
            )
            if result.returncode:
                raise ValueError(
                    (result.stderr or result.stdout).strip()[:220]
                    or "Kali Purple tools could not be checked."
                )
            report = json.loads(result.stdout)
            if not isinstance(report, dict):
                raise ValueError("Invalid Kali Purple inventory.")
            state = report.get("state")
            if state != "running":
                if state not in ("stopped", "missing", "unavailable", "unknown"):
                    state = "unknown"
                self.purple_status.setText(
                    f"Kali container: {state.upper()}. "
                    "No defensive services or tools were started."
                )
                return
            found = report.get("tools", {})
            if not isinstance(found, dict):
                raise ValueError("Invalid tool inventory.")
            names = (
                "suricata", "zeek", "yara", "lynis", "clamscan",
                "wireshark", "tcpdump", "tshark", "auditctl",
            )
            installed = [name for name in names if found.get(name) is True]
            absent = [name for name in names if found.get(name) is not True]
            self.purple_status.setText(
                "Available: " + (", ".join(installed) or "none detected")
                + "\nNot detected: " + (", ".join(absent) or "none")
                + "\nThis checks installed commands only. "
                  "Sensors and security services were NOT started."
            )
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            self.purple_status.setText(
                f"Purple tool check unavailable: {str(error)[:180]}. "
                "No container or service was started."
            )

    def build_category_page(self, categories, description):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)

        note = QLabel(description)
        note.setWordWrap(True)
        note.setStyleSheet("color:#c7b9d2;padding:5px 0 12px;")
        layout.addWidget(note)
        if categories is PURPLE_CATEGORIES:
            self.purple_status = QLabel(
                "Detection tools have not been checked. "
                "A tool being installed does not mean its sensor is running."
            )
            self.purple_status.setObjectName("kaliPurpleInventory")
            self.purple_status.setWordWrap(True)
            self.purple_status.setStyleSheet(
                "background:#160d27;color:#ffffff;border:1px solid #a78bfa;"
                "border-radius:8px;padding:12px;"
            )
            layout.addWidget(self.purple_status)
            check = QPushButton("CHECK PURPLE DEFENSE TOOLS (READ ONLY)")
            check.setObjectName("kaliPurpleCheck")
            check.clicked.connect(self.check_purple_defense_tools)
            layout.addWidget(check)

        # Explicit, allowlisted tools only. Buttons never scan a network,
        # install packages, start monitoring, or elevate permissions.
        items = (
            [
                ("Wireshark", "wireshark"),
                ("Burp Suite", "burpsuite"),
                ("OWASP ZAP", "zaproxy"),
                ("Ghidra", "ghidra"),
                ("Nmap terminal", "nmap"),
                ("Metasploit terminal", "msfconsole"),
            ]
            if categories is OFFENSIVE_CATEGORIES
            else [
                ("Wireshark", "wireshark"),
                ("Network inventory shell", "nmap"),
                ("Suricata shell", "suricata"),
                ("YARA shell", "yara"),
                ("Lynis shell", "lynis"),
                ("ClamTK", "clamtk"),
            ]
        )
        featured = QLabel("DIRECT SECURITY TOOL LAUNCHERS")
        featured.setStyleSheet(
            "color:#a78bfa;font-size:15px;font-weight:bold;"
        )
        layout.addWidget(featured)
        featured_grid = QGridLayout()
        featured_grid.setSpacing(8)
        for position, (title, tool_id) in enumerate(items):
            button = QPushButton(title)
            button.setMinimumHeight(44)
            button.setToolTip(
                "Checks availability inside the existing Kali container. "
                "Does not install software or execute security tests."
            )
            button.clicked.connect(
                lambda checked=False, ident=tool_id: self.open_tool(ident)
            )
            featured_grid.addWidget(
                button, position // 3, position % 3
            )
        layout.addLayout(featured_grid)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        container = QWidget()
        container.setStyleSheet("background:transparent;")
        grid = QGridLayout(container)
        grid.setSpacing(14)

        for index, (title, summary, package) in enumerate(categories):
            button = QPushButton(f"{title}\n{summary}")
            button.setMinimumHeight(88)
            button.setToolTip(f"Kali metapackage: {package}")
            button.clicked.connect(
                lambda checked=False, p=package, t=title:
                self.open_category(p, t)
            )
            grid.addWidget(button, index // 3, index % 3)

        scroll.setWidget(container)
        layout.addWidget(scroll, 1)
        return page

    def load_wallpaper(self):
        image = QPixmap(str(WALLPAPER)) if WALLPAPER.is_file() else QPixmap()
        self._wallpaper = image
        self.wallpaper_surface.set_wallpaper(image)

    def manager_status(self):
        try:
            result = subprocess.run(
                [
                    str(MANAGER),
                    "status",
                ],
                text=True,
                capture_output=True,
                timeout=25,
                check=False,
            )

            return (
                result.stdout.strip()
                or "missing"
            )

        except Exception:
            return "error"

    def refresh_status(self):
        status = self.manager_status()

        if status == "ready":
            text = (
                "● FULL KALI BAY READY  "
                "· kali-linux-everything installed"
            )

            style = (
                "color:#c4b5fd;"
                "padding:10px 0;"
                "font-weight:bold;"
            )

        elif status == "container":
            text = (
                "● KALI CONTAINER CREATED  "
                "· full toolset still needs provisioning"
            )

            style = (
                "color:#facc15;"
                "padding:10px 0;"
                "font-weight:bold;"
            )

        elif status == "error":
            text = (
                "● KALI BAY STATUS ERROR"
            )

            style = (
                "color:#fb7185;"
                "padding:10px 0;"
                "font-weight:bold;"
            )

        else:
            text = (
                "● KALI BAY NOT INITIALIZED"
            )

            style = (
                "color:#a89caf;"
                "padding:10px 0;"
                "font-weight:bold;"
            )

        self.setup_button.setEnabled(status != "ready")
        self.setup_button.setText(
            "FULL TOOLKIT INSTALLED" if status == "ready"
            else "INITIALIZE / REPAIR FULL KALI"
        )
        self.status.setText(
            text
        )

        self.status.setStyleSheet(
            style
        )

    def launch_terminal_command(
        self,
        args,
    ):
        if not shutil_which(
            "konsole"
        ):
            QMessageBox.warning(
                self,
                "Kali Bay",
                "Konsole is not installed.",
            )

            return

        subprocess.Popen(
            [
                "konsole",
                "--hold",
                "-e",
            ]
            + [
                str(item)
                for item in args
            ],
            start_new_session=True,
        )

    def setup_kali(self):
        self.launch_terminal_command(
            [
                MANAGER,
                "setup",
            ]
        )

    def update_kali(self):
        self.launch_terminal_command(
            [
                MANAGER,
                "update",
            ]
        )

    def open_terminal(self):
        subprocess.Popen(
            [
                str(MANAGER),
                "terminal",
            ],
            start_new_session=True,
        )

    def open_tool(self, tool_id):
        # Read-only preflight: no implicit Distrobox initialization, apt,
        # host changes, network scans, or background SOC services.
        try:
            result = subprocess.run(
                [str(MANAGER), "tool-check", tool_id],
                capture_output=True,
                text=True,
                check=False,
                timeout=12,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            QMessageBox.warning(
                self, "Kali Bay", f"Tool check failed: {exc}"
            )
            return

        if result.returncode != 0:
            message = (
                result.stderr.strip()
                or result.stdout.strip()
                or "The tool is unavailable in the running Kali container."
            )
            QMessageBox.information(self, "Kali Bay", message)
            return

        try:
            subprocess.Popen(
                [str(MANAGER), "tool", tool_id],
                start_new_session=True,
            )
        except OSError as exc:
            QMessageBox.warning(
                self, "Kali Bay", f"Could not open tool: {exc}"
            )

    def open_category(
        self,
        package,
        title,
    ):
        if (
            self.manager_status()
            != "ready"
        ):
            QMessageBox.information(
                self,
                "Kali Bay",
                "Initialize the full Kali "
                "toolset first.",
            )

            return

        subprocess.Popen(
            [
                str(MANAGER),
                "category",
                package,
                title,
            ],
            start_new_session=True,
        )


def shutil_which(command):
    from shutil import which

    return which(command)


def main():
    app = QApplication(
        sys.argv
    )

    app.setApplicationName(
        "Kali Bay"
    )

    window = KaliBayWindow()

    window.show()

    sys.exit(
        app.exec_()
    )


if __name__ == "__main__":
    main()
