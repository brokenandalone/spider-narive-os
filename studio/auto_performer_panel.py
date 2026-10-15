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
    QPushButton, QSpinBox, QVBoxLayout, QWidget, QSlider, QCheckBox,
)

try:
    from PyQt5.QtMultimedia import QAudioOutput, QAudioFormat
except ImportError:
    QAudioOutput = QAudioFormat = None

try:
    from .score_performer import parse_musicxml, parse_ascii_tab, load_notation
    from .chord_chart_performer import parse_chord_chart
    from .score_midi import export_performance_midi
    from .soundfont_render import quality_backend_available, render_soundfont, validate_soundfont
    from .performance_expression import Expression, GROOVES, express
    from .studio_score_mix import MixChannel, render_score_mix
    from .soundfont_library import auto_soundfont, discover_soundfonts
    from .score_edit_session import save_project, load_project
    from .score_stem_export import render_score_stems
except ImportError:
    from score_performer import parse_musicxml, parse_ascii_tab, load_notation
    from chord_chart_performer import parse_chord_chart
    from score_midi import export_performance_midi
    from soundfont_render import quality_backend_available, render_soundfont, validate_soundfont
    from performance_expression import Expression, GROOVES, express
    from studio_score_mix import MixChannel, render_score_mix
    from soundfont_library import auto_soundfont, discover_soundfonts
    from score_edit_session import save_project, load_project
    from score_stem_export import render_score_stems

TAB_EXAMPLE = """e|--0---2---3---2-|
B|--1---3---0---3-|
G|--0---2---0---2-|
D|--2---0---0---0-|
A|--3-------2-----|
E|----------3-----|"""

class ScoreRenderWorker(QThread):
    finished_score = pyqtSignal(bool, str, str)

    def __init__(self, performance, soundfont, output, preview=False, parent=None,
                 banks=None, channels=None, studio_mix=False, rate=48000,
                 bit_depth=16):
        super().__init__(parent)
        self.performance = performance
        self.soundfont = soundfont
        self.output = output
        self.preview = preview
        self.banks = dict(banks or {})
        self.channels = list(channels or [])
        self.studio_mix = bool(studio_mix)
        self.rate = rate
        self.bit_depth = bit_depth

    def run(self):
        try:
            if self.studio_mix or self.banks:
                result = render_score_mix(
                    self.performance, self.soundfont, self.output,
                    part_banks=self.banks, channels=self.channels,
                    rate=self.rate, bit_depth=self.bit_depth)
            else:
                result = render_soundfont(self.performance, self.soundfont, self.output,
                                          rate=self.rate)
            self.finished_score.emit(True, str(result), "")
        except (OSError, ValueError, RuntimeError) as error:
            self.finished_score.emit(False, "", str(error)[:300])

class StemRenderWorker(QThread):
    finished_score = pyqtSignal(bool, str, str)
    kind = "stems"
    preview = False

    def __init__(self, score, default_bank, destination, banks, rate, depth, parent=None):
        super().__init__(parent)
        self.score = score
        self.default_bank = default_bank
        self.destination = destination
        self.banks = dict(banks)
        self.rate = rate
        self.depth = depth

    def run(self):
        try:
            result = render_score_stems(
                self.score,self.default_bank,self.destination,
                part_banks=self.banks,rate=self.rate,bit_depth=self.depth)
            self.finished_score.emit(True,str(result),"")
        except (OSError,ValueError,RuntimeError) as error:
            self.finished_score.emit(False,"",str(error)[:320])


class AutoPerformerPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.performance = None
        self.editor_panel = None
        self.editor_switch = None
        self.soundfont = None
        self.part_banks = {}
        self.mix_channels = []
        self.worker = None
        self._play_after = False
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
            "Import MusicXML sheet music or MIDI, or paste six-string guitar/four-string "
            "bass ASCII tab. Spider translates the notes into a timed performance. "
            "Choose a local licensed SoundFont for higher-quality sound.")
        note.setWordWrap(True)
        layout.addWidget(note)
        row = QHBoxLayout()
        self.load_button = self._button("Import sheet music / MIDI / TAB / chords", self.import_file)
        row.addWidget(self.load_button)
        self.soundfont_button = self._button("Select instrument SoundFont (.sf2/.sf3)", self.choose_soundfont)
        row.addWidget(self.soundfont_button)
        row.addWidget(self._button("Find installed instruments", self.detect_soundfonts))
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
        layout.addWidget(QLabel("PASTE TAB OR CHORD CHART (e.g., Am | F | C | G)"))
        self.tab_text = QPlainTextEdit()
        self.tab_text.setPlainText(TAB_EXAMPLE)
        self.tab_text.setMinimumHeight(125)
        self.tab_text.setAccessibleName("Guitar or bass ASCII TAB input")
        layout.addWidget(self.tab_text)
        interpret_row = QHBoxLayout()
        interpret_row.addWidget(self._button("Interpret as Guitar/Bass TAB", self.interpret_tab))
        interpret_row.addWidget(self._button("Arrange as Chord Chart", self.interpret_chords))
        layout.addLayout(interpret_row)
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

        # Professional production controls operate on the selected score
        # part; the user picks local/licensed sample banks one part at a time.
        bank_row = QHBoxLayout()
        self.part_bank_label = QLabel("This part uses the default SoundFont")
        self.part_bank_label.setWordWrap(True)
        bank_row.addWidget(self.part_bank_label, 1)
        bank_row.addWidget(self._button("Assign SoundFont to selected part", self.choose_part_bank))
        bank_row.addWidget(self._button("Use default bank", self.reset_part_bank))
        layout.addLayout(bank_row)
        mixer_row = QHBoxLayout()
        mixer_row.addWidget(QLabel("PART VOLUME"))
        self.part_gain = QSlider(Qt.Horizontal)
        self.part_gain.setRange(0, 120)
        self.part_gain.setValue(90)
        self.part_gain.setAccessibleName("Selected score part volume")
        self.part_gain.valueChanged.connect(self._part_mix_changed)
        mixer_row.addWidget(self.part_gain, 2)
        mixer_row.addWidget(QLabel("PAN"))
        self.part_pan = QSlider(Qt.Horizontal)
        self.part_pan.setRange(-100, 100)
        self.part_pan.setAccessibleName("Selected score part stereo pan")
        self.part_pan.valueChanged.connect(self._part_mix_changed)
        mixer_row.addWidget(self.part_pan, 2)
        self.part_mute = QCheckBox("Mute")
        self.part_solo = QCheckBox("Solo")
        self.part_mute.toggled.connect(self._part_mix_changed)
        self.part_solo.toggled.connect(self._part_mix_changed)
        mixer_row.addWidget(self.part_mute)
        mixer_row.addWidget(self.part_solo)
        layout.addLayout(mixer_row)

        groove_row = QHBoxLayout()
        groove_row.addWidget(QLabel("PERFORMANCE FEEL"))
        self.groove = QComboBox()
        self.groove.addItems(GROOVES)
        self.groove.setCurrentText("Natural player")
        groove_row.addWidget(self.groove)
        groove_row.addWidget(QLabel("Energy"))
        self.energy = QSpinBox()
        self.energy.setRange(0, 100)
        self.energy.setValue(75)
        groove_row.addWidget(self.energy)
        groove_row.addWidget(QLabel("Strum ms"))
        self.strum_ms = QSpinBox()
        self.strum_ms.setRange(0, 45)
        self.strum_ms.setValue(9)
        groove_row.addWidget(self.strum_ms)
        groove_row.addWidget(QLabel("Output"))
        self.rate_select = QComboBox()
        self.rate_select.addItem("48 kHz", 48000)
        self.rate_select.addItem("44.1 kHz", 44100)
        groove_row.addWidget(self.rate_select)
        groove_row.addWidget(QLabel("WAV depth"))
        self.depth_select = QComboBox()
        self.depth_select.addItem("16-bit PCM", 16)
        self.depth_select.addItem("24-bit PCM mix", 24)
        self.depth_select.setCurrentIndex(1)
        self.depth_select.setAccessibleName("Export bit depth")
        groove_row.addWidget(self.depth_select)
        layout.addLayout(groove_row)
        self.studio_mix = QCheckBox(
            "Studio multi-bank mix · render each part separately (more CPU, enables per-part pan/volume)")
        self.studio_mix.setChecked(True)
        self.studio_mix.setAccessibleName("Enable studio multi SoundFont rendering")
        layout.addWidget(self.studio_mix)
        actions = QHBoxLayout()
        self.play_button = self._button("▶ Play score automatically", self.play)
        self.stop_button = self._button("■ Stop", self.stop)
        self.midi_button = self._button("Export written MIDI notes", self.export_midi)
        self.expressive_midi_button = self._button(
            "Export humanized MIDI performance", self.export_expressive_midi)
        self.wav_button = self._button("Export SoundFont WAV", self.export_wav)
        for button in (self.play_button, self.stop_button, self.midi_button,
                       self.expressive_midi_button, self.wav_button):
            actions.addWidget(button)
        layout.addLayout(actions)
        project_row = QHBoxLayout()
        project_row.addWidget(self._button("✎ Edit Notes / Quantize", self.open_editor))
        project_row.addWidget(self._button("Save Spider Score Session", self.save_score_session))
        project_row.addWidget(self._button("Open Spider Score Session", self.open_score_session))
        project_row.addWidget(self._button("Export Separate Instrument Stems", self.export_stems))
        layout.addLayout(project_row)
        self.status = QLabel(
            "Auto Performer is offline and does not monitor your mic, import private "
            "music or control Nova. Sound quality depends on your selected SoundFont.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        # Automatic local discovery is read-only and never enables a MIDI/
        # audio device. The user can replace this bank at any time.
        self.detect_soundfonts()

    def attach_editor(self, editor_panel, switch_callback):
        self.editor_panel = editor_panel
        self.editor_switch = switch_callback
        if self.performance is not None:
            editor_panel.set_score(self.performance)

    def open_editor(self):
        if self.performance is None:
            self.status.setText("Import notation or MIDI before editing notes.")
            return
        if self.editor_switch is not None:
            self.editor_switch()

    def apply_edited_score(self, performance):
        """Make all renders and MIDI exports use the actual edited note score."""
        self.performance = performance.validated()
        if self.part_select.count():
            self._part_selected(self.part_select.currentIndex())
        self.info.setText(
            f"Edited performance: {self.performance.title} · "
            f"{len(self.performance.notes)} notes · "
            f"{len(self.performance.parts)} instrument parts · "
            f"{self.performance.duration_seconds:.2f} seconds")
        self.status.setText("Edited score is active in Auto Performer and ready to render.")

    def _session_settings(self):
        return {
            "channels":[{"gain":m.gain,"pan":m.pan,"mute":m.mute,"solo":m.solo}
                        for m in self.mix_channels],
            "groove":self.groove.currentText(),
            "energy":self.energy.value(),
            "strum_ms":self.strum_ms.value(),
            "rate":self.rate_select.currentData(),
            "depth":self.depth_select.currentData(),
        }

    def save_score_session(self):
        if self.performance is None:
            self.status.setText("Import or compose a score before saving its session.")
            return
        filename,_=QFileDialog.getSaveFileName(
            self,"Save a private Spider Score Session",
            str(Path.home()/"Music"/"Spider-Session.spiderscore"),
            "Spider Score Session (*.spiderscore)")
        if not filename:
            return
        try:
            save_project(filename,self.performance,self._session_settings())
            self.status.setText(
                "Saved score, edits and mixer settings in " + Path(filename).name +
                ". Sample-bank locations are not embedded; reselect them when opening.")
        except (ValueError,OSError,TypeError) as error:
            QMessageBox.warning(self,"Session save failed",str(error)[:280])

    def open_score_session(self):
        filename,_=QFileDialog.getOpenFileName(
            self,"Open your Spider Score Session",str(Path.home()/"Music"),
            "Spider Score Session (*.spiderscore)")
        if not filename:
            return
        try:
            score,settings=load_project(filename)
            raw_channels=settings.get("channels",[])
            if raw_channels:
                if not isinstance(raw_channels,list) or len(raw_channels)!=len(score.parts):
                    raise ValueError("Saved mixer channels do not match the score")
                controls=[MixChannel(**record).validate() for record in raw_channels]
            else:
                controls=[MixChannel() for _ in score.parts]
            groove=settings.get("groove","Natural player")
            energy=settings.get("energy",75)
            strum=settings.get("strum_ms",9)
            rate=settings.get("rate",48000)
            depth=settings.get("depth",24)
            Expression(groove,energy,strum).validate()
            if rate not in (44100,48000) or depth not in (16,24):
                raise ValueError("Saved export format is invalid")
            self._load(score)
            self.mix_channels=controls
            self._part_selected(0)
            self.groove.setCurrentText(groove)
            self.energy.setValue(energy)
            self.strum_ms.setValue(strum)
            self.rate_select.setCurrentIndex(0 if rate==48000 else 1)
            self.depth_select.setCurrentIndex(1 if depth==24 else 0)
            self.status.setText(
                f"Loaded {Path(filename).name}: notes, parts, dynamics and mix restored. "
                "Reconnect your licensed sample banks to render.")
        except (ValueError,OSError,TypeError,KeyError,IndexError) as error:
            QMessageBox.warning(self,"Cannot open score session",str(error)[:320])

    def _button(self, text, action):
        button = QPushButton(text)
        button.clicked.connect(action)
        return button

    def _load(self, performance):
        self.stop()
        self.performance = performance
        self.part_banks = {}
        self.mix_channels = [MixChannel() for _ in performance.parts]
        self.part_select.blockSignals(True)
        try:
            self.part_select.clear()
            for part in performance.parts:
                self.part_select.addItem(part.name)
        finally:
            self.part_select.blockSignals(False)
        self._part_selected(0)
        if self.editor_panel is not None:
            self.editor_panel.set_score(performance)
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
        setting = self.mix_channels[index] if index < len(self.mix_channels) else MixChannel()
        for widget in (self.part_gain, self.part_pan, self.part_mute, self.part_solo):
            widget.blockSignals(True)
        try:
            self.part_gain.setValue(setting.gain)
            self.part_pan.setValue(setting.pan)
            self.part_mute.setChecked(setting.mute)
            self.part_solo.setChecked(setting.solo)
        finally:
            for widget in (self.part_gain, self.part_pan, self.part_mute, self.part_solo):
                widget.blockSignals(False)
        bank = self.part_banks.get(index)
        self.part_bank_label.setText(
            "Selected part bank: " + Path(bank).name if bank else
            "This part uses the default SoundFont")

    def _part_mix_changed(self, *unused):
        index = self.part_select.currentIndex()
        if not 0 <= index < len(self.mix_channels):
            return
        self.mix_channels[index] = MixChannel(
            self.part_gain.value(), self.part_pan.value(),
            self.part_mute.isChecked(), self.part_solo.isChecked()).validate()

    def choose_part_bank(self):
        index = self.part_select.currentIndex()
        if not 0 <= index < len(self.mix_channels):
            self.status.setText("Import a score and select an instrument part first.")
            return
        filename, _ = QFileDialog.getOpenFileName(
            self, "Choose licensed samples for this instrument",
            str(Path.home()), "SoundFont bank (*.sf2 *.sf3)")
        if filename:
            try:
                bank = validate_soundfont(filename)
                self.part_banks[index] = str(bank)
                self._part_selected(index)
                self.status.setText(
                    f"Selected {bank.name} for {self.performance.parts[index].name}. "
                    "Other instrument parts keep their selected banks.")
            except (OSError, ValueError) as error:
                QMessageBox.warning(self, "Invalid instrument bank", str(error)[:300])

    def reset_part_bank(self):
        index = self.part_select.currentIndex()
        if 0 <= index < len(self.mix_channels):
            self.part_banks.pop(index, None)
            self._part_selected(index)

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
            if self.editor_panel is not None:
                self.editor_panel.sync_external(self.performance)
            self.status.setText(
                f"SoundFont program updated: {part.name} · GM patch {index}. "
                "The next playback/render will use this sound.")

    def import_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open MusicXML sheet music or guitar/bass TAB",
            str(Path.home() / "Music"),
            "Notation and music (*.mxl *.musicxml *.xml *.mid *.midi *.txt *.chords)")
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

    def interpret_chords(self):
        try:
            self._load(parse_chord_chart(self.tab_text.toPlainText(),
                                         bpm=self.tempo.value()))
        except ValueError as error:
            QMessageBox.warning(self, "Chord chart error", str(error)[:400])

    def detect_soundfonts(self):
        try:
            banks = discover_soundfonts()
        except (OSError, ValueError):
            banks = []
        if not banks:
            self.status.setText(
                "No installed SoundFont detected in standard local folders. "
                "Select a licensed .sf2/.sf3 file to enable sample-based performance.")
            return
        self.soundfont = str(banks[0])
        backend = "FluidSynth ready" if quality_backend_available() else "FluidSynth not installed"
        self.status.setText(
            f"Found {len(banks)} local instrument bank(s); using {banks[0].name} "
            f"as the default. {backend}. Actual fidelity and licensing must be checked.")

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

    def export_expressive_midi(self):
        if self.performance is None:
            self.status.setText("Import notation or MIDI first.")
            return
        try:
            performance = express(self.performance, Expression(
                groove=self.groove.currentText(), energy=self.energy.value(),
                strum_ms=self.strum_ms.value()))
        except ValueError as error:
            self.status.setText("Invalid performance feel settings: " + str(error)[:220])
            return
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save musician-style MIDI performance",
            str(Path.home() / "Music" / "Spider-Humanized-Performance.mid"),
            "Standard MIDI (*.mid)")
        if filename:
            try:
                export_performance_midi(performance, filename)
                self.status.setText(
                    "Saved your expressive MIDI performance: " + Path(filename).name)
            except (OSError, ValueError) as error:
                QMessageBox.warning(self, "Expressive MIDI export failed", str(error)[:300])

    def export_stems(self):
        """Produce isolated dry tracks. Existing stem folders are never overwritten."""
        if self.performance is None:
            self.status.setText("Load a score before exporting individual instrument tracks.")
            return
        if self.worker is not None and self.worker.isRunning():
            self.status.setText("Another audio export is already running.")
            return
        if not self.soundfont:
            self.status.setText("Select one local licensed SoundFont first.")
            return
        if not quality_backend_available():
            self.status.setText("Install FluidSynth CLI to render independent instruments.")
            return
        parent=QFileDialog.getExistingDirectory(
            self,"Choose the parent folder for a new instrument-stems directory",
            str(Path.home()/"Music"))
        if not parent:
            return
        try:
            expressive=express(self.performance,Expression(
                self.groove.currentText(),self.energy.value(),self.strum_ms.value()))
            # A new folder, not the chosen existing parent, is created atomically.
            from re import sub
            safe=sub(r"[^A-Za-z0-9_-]+","-",expressive.title).strip("-")[:44]
            destination=Path(parent)/((safe or "Spider-Session")+"-Stems")
            if destination.exists():
                self.status.setText(
                    "Stem folder already exists. Choose a different parent folder or "
                    "rename the previous stems; no recordings were overwritten.")
                return
            self._play_after=False
            self.worker=StemRenderWorker(
                expressive,self.soundfont,str(destination),dict(self.part_banks),
                self.rate_select.currentData(),self.depth_select.currentData(),self)
            self.worker.finished_score.connect(self._done)
            self.worker.start()
            self.status.setText(
                "Rendering each instrument as aligned, dry stereo tracks. "
                "All stems remain available even when mixer channels are muted.")
        except (ValueError,OSError,TypeError) as error:
            self.status.setText("Cannot export stems: "+str(error)[:260])

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
        try:
            expression = Expression(
                groove=self.groove.currentText(), energy=self.energy.value(),
                strum_ms=self.strum_ms.value())
            snapshot = express(self.performance, expression)
        except (ValueError, TypeError) as error:
            self.status.setText("Performance settings invalid: " + str(error)[:200])
            return
        # Qt preview requires 16-bit audio; saved studio mixes may use 24.
        chosen_depth = 16 if preview else self.depth_select.currentData()
        if chosen_depth == 24 and not self.studio_mix.isChecked():
            self.status.setText(
                "24-bit WAV export requires Studio multi-bank mix. Enable its checkbox.")
            return
        self._play_after = preview
        self.worker = ScoreRenderWorker(
            snapshot, self.soundfont, destination, preview, self,
            banks=dict(self.part_banks), channels=list(self.mix_channels),
            studio_mix=self.studio_mix.isChecked(), rate=self.rate_select.currentData(),
            bit_depth=chosen_depth)
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
        if getattr(self.worker,"kind",None)=="stems":
            self.status.setText(
                "Exported aligned instrument stems and stems.json: " + Path(filename).name)
            return
        if self.worker is None or not self.worker.preview or not self._play_after:
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
        self._play_after = False
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
