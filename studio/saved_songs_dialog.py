"""Song library for the original Spider Audio Studio.

Only reads Spider's private export-session root. Selected items must be
checksum-verified by the existing SessionMixDialog before they can play.
"""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from PyQt5.QtCore import QThread,pyqtSignal
from PyQt5.QtWidgets import (
    QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QTableWidget,
    QTableWidgetItem,QAbstractItemView,QDialogButtonBox,QFileDialog)
try:
    from .session_library import recent_sessions
    from .session_mix_dialog import SessionMixDialog
    from .session_archive import create_backup,restore_backup
except ImportError:
    from session_library import recent_sessions
    from session_mix_dialog import SessionMixDialog
    from session_archive import create_backup,restore_backup


class SongArchiveWorker(QThread):
    complete=pyqtSignal(str,str)
    def __init__(self,action,source,target,parent=None):
        super().__init__(parent)
        self.action,self.source,self.target=action,source,target

    def run(self):
        try:
            if self.action=="backup":
                output=create_backup(self.source,self.target)
            elif self.action=="restore":
                output=restore_backup(self.source,output_root=self.target)
            else:
                raise ValueError("Unknown Studio session archive operation.")
            self.complete.emit(str(output),"")
        except (OSError,ValueError,RuntimeError) as error:
            self.complete.emit("",str(error)[:250])

