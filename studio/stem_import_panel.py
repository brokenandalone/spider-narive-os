"""Spider Audio Studio: native import of real WAV stems into verified sessions.

No terminal, recording device, file overwrite, external DAW, or source edit.
Copies owner-chosen independent PCM WAVs into a private hashed session folder.
"""
from __future__ import annotations
from pathlib import Path
import re
import threading
from PyQt5.QtCore import Qt,QThread,pyqtSignal
from PyQt5.QtWidgets import (
    QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QFileDialog,
    QTableWidget,QTableWidgetItem,QAbstractItemView,QComboBox,QLineEdit,
    QSpinBox,QCheckBox,QMessageBox)
try:
    from .multitrack import export_session,SessionError,ROLES,MAX_TRACKS,_probe
    from .session_mix_dialog import SessionMixDialog
except ImportError:
    from multitrack import export_session,SessionError,ROLES,MAX_TRACKS,_probe
    from session_mix_dialog import SessionMixDialog


def infer_role(filename):
    """Suggest conventional file roles; owner must verify dropdown choice."""
    name=Path(filename).stem.casefold().replace("_"," ").replace("-"," ")
    if re.search(r"\b(voice|vocals?|singer)\b",name):
        return "lead_vocal"
    if re.search(r"\bbass\b",name):
        return "bass"
    if re.search(r"\b(drums?|percussion)\b",name):
        return "drums"
    if re.search(r"\b(piano|keys?|keyboard)\b",name):
        return "piano_keys"
    # Broken Sorrow instrument stems identify guitar roles with either
    # "Rhythm_L"/"Rhythm_R" or full "Rhythm_Guitar" labels.
    if re.search(r"\b(rhythm|rhyth|rhy)\b",name):
        return "rhythm_guitar"
    if re.search(r"\b(lead|solo)\b",name):
        return "lead_guitar"
    return "other_instrument"


def prepare_tracks(paths,roles=None):
    """Validate selected sources before starting the asynchronous copy."""
    if not isinstance(paths,(list,tuple)) or not 1<=len(paths)<=MAX_TRACKS:
        raise SessionError("Choose 1–24 unique source WAVs.")
    roles=roles if roles is not None else [infer_role(p) for p in paths]
    if not isinstance(roles,(list,tuple)) or len(roles)!=len(paths):
        raise SessionError("Every imported WAV needs its own instrument role.")
    entries=[]
    seen=set()
    for path,role in zip(paths,roles):
        if type(role) is not str or role not in ROLES:
            raise SessionError("Select a supported track role.")
        source,metadata,details=_probe(path)
        if source in seen:
            raise SessionError("The same WAV cannot be imported twice.")
        seen.add(source)
        # Do not expose external folder paths in printed Studio status.
        entries.append({
            "path":str(source),"role":role,
            "label":source.stem[:100]})
    return entries


class StemImportWorker(QThread):
    created=pyqtSignal(str,str)
    def __init__(self,items,title,tempo,parent=None):
        super().__init__(parent)
        self.items=items
        self.title=title
        self.tempo=tempo
        self.stop=threading.Event()

    def run(self):
        try:
            location=export_session(
                self.items,title=self.title,tempo_bpm=self.tempo,
                stop=self.stop)
            if not self.stop.is_set():
                self.created.emit(str(location),"")
            else:
                self.created.emit("","Import cancelled. No existing WAV was modified.")
        except (SessionError,OSError,ValueError,RuntimeError) as exc:
            self.created.emit("",str(exc)[:260])


