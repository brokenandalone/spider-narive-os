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
            self.security_tabs.setCurrentIndex(1)
        elif "--offensive" in sys.argv[1:]:
            self.security_tabs.setCurrentIndex(0)

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
