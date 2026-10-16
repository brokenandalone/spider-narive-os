"""Spider OS Home: living map of the actual native bays, not an app launcher.

The Universal/MAX control centers are no longer required to find projects,
advanced analysis or the proper installed Ubuntu Studio program. Navigation
only opens native bay tabs already part of The Web, never new executables.
"""
from __future__ import annotations

from collections import Counter

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QApplication, QFrame, QGridLayout, QLabel, QPushButton,
                              QScrollArea, QVBoxLayout, QWidget)

from app_catalog import VISIBLE_WORKSPACES
from bay_missions import MissionStore, BLUEPRINTS

PURPOSES = {
    "webbie": "Resident intelligence, research, voice, privacy and owner-controlled JARVIS operations",
    "studio": "Record, play instruments, program drums, mix and publish original music",
    "author": "Write novels, inspect canon, manage chapters and enter Broken World",
    "study": "Learn, complete coursework, organize reference materials and prepare APA work",
    "art-lab": "Draw, paint, make photo outlines and build cinematic visual artwork",
    "media": "Watch films, manage your music and run BCN radio with Nova",
    "kali-bay": "Use your authorized security laboratory and document findings",
    "forage": "Gather sources, search and verify information",
    "deep-forage": "Compare evidence and pursue deeper scientific or creative research",
    "dev-bay": "Build and verify Spider OS source changes and software projects",
    "communications": "Draft messages and connect approved communications services",
    "productivity": "Review priorities and move work between native bays",
    "devices": "Inspect cameras, keyboards, audio interfaces and connected hardware",
    "system": "Inspect health, backups, rollback checkpoints and recovery status",
}


def dashboard_rows(missions, installed_apps):
    """Pure summary for UI and tests; no files or programs are opened."""
    tally = Counter()
    for item in missions:
        if (isinstance(item, dict) and item.get("bay") in PURPOSES
                and item.get("status") not in ("done",)):
            tally[item["bay"]] += 1
    installed = Counter()
    for app in installed_apps:
        bay = getattr(app, "workspace", None)
        if bay in PURPOSES:
            installed[bay] += 1
    return [
        {
            "bay": ident,
            "name": BLUEPRINTS[ident][0],
            "purpose": PURPOSES[ident],
            "missions": tally[ident],
            "programs": installed[ident],
        }
        for ident in VISIBLE_WORKSPACES if ident in PURPOSES
    ]

def focus_queue(missions, limit=6):
    """Stable, bounded queue of pending cross-bay work, without reading folders."""
    if type(limit) is not int or not 1 <= limit <= 20:
        raise ValueError("Queue limit must be 1..20")
    priority = {"blocked": 0, "active": 1, "next": 2}
    selected = []
    for index, item in enumerate(missions):
        if not isinstance(item, dict):
            continue
        bay, status = item.get("bay"), item.get("status")
        title = item.get("title")
        if (bay not in PURPOSES or status not in priority
                or not isinstance(title, str) or not title.strip()):
            continue
        selected.append((priority[status], index, {
            "bay": bay, "status": status, "title": title[:140],
            "bay_name": BLUEPRINTS[bay][0],
        }))
    selected.sort(key=lambda entry: (entry[0], entry[1]))
    return [row for _priority, _index, row in selected[:limit]]

def mission_brief(missions, *, limit=20):
    """Owner-requested plaintext handoff; never includes paths or IDs."""
    if type(limit) is not int or not 1 <= limit <= 20:
        raise ValueError("Brief limit must be 1..20")
    lines = ["SPIDER OS / MISSION BRIEF", "Blocked work first; private paths excluded."]
    items = focus_queue(missions, limit=limit)
    if not items:
        lines.append("No unfinished missions.")
    for item in items:
        title = " ".join(item["title"].split())
        lines.append(f'[{item["status"].upper()}] {item["bay_name"]}: {title}')
    return "\n".join(lines)