class StemImportPanel(QWidget):
    """End-to-end owner-driven WAV-to-native-mixer workflow."""
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setObjectName("spiderStemImport")
        self.worker=None
        self.items=[]
        self.last_session=None
        self.last_mixer=None
        self.setStyleSheet("""
            #spiderStemImport {background:#130d21;color:#f0e9fc}
            QTableWidget {background:#201830;color:#eee2fa;border:1px solid #635187}
            QLineEdit,QComboBox,QSpinBox {background:#302448;color:#faf4ff;
                border:1px solid #7455a4;padding:5px}
        """)
        box=QVBoxLayout(self)
        title=QLabel("SPIDER AUDIO STUDIO  /  IMPORT REAL AUDIO STEMS")
        title.setStyleSheet("font-size:20px;font-weight:bold;color:#c5a7ff")
        box.addWidget(title)
        note=QLabel(
            "Choose up to 24 real WAV recordings or instrument tracks. "
            "Assign a role to each, create a NEW private multitrack session, "
            "then open the actual Spider Mixer. No recordings are overwritten.")
        note.setWordWrap(True)
        box.addWidget(note)
        project=QHBoxLayout()
        project.addWidget(QLabel("Song"))
        self.song=QLineEdit()
        self.song.setPlaceholderText("Broken Sorrow - What the Silence Kept")
        self.song.setMaxLength(120)
        project.addWidget(self.song,1)
        project.addWidget(QLabel("BPM"))
        self.tempo=QSpinBox()
        self.tempo.setRange(30,300)
        self.tempo.setValue(96)
        project.addWidget(self.tempo)
        box.addLayout(project)
        commands=QHBoxLayout()
        self.add_button=QPushButton("＋ Choose WAV tracks")
        self.add_button.clicked.connect(self.add_files)
        commands.addWidget(self.add_button)
        self.remove_button=QPushButton("Remove selected")
        self.remove_button.clicked.connect(self.remove_selected)
        commands.addWidget(self.remove_button)
        self.clear_button=QPushButton("Clear selection")
        self.clear_button.clicked.connect(self.clear_files)
        commands.addWidget(self.clear_button)
        box.addLayout(commands)
        self.table=QTableWidget(0,3)
        self.table.setHorizontalHeaderLabels(("File","Role","Format"))
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setColumnWidth(0,370)
        self.table.setColumnWidth(1,185)
        self.table.setColumnWidth(2,200)
        box.addWidget(self.table,1)
        footer=QHBoxLayout()
        self.import_button=QPushButton("Create New Multitrack Session")
        self.import_button.clicked.connect(self.create_session)
        footer.addWidget(self.import_button)
        self.cancel_button=QPushButton("Cancel Import")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_import)
        footer.addWidget(self.cancel_button)
        self.mixer_button=QPushButton("Open Session in Spider Mixer")
        self.mixer_button.setEnabled(False)
        self.mixer_button.clicked.connect(self.open_mixer)
        footer.addWidget(self.mixer_button)
        box.addLayout(footer)
        self.status=QLabel("Select WAV tracks to start. PCM mono/stereo files only.")
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.PlainText)
        box.addWidget(self.status)

    def add_files(self):
        if self.worker is not None:
            return
        filenames,_=QFileDialog.getOpenFileNames(
            self,"Select independent instrument and vocal WAVs",
            str(Path.home()/"Documents"),"PCM WAV audio (*.wav *.WAV)")
        if filenames:
            self.add_paths(filenames)

    def add_paths(self,paths):
        """Public GUI method used by the actual folder picker and tests."""
        if self.worker is not None:
            return
        try:
            existing={item["path"] for item in self.items}
            incoming=[]
            for path in paths:
                src,stat,properties=_probe(path)
                if str(src) in existing:
                    continue
                incoming.append({
                    "path":str(src),"role":infer_role(src.name),
                    "label":src.stem[:100],
                    "format":f"{properties['sample_rate']} Hz / "
                             f"{properties['channels']} ch / "
                             f"{properties['sample_width_bytes']*8}-bit"})
                existing.add(str(src))
            if len(self.items)+len(incoming)>MAX_TRACKS:
                raise SessionError("Import supports up to 24 different WAVs.")
            self.items.extend(incoming)
            self.refresh_table()
            self.status.setText(
                f"{len(self.items)} tracks selected. Verify each role before creating a session.")
        except (OSError,ValueError,SessionError) as exc:
            self.status.setText("Cannot add WAV: "+str(exc)[:260])

    def refresh_table(self):
        self.table.setRowCount(len(self.items))
        for idx,item in enumerate(self.items):
            self.table.setItem(idx,0,QTableWidgetItem(Path(item["path"]).name))
            selector=QComboBox()
            for role in ROLES:
                selector.addItem(role.replace("_"," ").title(),role)
            position=selector.findData(item["role"])
            selector.setCurrentIndex(max(0,position))
            selector.currentIndexChanged.connect(
                lambda _index,row=idx:self._set_role(row))
            self.table.setCellWidget(idx,1,selector)
            self.table.setItem(idx,2,QTableWidgetItem(item["format"]))
        self.mixer_button.setEnabled(self.last_session is not None)

    def _set_role(self,row):
        if 0<=row<len(self.items):
            widget=self.table.cellWidget(row,1)
            if widget is not None:
                self.items[row]["role"]=widget.currentData()

    def remove_selected(self):
        if self.worker is not None:
            return
        selected=sorted({cell.row() for cell in self.table.selectedItems()},reverse=True)
        for index in selected:
            del self.items[index]
        self.refresh_table()

    def clear_files(self):
        if self.worker is not None:
            return
        self.items.clear()
        self.refresh_table()

    def create_session(self):
        if self.worker is not None:
            return
        try:
            tracks=prepare_tracks(
                [item["path"] for item in self.items],
                [item["role"] for item in self.items])
            title=self.song.text().strip()
            if not title:
                raise SessionError("Enter a song title before exporting the session.")
            self.worker=StemImportWorker(tracks,title,self.tempo.value(),self)
            self.worker.created.connect(self.session_created)
            self.worker.finished.connect(self.worker_finished)
            self.last_session=None
            self.mixer_button.setEnabled(False)
            for button in (self.add_button,self.remove_button,
                           self.clear_button,self.import_button):
                button.setEnabled(False)
            self.cancel_button.setEnabled(True)
            self.status.setText("Copying verified audio into a new private session...")
            self.worker.start()
        except (OSError,ValueError,SessionError) as exc:
            self.status.setText("Cannot create session: "+str(exc)[:260])

    def session_created(self,folder,error):
        if folder:
            self.last_session=Path(folder)
            self.mixer_button.setEnabled(True)
            self.status.setText(
                f"Verified new session: {self.last_session.name}. "
                "Click Open Session in Spider Mixer to edit and hear it.")
        else:
            self.status.setText("Import did not complete: "+error)

    def worker_finished(self):
        current=self.worker
        self.worker=None
        if current is not None:
            current.deleteLater()
        for button in (self.add_button,self.remove_button,
                       self.clear_button,self.import_button):
            button.setEnabled(True)
        self.cancel_button.setEnabled(False)

    def cancel_import(self):
        if self.worker is not None:
            self.worker.stop.set()
            self.status.setText(
                "Cancelling copy. Original recordings remain unchanged.")

    def open_mixer(self):
        if self.worker is not None or self.last_session is None:
            return
        if not self.last_session.is_dir() or self.last_session.is_symlink():
            self.status.setText("Session folder is missing or unsafe.")
            return
        mixer=SessionMixDialog(str(self.last_session),self)
        self.last_mixer=mixer
        mixer.exec_()

    def closeEvent(self,event):
        if self.worker is not None and self.worker.isRunning():
            self.worker.stop.set()
            self.status.setText("Finishing cancellation before closing the importer.")
            event.ignore()
            return
        super().closeEvent(event)
