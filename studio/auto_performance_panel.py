"""Native sheet-music and tablature self-playing workspace for Spider Studio."""
from pathlib import Path
from PyQt5.QtCore import QThread,pyqtSignal
from PyQt5.QtWidgets import (
    QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QTextEdit,
    QSpinBox,QComboBox,QFileDialog,QLineEdit,QMessageBox,
)
try:
    from .score_performance import import_score_file,import_ascii_tab
    from .score_audio_render import export_performance_midi,render_soundfont,soundfont_ready
except ImportError:
    from score_performance import import_score_file,import_ascii_tab
    from score_audio_render import export_performance_midi,render_soundfont,soundfont_ready

class ScoreRenderThread(QThread):
    done=pyqtSignal(bool,str)
    def __init__(self,score,bank,destination,parent=None):
        super().__init__(parent)
        self.score,self.bank,self.destination=score,bank,destination
    def run(self):
        try:
            render_soundfont(self.score,self.bank,self.destination)
            self.done.emit(True,"Rendered sampled-instrument performance: "+Path(self.destination).name)
        except (OSError,ValueError,RuntimeError,TimeoutError) as error:
            self.done.emit(False,str(error)[:320])

class AutoPerformancePanel(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.score=None
        self.worker=None
        self.setObjectName("spiderAutoPerformance")
        self.setStyleSheet("""QWidget#spiderAutoPerformance{background:#100e1d;color:#eee3ff}
            QLabel{color:#f1e6ff} QPushButton{background:#322447;color:white;
            border:1px solid #966ac7;border-radius:6px;padding:9px}
            QTextEdit,QLineEdit,QSpinBox,QComboBox{background:#211932;color:white;
            border:1px solid #755a9c;padding:6px}""")
        root=QVBoxLayout(self)
        root.addWidget(QLabel("AUTOPLAY / SHEET MUSIC · TABS · INSTRUMENT PERFORMANCE"))
        blurb=QLabel("Import MusicXML sheet music or paste aligned guitar/bass TAB. "
            "Spider reads the notes and timing, creates a full MIDI performance, "
            "and can render sampled instruments through a SoundFont you choose. "
            "PDF/photos are not supported by this importer yet.")
        blurb.setWordWrap(True)
        root.addWidget(blurb)
        commands=QHBoxLayout()
        read=QPushButton("Import MusicXML / TAB file")
        read.clicked.connect(self.import_file)
        commands.addWidget(read)
        commands.addWidget(QLabel("TAB instrument"))
        self.instrument=QComboBox()
        self.instrument.addItems(["guitar","bass"])
        commands.addWidget(self.instrument)
        commands.addWidget(QLabel("Tempo"))
        self.tempo=QSpinBox()
        self.tempo.setRange(30,300)
        self.tempo.setValue(120)
        self.tempo.setSuffix(" BPM")
        commands.addWidget(self.tempo)
        root.addLayout(commands)
        self.tab=QTextEdit()
        self.tab.setPlaceholderText("Paste aligned ASCII guitar/bass tab here.\n"
            "e|--0---3---5---|\nB|--1---3---5---|\nG|--0---0---5---|\n"
            "D|--2---0---7---|\nA|--3---2---7---|\nE|------3---5---|")
        self.tab.setMinimumHeight(150)
        root.addWidget(self.tab,1)
        parse=QPushButton("Read pasted TAB and prepare performance")
        parse.clicked.connect(self.read_tab)
        root.addWidget(parse)
        self.detail=QLabel("No score loaded.")
        self.detail.setWordWrap(True)
        root.addWidget(self.detail)
        bankrow=QHBoxLayout()
        bankrow.addWidget(QLabel("SoundFont .sf2/.sf3"))
        self.bank=QLineEdit()
        self.bank.setPlaceholderText("Choose a licensed sampled instrument bank for WAV performance")
        bankrow.addWidget(self.bank,1)
        choose=QPushButton("Select bank")
        choose.clicked.connect(self.choose_bank)
        bankrow.addWidget(choose)
        root.addLayout(bankrow)
        exports=QHBoxLayout()
        midi=QPushButton("Export playable MIDI arrangement")
        midi.clicked.connect(self.export_midi)
        exports.addWidget(midi)
        wav=QPushButton("Render full performance as sampled WAV")
        wav.clicked.connect(self.render_wav)
        exports.addWidget(wav)
        root.addLayout(exports)
        self.status=QLabel("Spider follows the written notes. Quality depends on the configured SoundFont.")
        self.status.setWordWrap(True)
        root.addWidget(self.status)
    def _loaded(self):
        if self.score:
            self.detail.setText(
                f"{self.score.title}: {len(self.score.notes)} notes; "
                f"{len(self.score.tracks)} instruments; {self.score.bpm} BPM; "
                f"{self.score.seconds:.1f}s. "
                + " ".join(self.score.warnings[:3]))
    def import_file(self):
        filename,_=QFileDialog.getOpenFileName(self,"Import sheet music or TAB",
            str(Path.home()/"Music"),"Notation (*.musicxml *.xml *.tab *.txt)")
        if not filename:return
        try:
            candidate=import_score_file(filename,self.instrument.currentText(),self.tempo.value())
            if len(candidate.tracks)>15:
                raise ValueError("Current MIDI renderer supports up to 15 instrument parts")
            self.score=candidate
            self._loaded()
        except (OSError,ValueError,UnicodeError) as error:
            QMessageBox.warning(self,"Import failed",str(error)[:300])
    def read_tab(self):
        try:
            candidate=import_ascii_tab(self.tab.toPlainText(),self.instrument.currentText(),
                                       self.tempo.value())
            self.score=candidate
            self._loaded()
        except (OSError,ValueError) as error:
            self.status.setText("TAB parsing failed: "+str(error)[:300])
    def choose_bank(self):
        filename,_=QFileDialog.getOpenFileName(self,"Choose licensed SoundFont",
            str(Path.home()),"SoundFont (*.sf2 *.sf3)")
        if filename:self.bank.setText(filename)
    def export_midi(self):
        if self.score is None:
            self.status.setText("Read a score first.")
            return
        filename,_=QFileDialog.getSaveFileName(self,"Export playable score MIDI",
            str(Path.home()/"Music"/"Spider-Performance.mid"),"MIDI (*.mid)")
        if filename:
            try:
                export_performance_midi(self.score,filename)
                self.status.setText("Full performance exported as standard MIDI.")
            except (OSError,ValueError) as error:
                QMessageBox.warning(self,"MIDI export failed",str(error)[:300])
    def render_wav(self):
        if self.score is None:
            self.status.setText("Read sheet music or TAB first.")
            return
        if not soundfont_ready(self.bank.text().strip()):
            self.status.setText("Install/configure FluidSynth and choose an existing licensed .sf2/.sf3 bank.")
            return
        if self.worker is not None and self.worker.isRunning():
            self.status.setText("Performance render is running.")
            return
        filename,_=QFileDialog.getSaveFileName(self,"Render score to WAV",
            str(Path.home()/"Music"/"Spider-Performance.wav"),"WAV (*.wav)")
        if not filename:return
        self.worker=ScoreRenderThread(self.score,self.bank.text().strip(),filename,self)
        self.worker.done.connect(
            lambda ok,msg:self.status.setText(msg if ok else "Performance failed: "+msg))
        self.worker.start()
        self.status.setText("Rendering the written performance using the chosen SoundFont.")
    def closeEvent(self,event):
        if self.worker is not None and self.worker.isRunning():
            event.ignore()
        else:
            super().closeEvent(event)