class SpiderHomeDashboard(QWidget):
    def __init__(self, workspace_opener, installed_supplier, parent=None, store=None):
        super().__init__(parent)
        self.setObjectName("spiderNativeHomeDashboard")
        self.workspace_opener = workspace_opener
        self.installed_supplier = installed_supplier
        self.store = store if store is not None else MissionStore()
        self.buttons = {}
        self.summaries = {}
        root = QVBoxLayout(self)
        header = QLabel("YOUR LIFE. ONE WEB.")
        header.setStyleSheet(
            "font-size:27px;font-weight:bold;color:#dfc5ff")
        root.addWidget(header)
        description = QLabel(
            "These are native Spider OS workspaces, not another set of launchers. "
            "Enter the real bay to use its projects, Webbie, instruments, advanced "
            "analysis and all available Ubuntu Studio programs.")
        description.setWordWrap(True)
        root.addWidget(description)
        self.status = QLabel("")
        root.addWidget(self.status)
        refresh = QPushButton("Refresh workspaces and installed tools")
        refresh.clicked.connect(self.refresh)
        root.addWidget(refresh)
        focus_title = QLabel("MISSION CONTROL  /  WHAT NEEDS ATTENTION")
        focus_title.setStyleSheet("font-weight:bold;color:#dcb8ff")
        root.addWidget(focus_title)
        self.focus_status = QLabel("No pending missions.")
        self.focus_status.setWordWrap(True)
        root.addWidget(self.focus_status)
        brief_button = QPushButton("Copy Mission Brief (no project paths)")
        brief_button.setToolTip("Copies unfinished mission titles only, on your command.")
        brief_button.clicked.connect(self.copy_mission_brief)
        root.addWidget(brief_button)
        self.focus_buttons = []
        for _ in range(6):
            focus_button = QPushButton("")
            focus_button.hide()
            root.addWidget(focus_button)
            self.focus_buttons.append(focus_button)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        contents = QWidget()
        grid = QGridLayout(contents)
        grid.setSpacing(12)
        for position, bay in enumerate(PURPOSES):
            row, col = divmod(position, 3)
            card = QFrame()
            card.setObjectName("spiderHomeBayCard")
            card.setStyleSheet(
                "QFrame#spiderHomeBayCard {background:#1d1428;"
                "border:1px solid #7848a8;border-radius:10px;"
                "padding:8px;}")
            stack = QVBoxLayout(card)
            label = QLabel(BLUEPRINTS[bay][0].upper())
            label.setStyleSheet("font-weight:bold;color:#dcb8ff")
            stack.addWidget(label)
            purpose = QLabel(PURPOSES[bay])
            purpose.setWordWrap(True)
            stack.addWidget(purpose, 1)
            status = QLabel("")
            status.setWordWrap(True)
            self.summaries[bay] = status
            stack.addWidget(status)
            button = QPushButton("Enter " + BLUEPRINTS[bay][0])
            button.clicked.connect(
                lambda checked=False, selected=bay: self.workspace_opener(selected))
            self.buttons[bay] = button
            stack.addWidget(button)
            grid.addWidget(card, row, col)
        scroll.setWidget(contents)
        root.addWidget(scroll, 1)
        self.refresh()

    def copy_mission_brief(self):
        try:
            contents = mission_brief(self.store.read())
        except (ValueError, OSError):
            self.status.setText("Could not read missions. Clipboard unchanged.")
            return
        clipboard = QApplication.clipboard()
        if clipboard is None:
            self.status.setText("Clipboard is unavailable.")
            return
        clipboard.setText(contents)
        self.status.setText("Mission brief copied. No linked folder paths or IDs included.")

    def refresh(self):
        try:
            missions = self.store.read()
            self.status.setText("Workspaces loaded. Project count is local-only.")
        except (ValueError, OSError):
            missions = []
            self.status.setText(
                "Project list unavailable. All native bays remain accessible.")
        try:
            applications = self.installed_supplier()
        except (ValueError, OSError, TypeError):
            applications = []
        focus = focus_queue(missions)
        self.focus_status.setText(
            f"{len(focus)} priorities shown. Blocked work appears first."
            if focus else "No pending missions. Open a bay to create one.")
        for index, button in enumerate(self.focus_buttons):
            try:
                button.clicked.disconnect()
            except (TypeError, RuntimeError):
                pass
            if index >= len(focus):
                button.hide()
                continue
            item = focus[index]
            button.setText(
                f'[{item["status"].upper()}] {item["bay_name"]}: {item["title"]}')
            button.clicked.connect(
                lambda checked=False, bay=item["bay"]: self.workspace_opener(bay))
            button.show()
        rows = dashboard_rows(missions, applications)
        for row in rows:
            self.summaries[row["bay"]].setText(
                "{} unfinished missions · {} installed tool entries".format(
                    row["missions"], row["programs"]))
