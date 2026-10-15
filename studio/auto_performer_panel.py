"""Native Spider Auto Performer: give it MusicXML or tab, then play/export.

Actual sheet and text-tab import plus opt-in local SoundFont performance.
PDF scans, Guitar Pro binary files, lyric-only sheets and complex repeat
directions are not supported; unsupported material is reported honestly.
"""
from __future__ import annotations

from pathlib import Path
from dataclasses import replace
import tempfile
import wave

from PyQt5.QtCore import Qt, QBuffer, QByteArray, QIODevice, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QFileDialog, QComboBox, QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit,
    QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

try:
    from PyQt5.QtMultimedia import QAudioOutput, QAudioFormat
except ImportError:
    QAudioOutput = QAudioFormat = None

try:
    from .score_performer import parse_musicxml, parse_ascii_tab, load_notation
    from .score_midi import export_performance_midi
    from .soundfont_render import quality_backend_available, render_soundfont
except ImportError:
    from score_performer import parse_musicxml, parse_ascii_tab, load_notation
    from score_midi import export_performance_midi
    from soundfont_render import quality_backend_available, render_soundfont

TAB_EXAMPLE = """e|--0---2---3---2-|
B|--1---3---0---3-|
G|--0---2---0---2-|
D|--2---0---0---0-|
A|--3-------2-----|
E|----------3-----|"""

class ScoreRenderWorker(QThread):
    finished_score = pyqtSignal(bool, str, str)

    def __init__(self, performance, soundfont, output, preview=False, parent=None):
        super().__init__(parent)
        self.performance = performance
        self.soundfont = soundfont
        self.output = output
        self.preview = preview

    def run(self):
        try:
            result = render_soundfont(self.performance, self.soundfont, self.output)
            self.finished_score.emit(True, str(result), "")
        except (OSError, ValueError, RuntimeError) as error:
            self.finished_score.emit(False, "", str(error)[:300])

class AutoPerformerPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.performance = None
        self.soundfont = None
        self.worker = None
        self._audio = None
        self._buffer = None
        self._temporary = None
        self.setObjectName("spiderAutoPerformerPanel")
        self.setStyleSheet("""
            QWidget#spiderAutoPerformerPanel { background:#110d21; }
            QLabel {color:#ecdefe;}
            QPushButton {background:#38254f;color:#f3e7ff;border:1px solid #9568bd;
                padding:9px;border-radius:8px;min-height:32px;}
            QPushButton:hover {background:#66478d;}
            QPlainTextEdit,QComboBox,QSpinBox {background:#1d1730;color:#f8edff;
                border:1px solid #684f89;padding:6px;}
        """)
        layout = QVBoxLayout(self)
        title = QLabel("SPIDER AUTO PERFORMER  /  READ IT. PLAY IT.")
        title.setStyleSheet("font-size:21px;font-weight:bold;color:#d0b0ff")
        layout.addWidget(title)
        note = QLabel(
            "Import MusicXML sheet music, or paste standard six-string guitar/four-string "
            "bass ASCII tab. Spider translates the notes into a timed performance. "
            "Choose a local licensed SoundFont for higher-quality sound.")
        note.setWordWrap(True)
        layout.addWidget(note)
        row = QHBoxLayout()
        self.load_button = self._button("Import MusicXML / MXL / TXT TAB", self.import_file)
        row.addWidget(self.load_button)
        self.soundfont_button = self._button("Select instrument SoundFont (.sf2/.sf3)", self.choose_soundfont)
        row.addWidget(self.soundfont_button)
        layout.addLayout(row)
        config = QHBoxLayout()
        config.addWidget(QLabel("TAB tempo"))
        self.tempo = QSpinBox()
        self.tempo.setRange(30, 280)
        self.tempo.setValue(110)
        self.tempo.setSuffix(" BPM")
        config.addWidget(self.tempo)
        config.addWidget(QLabel("Tab timing"))
        self.grid = QComboBox()
        self.grid.addItem("Eighth-note columns (2/beat)", 2)
        self.grid.addItem("Quarter-note columns (1/beat)", 1)
        self.grid.addItem("Sixteenth-note columns (4/beat)", 4)
        config.addWidget(self.grid)
        config.addStretch()
        layout.addLayout(config)
        layout.addWidget(QLabel("PASTE TEXT GUITAR OR BASS TAB (example below)"))
        self.tab_text = QPlainTextEdit()
        self.tab_text.setPlainText(TAB_EXAMPLE)
        self.tab_text.setMinimumHeight(125)
        self.tab_text.setAccessibleName("Guitar or bass ASCII TAB input")
        layout.addWidget(self.tab_text)
        layout.addWidget(self._button("Interpret pasted tab as performance", self.interpret_tab))
        self.info = QLabel("No score loaded. MusicXML supports chords, rests, voices, ties, "
                           "transposition and a fixed tempo; complex notation may need review.")
        self.info.setWordWrap(True)
        layout.addWidget(self.info)
        # Override GM patches in the SoundFont without changing the score.
        # This is especially useful for electric guitar vs. steel acoustic
        # guitar. General MIDI programs are 0-127.
        patch_row = QHBoxLayout()
        patch_row.addWidget(QLabel("PLAY PART"))
        self.part_select = QComboBox()
        self.part_select.setAccessibleName("Imported score part to adjust")
        self.part_select.currentIndexChanged.connect(self._part_selected)
        patch_row.addWidget(self.part_select, 1)
        patch_row.addWidget(QLabel("AS INSTRUMENT"))
        self.patch_select = QComboBox()
        self.patch_select.setAccessibleName("Instrument sound program")
        labels = {
            0: "Grand Piano", 1: "Bright Piano", 4: "Electric Piano",
            16: "Drawbar Organ", 24: "Nylon Acoustic Guitar",
            25: "Steel Acoustic Guitar", 26: "Jazz Electric Guitar",
            27: "Clean Electric Guitar", 28: "Muted Electric Guitar",
            29: "Overdrive Guitar", 30: "Distortion Guitar",
            31: "Guitar Harmonics", 32: "Acoustic Bass",
            33: "Finger Electric Bass", 34: "Pick Electric Bass",
            35: "Fretless Bass", 38: "Synth Bass I", 39: "Synth Bass II",
            40: "Violin", 42: "Cello", 48: "Strings",
            52: "Choir", 80: "Square Lead",
        }
        for patch in range(128):
            self.patch_select.addItem(f"{patch:03} · {labels.get(patch, 'GM Program')}", patch)
        self.patch_select.currentIndexChanged.connect(self._patch_selected)
        patch_row.addWidget(self.patch_select, 2)
        layout.addLayout(patch_row)
        actions = QHBoxLayout()
        self.play_button = self._button("▶ Play score automatically", self.play)
        self.stop_button = self._button("■ Stop", self.stop)
        self.midi_button = self._button("Export accurate MIDI notes", self.export_midi)
        self.wav_button = self._button("Export SoundFont WAV", self.export_wav)
        for button in (self.play_button, self.stop_button, self.midi_button, self.wav_button):
            actions.addWidget(button)
        layout.addLayout(actions)
        self.status = QLabel(
            "Auto Performer is offline and does not monitor your mic, import private "
            "music or control Nova. Sound quality depends on your selected SoundFont.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

    def _button(self, text, action):
        button = QPushButton(text)
        button.clicked.connect(action)
        return button

    def _load(self, performance):
        self.stop()
        self.performance = performance
        self.part_select.blockSignals(True)
        try:
            self.part_select.clear()
            for part in performance.parts:
                self.part_select.addItem(part.name)
        finally:
            self.part_select.blockSignals(False)
        self._part_selected(0)
        parts = ", ".join(p.name for p in performance.parts)
        warning = " | ".join(performance.warnings)
        self.info.setText(
            f"Loaded: {performance.title} · {len(performance.notes)} notes · "
            f"{len(performance.parts)} part(s): {parts} · "
            f"{performance.bpm} BPM · {performance.duration_seconds:.1f} sec"
            + (f"\nLIMITATIONS: {warning}" if warning else ""))
        self.status.setText("Performance ready. Select a SoundFont to play it, or export MIDI.")

    def _part_selected(self, index):
        if self.performance is None or not 0 <= index < len(self.performance.parts):
            self.patch_select.setEnabled(False)
            return
        part = self.performance.parts[index]
        self.patch_select.blockSignals(True)
        try:
            self.patch_select.setCurrentIndex(part.program)
            self.patch_select.setEnabled(part.channel != 9)
        finally:
            self.patch_select.blockSignals(False)

    def _patch_selected(self, index):
        if self.performance is None:
            return
        selected = self.part_select.currentIndex()
        if not 0 <= selected < len(self.performance.parts):
            return
        part = self.performance.parts[selected]
        if part.channel == 9:
            return  # GM percussion channel is a drum kit, not a pitched patch.
        if 0 <= index <= 127:
            self.performance.parts[selected] = replace(part, program=index)
            self.status.setText(
                f"SoundFont program updated: {part.name} · GM patch {index}. "
                "The next playback/render will use this sound.")

    def import_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open MusicXML sheet music or guitar/bass TAB",
            str(Path.home() / "Music"),
            "Notation and tab (*.mxl *.musicxml *.xml *.txt)")
        if not filename:
            return
        try:
            self._load(load_notation(filename, self.tempo.value(), self.grid.currentData()))
        except (OSError, ValueError, UnicodeError) as error:
            QMessageBox.warning(self, "Cannot read this notation", str(error)[:400])

    def interpret_tab(self):
        try:
            self._load(parse_ascii_tab(self.tab_text.toPlainText(),
                                       self.tempo.value(), self.grid.currentData()))
        except ValueError as error:
            QMessageBox.warning(self, "TAB error", str(error)[:400])

    def choose_soundfont(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Choose your own licensed SoundFont",
            str(Path.home()), "SoundFont bank (*.sf2 *.sf3)")
        if not filename:
            return
        try:
            from .soundfont_render import validate_soundfont
        except ImportError:
            from soundfont_render import validate_soundfont
        try:
            self.soundfont = str(validate_soundfont(filename))
            self.status.setText(
                "Selected local instrument bank: " + Path(filename).name +
                (". Ready to render." if quality_backend_available() else
                 ". FluidSynth CLI needs installation for high-quality rendering."))
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Invalid SoundFont", str(error)[:250])

    def export_midi(self):
        if self.performance is None:
            self.status.setText("Import sheet music or interpret tab before exporting.")
            return
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export MusicXML/TAB performance as MIDI",
            str(Path.home() / "Music" / "Spider-Performance.mid"),
            "MIDI file (*.mid)")
        if not filename:
            return
        try:
            export_performance_midi(self.performance, filename)
            self.status.setText("Exported full multi-part MIDI: " + Path(filename).name)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "MIDI export failed", str(error)[:300])

    def _start_render(self, destination, preview):
        if self.performance is None:
            self.status.setText("Import MusicXML or interpret text tab first.")
            return
        if not self.soundfont:
            self.status.setText("Select a local .sf2/.sf3 SoundFont to hear these notes.")
            return
        if not quality_backend_available():
            self.status.setText(
                "FluidSynth executable not detected. You can export MIDI and render elsewhere.")
            return
        if self.worker is not None and self.worker.isRunning():
            self.status.setText("A score is already rendering.")
            return
        self.worker = ScoreRenderWorker(
            self.performance, self.soundfont, destination, preview, self)
        self.worker.finished_score.connect(self._done)
        self.worker.start()
        self.status.setText(
            "Rendering notation into instruments in a separate thread "
            "(SoundFont-dependent quality).")

    def play(self):
        if self.performance is None:
            self.status.setText("Import MusicXML or interpret text tab first.")
            return
        if QAudioOutput is None:
            self.status.setText("Qt Multimedia unavailable for playback; MIDI export still works.")
            return
        if self.worker is not None and self.worker.isRunning():
            self.status.setText("Still rendering the current performance.")
            return
        self.stop()
        self._temporary = tempfile.TemporaryDirectory(prefix="spider-score-play-")
        filename = Path(self._temporary.name) / "preview.wav"
        self._start_render(str(filename), preview=True)

    def export_wav(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Render MusicXML/TAB with your SoundFont",
            str(Path.home() / "Music" / "Spider-Score.wav"),
            "WAV audio (*.wav)")
        if filename:
            self._start_render(filename, preview=False)

    def _done(self, ok, filename, error):
        if not ok:
            self.status.setText("SoundFont rendering failed: " + error)
            return
        if self.worker is None or not self.worker.preview:
            self.status.setText("Rendered full SoundFont WAV: " + Path(filename).name)
            return
        self._play_wav(filename)

    def _play_wav(self, filename):
        try:
            with wave.open(str(filename), "rb") as audio:
                rate = audio.getframerate()
                channels = audio.getnchannels()
                if audio.getsampwidth() != 2 or channels != 2:
                    raise ValueError("Unsupported playback PCM format")
                pcm = audio.readframes(audio.getnframes())
            fmt = QAudioFormat()
            fmt.setSampleRate(rate)
            fmt.setChannelCount(2)
            fmt.setSampleSize(16)
            fmt.setCodec("audio/pcm")
            fmt.setByteOrder(QAudioFormat.LittleEndian)
            fmt.setSampleType(QAudioFormat.SignedInt)
            output = QAudioOutput(fmt, self)
            buffer = QBuffer(output)
            buffer.setData(QByteArray(pcm))
            buffer.open(QIODevice.ReadOnly)
            self._audio = output
            self._buffer = buffer
            output.setVolume(.6)
            output.start(buffer)
            self.status.setText("Spider is now performing the imported notes with your selected SoundFont.")
        except (OSError, ValueError, RuntimeError) as error:
            self.status.setText("Playback failed: " + str(error)[:250])

    def stop(self):
        if self._audio is not None:
            self._audio.stop()
            self._audio.deleteLater()
            self._audio = None
            self._buffer = None
        if self.worker is None or not self.worker.isRunning():
            if self._temporary is not None:
                self._temporary.cleanup()
                self._temporary = None

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            self.status.setText("SoundFont render active; export must finish before closing.")
            event.ignore()
            return
        self.stop()
        super().closeEvent(event)