class SavedSongsDialog(QDialog):
    def __init__(self,parent=None,*,root=None):
        super().__init__(parent)
        self.root=root
        self.selected_path=None
        self.mixer=None
        self.archive_worker=None
        self.setWindowTitle("Spider Audio Studio · Saved Songs")
        self.setObjectName("spiderSavedSongLibrary")
        self.resize(910,490)
        self.setStyleSheet(
            "#spiderSavedSongLibrary {background:#171027;color:#eee7ff}"
            "QTableWidget {background:#241b37;color:#f0e7fa}"
            "QPushButton {background:#362651;color:#f8edff;padding:8px}")
        box=QVBoxLayout(self)
        title=QLabel("YOUR SONGS · PROTECTED SESSION LIBRARY")
        title.setStyleSheet("font-size:19px;color:#cbb0ff;font-weight:bold")
        box.addWidget(title)
        copy=QLabel(
            "Recent Spider Audio Studio multitrack sessions are listed below. "
            "The folder inventory is read-only. Opening a song verifies the "
            "actual WAV files and their saved SHA-256 checksums before mixing. "
            "This list is not a cloud scan or a recording recovery guarantee.")
        copy.setWordWrap(True)
        box.addWidget(copy)
        self.table=QTableWidget(0,4)
        self.table.setHorizontalHeaderLabels(
            ("Song","Tracks","Tempo","Exported / changed"))
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setColumnWidth(0,400)
        self.table.setColumnWidth(1,90)
        self.table.setColumnWidth(2,90)
        self.table.setColumnWidth(3,190)
        self.table.itemDoubleClicked.connect(lambda _item:self.open_selected())
        box.addWidget(self.table,1)
        actions=QHBoxLayout()
        refresh=QPushButton("Refresh Song List")
        refresh.clicked.connect(self.refresh)
        actions.addWidget(refresh)
        self.open_button=QPushButton("Verify and Open Selected Song")
        self.open_button.clicked.connect(self.open_selected)
        actions.addWidget(self.open_button)
        browse=QPushButton("Browse for Another Session")
        browse.clicked.connect(self.browse)
        actions.addWidget(browse)
        box.addLayout(actions)
        safety=QHBoxLayout()
        self.backup_button=QPushButton("Back Up Selected Song")
        self.backup_button.clicked.connect(self.backup_selected)
        safety.addWidget(self.backup_button)
        self.restore_button=QPushButton("Restore Song from Backup")
        self.restore_button.clicked.connect(self.restore_selected)
        safety.addWidget(self.restore_button)
        box.addLayout(safety)
        self.message=QLabel("Open a saved song to continue editing in the native mixer.")
        self.message.setWordWrap(True)
        box.addWidget(self.message)
        close=QDialogButtonBox(QDialogButtonBox.Close)
        close.rejected.connect(self.reject)
        box.addWidget(close)
        self.refresh()

    def refresh(self):
        self.candidates=recent_sessions(self.root)
        self.table.setRowCount(len(self.candidates))
        for row,item in enumerate(self.candidates):
            columns=[
                item["title"],str(item["track_count"]),
                f'{item["bpm"]} BPM' if item["bpm"] else "Unspecified",
                datetime.fromtimestamp(
                    item["modified_ns"]/1_000_000_000).strftime("%Y-%m-%d %H:%M"),
            ]
            for col,value in enumerate(columns):
                self.table.setItem(row,col,QTableWidgetItem(value))
        if self.candidates:
            self.table.setCurrentCell(0,0)
            self.message.setText(
                f"{len(self.candidates)} recent saved songs found. "
                "Choose one to verify.")
        else:
            self.message.setText(
                "No saved sessions found in the default Studio session library. "
                "Use Browse for Another Session if your song is stored elsewhere.")
        self.open_button.setEnabled(bool(self.candidates))
        self.backup_button.setEnabled(
            bool(self.candidates) and self.archive_worker is None)

    def _run_archive(self,action,source,target):
        if self.archive_worker is not None:
            return
        self.archive_worker=SongArchiveWorker(action,source,target,self)
        self.archive_worker.complete.connect(self._archive_done)
        self.archive_worker.finished.connect(self._archive_finished)
        self.backup_button.setEnabled(False)
        self.restore_button.setEnabled(False)
        self.open_button.setEnabled(False)
        self.message.setText("Verifying and "+(
            "backing up" if action=="backup" else "restoring")+
            " the saved song on a worker thread...")
        self.archive_worker.start()

    def backup_selected(self):
        row=self.table.currentRow()
        if self.archive_worker is not None or not 0<=row<len(self.candidates):
            return
        source=self.candidates[row]
        title="".join(
            ch if ch.isalnum() or ch in "-_ " else "_"
            for ch in source["title"])[:70].strip().replace(" ","_")
        suggested=Path.home()/"Documents"/(
            (title or "Spider_Song")+".spiderstudio.zip")
        dest,_=QFileDialog.getSaveFileName(
            self,"Save a verified Spider Song Backup",
            str(suggested),"Spider Song Backup (*.zip)")
        if dest:
            self._run_archive("backup",source["path"],dest)

    def restore_selected(self):
        if self.archive_worker is not None:
            return
        filename,_=QFileDialog.getOpenFileName(
            self,"Choose a Spider Audio Studio Song Backup",
            str(Path.home()/"Documents"),"Spider Song Backup (*.zip)")
        if filename:
            try:
                from .multitrack import DEFAULT_OUTPUT
            except ImportError:
                from multitrack import DEFAULT_OUTPUT
            root=self.root if self.root is not None else DEFAULT_OUTPUT
            self._run_archive("restore",filename,str(root))

    def _archive_done(self,output,error):
        if output:
            action=self.archive_worker.action if self.archive_worker else "backup"
            if action=="restore":
                self.message.setText(
                    "Song restored as a NEW verified Studio session. "
                    "The original session and backup remain untouched.")
                self.refresh()
            else:
                self.message.setText(
                    "Verified song backup created: "+Path(output).name+
                    ". Keep another copy somewhere safe.")
        else:
            self.message.setText("Song archive was not completed: "+error)

    def _archive_finished(self):
        current=self.archive_worker
        self.archive_worker=None
        if current is not None:
            current.deleteLater()
        self.open_button.setEnabled(bool(self.candidates))
        self.restore_button.setEnabled(True)
        self.backup_button.setEnabled(bool(self.candidates))

    def reject(self):
        if self.archive_worker is not None:
            self.message.setText(
                "Finish the active backup/restore before closing this window.")
            return
        super().reject()

    def closeEvent(self,event):
        if self.archive_worker is not None:
            self.message.setText(
                "Finish the active backup/restore before closing this window.")
            event.ignore()
            return
        super().closeEvent(event)

    def open_selected(self):
        row=self.table.currentRow()
        if not 0<=row<len(self.candidates):
            return
        self._open_path(Path(self.candidates[row]["path"]))

    def browse(self):
        folder=QFileDialog.getExistingDirectory(
            self,"Choose a verified Spider Studio session folder",
            str(Path.home()/"Documents"))
        if folder:
            self._open_path(Path(folder))

    def _open_path(self,path):
        if path.is_symlink() or not path.is_dir():
            self.message.setText("The selected project folder is missing or linked.")
            return
        self.selected_path=path
        self.mixer=SessionMixDialog(str(path),self)
        self.mixer.exec_()
