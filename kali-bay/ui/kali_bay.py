#!/usr/bin/env python3

import os
import subprocess
import sys
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPixmap,
)
from PyQt5.QtWidgets import (
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QComboBox,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
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


class KaliBayWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self._wallpaper = None

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
        self.load_wallpaper()
        self.refresh_status()
        if "--purple" in sys.argv[1:]:
            self.security_tabs.setCurrentIndex(2)
        elif "--offensive" in sys.argv[1:]:
            self.security_tabs.setCurrentIndex(1)

    def build_ui(self):
        self.setStyleSheet(
            """
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
                padding: 12px 20px;
                min-width: 155px;
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
        self.desktop_list = QListWidget()
        self.desktop_list.setObjectName("kaliDesktopToolList")
        self.desktop_list.setStyleSheet(
            "QListWidget {background:rgba(12,7,24,215);color:#f3e8ff;"
            "border:1px solid #7645a6;border-radius:8px;}"
            "QListWidget::item {padding:9px;}"
            "QListWidget::item:selected {background:#5b21b6;}"
        )
        self.desktop_list.itemDoubleClicked.connect(
            lambda item: self.open_tool(item.data(Qt.UserRole))
        )
        left.addWidget(self.desktop_list, 1)
        launch = QPushButton("OPEN SELECTED TOOL")
        launch.setObjectName("kaliDesktopLaunchTool")
        launch.clicked.connect(self.open_selected_desktop_tool)
        left.addWidget(launch)
        layout.addWidget(menu, 2)

        actions = QWidget()
        actions.setObjectName("kaliDesktopQuickActions")
        right = QVBoxLayout(actions)
        right.setSpacing(12)
        hero = QLabel("KALI × SPIDER")
        hero.setStyleSheet("font-size:24px;font-weight:bold;color:#c084fc;")
        right.addWidget(hero)
        about = QLabel(
            "Kali-style security environment, powered by the existing "
            "Kali Distrobox container. The desktop, wallpaper and assistant "
            "belong to Spider OS. This is not a separate Kali XFCE session."
        )
        about.setWordWrap(True)
        right.addWidget(about)
        for caption, operation in (
            ("KALI TERMINAL", self.open_terminal),
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
        layout.addWidget(actions, 3)
        self.filter_desktop_tools()
        return page

    def filter_desktop_tools(self, *_args):
        query = self.desktop_search.text().strip().casefold()
        category = self.desktop_category.currentText()
        self.desktop_list.clear()
        for group, label, tool_id in DESKTOP_TOOL_MENU:
            if category != "All categories" and group != category:
                continue
            if query and query not in (group + " " + label).casefold():
                continue
            item = QListWidgetItem(f"{group}  /  {label}")
            item.setData(Qt.UserRole, tool_id)
            self.desktop_list.addItem(item)
        if self.desktop_list.count():
            self.desktop_list.setCurrentRow(0)

    def open_selected_desktop_tool(self):
        item = self.desktop_list.currentItem()
        if item is None:
            QMessageBox.information(self, "Kali Bay", "Select a tool first.")
            return
        self.open_tool(item.data(Qt.UserRole))

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
        # The Web owns one persistent Webbie panel; never start a duplicate
        # resident voice agent or bypass the main shell's consent checks.
        parent = self.parentWidget()
        while parent is not None:
            if hasattr(parent, "open_kali_assistant"):
                parent.open_kali_assistant()
                return
            if hasattr(parent, "toggle_webbie_assistant"):
                parent.update_webbie_context()
                dock = getattr(parent, "webbie_dock", None)
                if dock is not None and dock.isVisible():
                    dock.raise_()
                else:
                    parent.toggle_webbie_assistant()
                return
            parent = parent.parentWidget()
        QMessageBox.information(
            self, "Webbie",
            "Open Kali Bay inside The Web and use Ask Webbie. "
            "The standalone Kali window does not start a second Webbie."
        )

    def build_category_page(self, categories, description):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)

        note = QLabel(description)
        note.setWordWrap(True)
        note.setStyleSheet("color:#c7b9d2;padding:5px 0 12px;")
        layout.addWidget(note)

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
