"""Run Workspace MAX's proven read-only operations INSIDE existing native bays.

No MAX launcher, separate window, subprocess action, network request, or OS
installation. The approved v4 analysis code is used as a library. In the
self-contained release it lives at spider_max_source/spider_monster; until that
source is vendored, the same verified v4 ZIP can supply it privately.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import threading
import zipfile

from PyQt5.QtCore import QThread, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMessageBox, QPushButton,
    QTextEdit, QVBoxLayout, QWidget, QInputDialog,
)

WORKSPACE_TO_MAX = {
    "default": "The Web", "webbie": "Webbie",
    "forage": "Forage", "deep-forage": "Forage",
    "studio": "Studio", "author": "Author",
    "study": "Study", "art-lab": "Art Lab",
    "media": "Media Center", "communications": "Communications",
    "kali-bay": "Kali Bay", "dev-bay": "Dev Bay",
    "system": "System", "recovery": "Recovery",
}
V4_SHA256 = "ac9af96ea33201817a43190d4cc622621f386002bae79b493ac068625e1cf391"
V4_NAMES = (
    "max_catalog.py", "max_core.py", "max_board.py", "security.py",
    "max_author.py", "max_study.py", "max_studio.py", "max_media.py",
    "max_art.py", "max_forage.py", "max_dev.py", "max_kali.py",
    "max_webbie.py", "max_theweb.py", "max_nova.py", "max_comms.py",
    "max_recovery.py", "max_system.py", "max_backups.py",
)
V4_BLOB_SHA256 = {
    "max_catalog.py": "5fcdc5f8fdf98c0993f91a316f083dcace0a37805960e770a9b4311c6d048c6b",
    "max_core.py": "305a96d45f1b1c5722658d45f0c9b59f1b16ea07387faae918fdd1ab1858736b",
    "max_board.py": "062595156dcdd0e7ecebe3da3761b23a7d7c355828b9be4768ea9628a951a2fa",
    "security.py": "55e69d78dcdb6f7eafc4388ec7c560146c04145aa3dd1e9d943dc1e9b55c1c4b",
    "max_author.py": "1d071cab6e684b9cd8435e106c0e88141335dc0893c15ad1444761c52aa4b0e8",
    "max_study.py": "c5e965e11d7787fe6d13b5367257be96d4b133a9d49f76d66d7fc7b29f3b9378",
    "max_studio.py": "e218f9db4fed27b46ed8b2737f1b8ce5a81f024e7c5e2b469b023cc4a193b0ef",
    "max_media.py": "52fef17446f8e7d54db24178084a1068d8ac1679c240718936099dc427e05acd",
    "max_art.py": "df35770e4065cdeb89b68cb4d2f1ab63668b78ed60aeb80ead82092790722820",
    "max_forage.py": "c39052f31522a6503274e380594e99e49650e10cadc27e43c0ee0b900cffe7c5",
    "max_dev.py": "9ed6ae82ef3c1e1de530f31931c711d1fea271be77eb24a1f2541da94451dd06",
    "max_kali.py": "bcc2dedf6a432b58af52c1b5cece32d46afeda863f5361c866fa201563b05f81",
    "max_webbie.py": "a68fb542191247ed6895f3b92fdd8b5f2c0ef8236790a558d1c4e77eec4cbe37",
    "max_theweb.py": "57fe3d444d3e270e3ebe38354ba068a8c568eec1808c544fe062a89934f5b273",
    "max_nova.py": "158ba3cbe23419cdddd8f72d0f6183a1d46bf1f192fb05a14d24f8d19a498383",
    "max_comms.py": "a78745974735a6d87da8408a4d0e1f6d25e8ec967d822c7a790a3913af1e53b4",
    "max_recovery.py": "ce27e7b437a43a6c7e534eea880fde3d329fc4c946a567e2eb1c3cfac3e7b4e1",
    "max_system.py": "8fee883afe23ad97618adc4bc2dd57c6542af1a736130efaadfd783d07ef8fca",
    "max_backups.py": "e3e94037be10eaab7573e4f79e4b141735503cc9c81524d861327ae939ea5cc1",
}
_PACKAGE = None
_PACKAGE_LOCK = threading.Lock()


def _sha_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(128 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verified_source():
    """Use only exact reviewed v4 code, never arbitrary Downloads Python."""
    root = Path(__file__).resolve().parents[2]
    candidates = [
        root / "spider_max_source",  # source-vendored native release
        Path.home() / ".local/share/spider-os/intelligence-center/2026.10-workspace-max-v4",
        Path.home() / "Downloads/Spider_OS_Workspace_MAX_v4",
        Path.home() / "Downloads/Spider_OS_2026_10_WORKSPACE_MAX_v4.zip",
    ]
    for candidate in candidates:
        if candidate.is_symlink() or not candidate.exists():
            continue
        if candidate.is_dir():
            package_dir = candidate / "spider_monster"
            if package_dir.is_symlink() or not package_dir.is_dir():
                continue
            if all(
                (not (package_dir / name).is_symlink()) and
                (package_dir / name).is_file() and
                _sha_file(package_dir / name) == V4_BLOB_SHA256[name]
                for name in V4_NAMES
            ):
                return str(candidate)
        elif candidate.is_file() and candidate.suffix.lower() == ".zip":
            if _sha_file(candidate) != V4_SHA256:
                continue
            # The whole archive hash pins the content exactly, including every
            # embedded module. The source was reviewed from this exact ZIP.
            return str(candidate)
    return None


def load_max_catalog():
    global _PACKAGE
    with _PACKAGE_LOCK:
        if _PACKAGE is not None:
            return _PACKAGE
        source = _verified_source()
        if source is None:
            return None
        if "spider_monster" in sys.modules:
            # Do not accidentally use a different already-imported package.
            loaded = getattr(sys.modules["spider_monster"], "__file__", "") or ""
            if not str(loaded).startswith(source):
                return None
        if source not in sys.path:
            sys.path.insert(0, source)
        module = importlib.import_module("spider_monster.max_catalog")
        _PACKAGE = module
        return _PACKAGE


def available_operations(workspace):
    catalog = load_max_catalog()
    name = WORKSPACE_TO_MAX.get(workspace)
    if catalog is None or name is None:
        return ()
    module = catalog.WORKSPACES.get(name)
    return tuple(module.ACTIONS) if module else ()


class OperationWorker(QThread):
    result_ready = pyqtSignal(object)

    def __init__(self, workspace, action, folder, query, parent=None):
        super().__init__(parent)
        self.workspace = workspace
        self.action = action
        self.folder = folder
        self.query = query

    def run(self):
        try:
            catalog = load_max_catalog()
            if catalog is None:
                raise RuntimeError("Verified MAX source unavailable")
            result = catalog.run(self.workspace, self.action, self.folder, self.query)
            self.result_ready.emit({"ok": True, "result": result})
        except Exception as error:
            self.result_ready.emit({"ok": False, "error": str(error)[:350]})


class NativeWorkspaceTools(QWidget):
    """A real tab WITHIN an existing bay; no standalone MAX UI is invoked."""

    def __init__(self, workspace, parent=None):
        super().__init__(parent)
        self.workspace = workspace
        self.workspace_title = WORKSPACE_TO_MAX.get(workspace)
        if not self.workspace_title:
            raise ValueError("Workspace does not have MAX actions")
        self.worker = None
        self.setObjectName("spiderNativeWorkspaceTools")
        layout = QVBoxLayout(self)
        heading = QLabel(self.workspace_title.upper() + " / ADVANCED WORKSPACE TOOLS")
        heading.setStyleSheet("color:#cbb5fc; font-size:17px; font-weight:bold")
        layout.addWidget(heading)
        self.explanation = QLabel(
            "Run the advanced analysis tools right here in this bay. "
            "Choose which local folder to inspect. Reports are advisory and read-only.")
        self.explanation.setWordWrap(True)
        layout.addWidget(self.explanation)
        row = QHBoxLayout(); layout.addLayout(row)
        self.action = QComboBox()
        self.action.setAccessibleName("Native " + self.workspace_title + " operation")
        row.addWidget(self.action, 1)
        self.folder = QLineEdit(); self.folder.setReadOnly(True)
        self.folder.setPlaceholderText("Selected local project folder")
        row.addWidget(self.folder, 2)
        browse = QPushButton("Choose folder")
        browse.clicked.connect(self.choose_folder)
        row.addWidget(browse)
        row = QHBoxLayout(); layout.addLayout(row)
        self.query = QLineEdit()
        self.query.setPlaceholderText("Optional search terms or filters")
        row.addWidget(self.query, 2)
        self.run_button = QPushButton("Analyze in this bay")
        self.run_button.clicked.connect(self.run_action)
        row.addWidget(self.run_button)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.results = QTextEdit()
        self.results.setReadOnly(True)
        layout.addWidget(self.results, 1)
        self.board = QListWidget()
        self.board.setAccessibleName(self.workspace_title + " tasks and notes")
        layout.addWidget(QLabel("WORKSPACE TASKS AND NOTES"))
        layout.addWidget(self.board, 1)
        actions = QHBoxLayout(); layout.addLayout(actions)
        add_note = QPushButton("Add private note")
        add_note.clicked.connect(lambda: self.add_board_item("note"))
        actions.addWidget(add_note)
        add_task = QPushButton("Add task")
        add_task.clicked.connect(lambda: self.add_board_item("task"))
        actions.addWidget(add_task)
        complete = QPushButton("Complete selected")
        complete.clicked.connect(self.complete_board_item)
        actions.addWidget(complete)
        self.reload()

    def _board_file(self):
        return Path.home() / ".local/share/spider-os/monster/workspace_max_boards.sqlite3"

    def _board_access(self):
        catalog = load_max_catalog()
        if catalog is None:
            return None
        return importlib.import_module("spider_monster.max_board").WorkspaceBoard

    def reload(self):
        operations = available_operations(self.workspace)
        self.action.clear()
        for operation in operations:
            self.action.addItem(operation.replace("-", " ").title(), operation)
        self.run_button.setEnabled(bool(operations))
        if operations:
            self.status.setText(
                str(len(operations)) + " verified MAX operations are ready in this native bay.")
        else:
            self.status.setText(
                "Advanced analysis source is not bundled yet. "
                "Keep the existing native tools; install/source-vendor the reviewed v4 "
                "backend to enable these operations. No extra launcher is needed.")
        self.refresh_board()

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Choose folder for " + self.workspace_title, str(Path.home()))
        if folder:
            self.folder.setText(folder)

    def run_action(self):
        if self.worker is not None and self.worker.isRunning():
            return
        if not self.folder.text():
            self.status.setText("Select an existing project folder first.")
            return
        action = self.action.currentData()
        if not action:
            self.status.setText("This bay's advanced analysis source is not available.")
            return
        self.run_button.setEnabled(False)
        self.status.setText("Analyzing selected files without modifying them...")
        self.worker = OperationWorker(
            self.workspace_title, action, self.folder.text(), self.query.text(), self)
        self.worker.result_ready.connect(self.finish_action)
        self.worker.finished.connect(self.worker_finished)
        self.worker.start()

    def worker_finished(self):
        self.run_button.setEnabled(bool(available_operations(self.workspace)))

    def finish_action(self, response):
        if response.get("ok"):
            self.results.setPlainText(
                json.dumps(response.get("result"), indent=2, ensure_ascii=False, default=str)[:160000])
            self.status.setText("Analysis complete. No original files were modified.")
        else:
            self.results.setPlainText("Analysis unavailable: " + response.get("error", "Unknown error"))
            self.status.setText("Nothing changed.")

    def refresh_board(self):
        self.board.clear()
        Board = self._board_access()
        if Board is None:
            return
        try:
            with Board(self._board_file()) as board:
                entries = board.list(self.workspace_title)
            for entry in entries:
                item = QListWidgetItem(
                    ("✓" if entry["status"] == "done" else "○") +
                    " [" + entry["kind"] + "] " + entry["title"])
                item.setData(Qt.UserRole, entry["id"])
                item.setToolTip(entry.get("detail", "")[:500])
                self.board.addItem(item)
        except (OSError, ValueError, PermissionError) as error:
            self.status.setText("Private board unavailable: " + str(error))

    def add_board_item(self, kind):
        Board = self._board_access()
        if Board is None:
            self.status.setText("Verified board module not yet available.")
            return
        title, ok = QInputDialog.getText(self, "New " + kind, "Title")
        if not ok or not title.strip():
            return
        detail, ok = QInputDialog.getMultiLineText(self, "Optional details", "Details")
        if not ok:
            return
        try:
            with Board(self._board_file()) as board:
                board.add(self.workspace_title, title, detail, kind)
            self.refresh_board()
        except (OSError, ValueError, PermissionError) as error:
            self.status.setText("Could not save note: " + str(error))

    def complete_board_item(self):
        item = self.board.currentItem()
        Board = self._board_access()
        if item is None or Board is None:
            return
        try:
            with Board(self._board_file()) as board:
                board.set_status(item.data(Qt.UserRole), "done")
            self.refresh_board()
        except (KeyError, OSError, ValueError, PermissionError) as error:
            self.status.setText("Could not update task: " + str(error))

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            event.ignore()
        else:
            event.accept()
