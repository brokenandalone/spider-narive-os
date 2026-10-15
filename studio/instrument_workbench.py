"""Playable native drum/guitar/bass/keyboard workbench inside Spider Studio.

Phase-one prototype: procedural mono audio via Qt Multimedia when available,
with validated pattern JSON and offline WAV exports. Original Ubuntu Studio
applications are preserved, not embedded or replaced.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

from PyQt5.QtCore import Qt, QBuffer, QByteArray, QIODevice, QTimer, QRectF
from PyQt5.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen, QKeySequence
from PyQt5.QtWidgets import (
    QComboBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QScrollArea, QShortcut, QSpinBox, QTabWidget,
    QVBoxLayout, QWidget,
)

try:
    from PyQt5.QtSvg import QSvgRenderer
except ImportError:
    QSvgRenderer = None

try:
    from PyQt5.QtMultimedia import QAudio, QAudioFormat, QAudioOutput
except ImportError:
    QAudio = QAudioFormat = QAudioOutput = None

try:
    from .instruments_engine import (
        RATE, TRACKS, DRUMS, DEFAULT_MIDI, PRESETS,
        Pattern, note_name, synthesize, render_loop, write_wav,
    )
except ImportError:
    from instruments_engine import (
        RATE, TRACKS, DRUMS, DEFAULT_MIDI, PRESETS,
        Pattern, note_name, synthesize, render_loop, write_wav,
    )

# MIDI numbering (C4 = 60). Guitar E2 A2 D3 G3 B3 E4; bass E1 A1 D2 G2.
GUITAR_OPEN = (40, 45, 50, 55, 59, 64)
BASS_OPEN = (28, 33, 38, 43)
KEYS_START = 48
ACCENT = "#a77aff"

class InstrumentWorkbench(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("spiderAudioInstrumentWorkbench")
        art = Path(__file__).resolve().parents[1] / "branding/spider-apps/backgrounds/spider-audio-studio.svg"
        self._background = QSvgRenderer(str(art)) if QSvgRenderer is not None and art.is_file() else None
        self.setMinimumSize(670, 430)
        self.pattern = Pattern.preset("Rock")
        self.selected = dict(DEFAULT_MIDI)
        self._voices = []
        self._playhead = 0
        self._buttons = {}
        self._preview_supported = QAudioOutput is not None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.setStyleSheet("""
            QWidget#spiderAudioInstrumentWorkbench { background:transparent; }
            QFrame#spiderInstrumentSurface, QTabWidget::pane {
                background:#121022; border:1px solid #6443a0; border-radius:12px; }
            QLabel { background:transparent; color:#ede4ff; }
            QPushButton { min-height:25px; background:#272038; color:#f0e9fa;
                border:1px solid #66517f; border-radius:5px; padding:5px; }
            QPushButton:hover { border:1px solid #c2a7fd; background:#42305d; }
            QPushButton:checked { background:#7045ba; border:1px solid #d1b6ff; }
            QTabBar::tab { background:#201b34; color:#e6d9ff; padding:10px; }
            QTabBar::tab:selected { background:#7045ba; }
            QComboBox, QSpinBox { background:#241b38; color:white; padding:5px; }
        """)
        outer = QVBoxLayout(self)
        heading = QLabel("SPIDER AUDIO STUDIO  /  LIVE INSTRUMENTS")
        heading.setFont(QFont("Sans Serif", 18, QFont.Bold))
        heading.setStyleSheet("color:#d5b8ff")
        outer.addWidget(heading)
        note = QLabel("Original Spider synthesizers · Playable instruments · 16-step sequencing · WAV export")
        outer.addWidget(note)
        row = QHBoxLayout()
        self.tempo = QSpinBox()
        self.tempo.setRange(40, 240)
        self.tempo.setValue(self.pattern.bpm)
        self.tempo.setSuffix(" BPM")
        self.tempo.valueChanged.connect(self._change_tempo)
        row.addWidget(QLabel("Tempo"))
        row.addWidget(self.tempo)
        self.play_btn = QPushButton("▶ Play pattern")
        self.play_btn.clicked.connect(self._toggle_play)
        row.addWidget(self.play_btn)
        row.addWidget(self._action("Clear pattern", self._clear_pattern))
        row.addWidget(self._action("Save project", self._save_project))
        row.addWidget(self._action("Open project", self._open_project))
        row.addWidget(self._action("Export WAV", self._export_wav))
        outer.addLayout(row)

        self.tabs = QTabWidget(self)
        outer.addWidget(self.tabs, 1)
        self.tabs.addTab(self._build_sequencer(), "Drum Machine + Sequencer")
        self.tabs.addTab(self._build_fretboard("guitar", GUITAR_OPEN), "Guitar Machine")
        self.tabs.addTab(self._build_fretboard("bass", BASS_OPEN), "Bass Machine")
        self.tabs.addTab(self._build_keys(), "Keyboard + Synth")

        self.status = QLabel("Ready. Click pads, frets or keys to play, or sequence a pattern.")
        self.status.setWordWrap(True)
        outer.addWidget(self.status)
        if not self._preview_supported:
            self.status.setText("Qt Multimedia unavailable: editing and WAV export work, live audio needs PyQt5.QtMultimedia.")
        self._update_grid()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        fade = QLinearGradient(0, 0, self.width(), self.height())
        fade.setColorAt(0, QColor("#080715"))
        fade.setColorAt(.5, QColor("#17112a"))
        fade.setColorAt(1, QColor("#090816"))
        if self._background is not None and self._background.isValid():
            self._background.render(painter, QRectF(self.rect()))
            painter.fillRect(self.rect(), QColor(8, 7, 18, 115))
            painter.end()
            return
        painter.fillRect(self.rect(), fade)
        painter.setPen(QPen(QColor(138, 89, 220, 55), 1))
        for x in range(0, self.width(), 36):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), 36):
            painter.drawLine(0, y, self.width(), y)
        painter.end()

    def _action(self, text, slot):
        b = QPushButton(text)
        b.clicked.connect(slot)
        return b

    def _panel(self):
        panel = QFrame()
        panel.setObjectName("spiderInstrumentSurface")
        return panel

    def _build_sequencer(self):
        page = self._panel()
        layout = QVBoxLayout(page)
        pads = QHBoxLayout()
        for track in TRACKS[:4]:
            pads.addWidget(self._action(track.upper(), lambda checked=False, t=track: self._play_note(t)))
        layout.addLayout(pads)
        pattern_row = QHBoxLayout()
        pattern_row.addWidget(QLabel("Starter groove"))
        presets = QComboBox()
        presets.addItems(["Custom", *PRESETS])
        presets.currentTextChanged.connect(self._preset_selected)
        pattern_row.addWidget(presets)
        pattern_row.addStretch()
        layout.addLayout(pattern_row)
        grid = QGridLayout()
        grid.setHorizontalSpacing(3)
        grid.setVerticalSpacing(5)
        grid.addWidget(QLabel("TRACK"), 0, 0)
        for step in range(16):
            number = QLabel(str(step + 1))
            number.setAlignment(Qt.AlignCenter)
            grid.addWidget(number, 0, step + 1)
        for row, track in enumerate(TRACKS, 1):
            label = QLabel(track.upper())
            label.setMinimumWidth(69)
            grid.addWidget(label, row, 0)
            for step in range(16):
                button = QPushButton("·")
                button.setCheckable(True)
                button.setMinimumWidth(24)
                button.setMaximumWidth(44)
                button.setToolTip(f"{track.title()} · step {step + 1}")
                button.clicked.connect(
                    lambda checked=False, t=track, s=step: self._toggle_step(t, s))
                grid.addWidget(button, row, step + 1)
                self._buttons[(track, step)] = button
        layout.addLayout(grid)
        expl = QLabel("Select a fret or piano key, then click a Guitar, Bass or Keys step to place that note.")
        expl.setWordWrap(True)
        layout.addWidget(expl)
        layout.addStretch()
        scroller = QScrollArea()
        scroller.setWidgetResizable(True)
        scroller.setWidget(page)
        return scroller

    def _build_fretboard(self, instrument, strings):
        page = self._panel()
        layout = QVBoxLayout(page)
        title = "GUITAR / PLAY THE STRINGS" if instrument == "guitar" else "BASS / PLAY THE STRINGS"
        layout.addWidget(QLabel(title))
        layout.addWidget(QLabel("Click any fret for a real synthesized plucked tone; selected note goes into the step sequencer."))
        grid = QGridLayout()
        grid.addWidget(QLabel("STRING"), 0, 0)
        for fret in range(8):
            grid.addWidget(QLabel("OPEN" if fret == 0 else str(fret)), 0, fret + 1)
        for row, open_note in enumerate(reversed(strings), 1):
            grid.addWidget(QLabel(note_name(open_note)), row, 0)
            for fret in range(8):
                pitch = open_note + fret
                b = self._action(note_name(pitch),
                    lambda checked=False, t=instrument, p=pitch: self._play_note(t, p))
                b.setToolTip(f"{instrument.title()} {note_name(pitch)} · MIDI {pitch}")
                grid.addWidget(b, row, fret + 1)
        layout.addLayout(grid)
        layout.addStretch()
        return page

    def _build_keys(self):
        page = self._panel()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("SPIDER KEYS / TWO-OCTAVE PLAYABLE KEYBOARD"))
        layout.addWidget(QLabel("Play the keys, then place the selected note on the Keys track."))
        grid = QGridLayout()
        for pos in range(25):
            midi = KEYS_START + pos
            key = self._action(note_name(midi),
                lambda checked=False, p=midi: self._play_note("keys", p))
            if midi % 12 in (1, 3, 6, 8, 10):
                key.setStyleSheet("background:#181224; color:#e9d8ff; border:1px solid #7a54a1;")
            else:
                key.setStyleSheet("background:#e7dcf6; color:#1a1424; border:1px solid #856bb1;")
            grid.addWidget(key, pos // 13, pos % 13)
        layout.addLayout(grid)
        layout.addWidget(QLabel("Keyboard shortcuts: A W S E D F T G Y H U J play the first 12 notes."))
        keys = "AWSEDFTGYHUJ"
        for offset, letter in enumerate(keys):
            shortcut = QShortcut(QKeySequence(letter), self)
            shortcut.setContext(Qt.WidgetWithChildrenShortcut)
            shortcut.activated.connect(lambda n=KEYS_START + offset: self._shortcut_key(n))
        layout.addStretch()
        return page

    def _shortcut_key(self, midi):
        if self.tabs.currentIndex() == 3:
            self._play_note("keys", midi)

    def _change_tempo(self, tempo):
        self.pattern.bpm = tempo
        if self.timer.isActive():
            self.timer.setInterval(max(20, round(60000 / (tempo * 4))))

    def _preset_selected(self, name):
        if name in PRESETS:
            bpm = self.tempo.value()
            self.pattern = Pattern.preset(name)
            self.pattern.bpm = bpm
            self._update_grid()

    def _toggle_step(self, track, step):
        if self.pattern.events[track][step] is None:
            self.pattern.set(track, step, None if track in DRUMS else self.selected[track])
        else:
            self.pattern.clear(track, step)
        self._update_grid()

    def _update_grid(self):
        for (track, step), button in self._buttons.items():
            value = self.pattern.events[track][step]
            button.setChecked(value is not None)
            button.setText(note_name(value) if type(value) is int else ("●" if value else "·"))
            button.setStyleSheet(
                "border:2px solid #e8caff;" if step == self._playhead and self.timer.isActive() else "")
            if type(value) is int:
                button.setToolTip(f"{track} step {step + 1}: {note_name(value)}")
            else:
                button.setToolTip(f"{track} step {step + 1}")

    def _play_note(self, instrument, pitch=None):
        if instrument not in DRUMS:
            if pitch is None:
                pitch = self.selected[instrument]
            self.selected[instrument] = pitch
        try:
            pcm = synthesize(instrument, pitch if instrument not in DRUMS else None)
            self._audio(pcm)
            name = note_name(pitch) if instrument not in DRUMS else "pad"
            self.status.setText(f"{instrument.title()}: {name} selected and triggered.")
        except (ValueError, RuntimeError) as error:
            self.status.setText(str(error))

    def _audio(self, pcm):
        if not self._preview_supported:
            return
        audioformat = QAudioFormat()
        audioformat.setSampleRate(RATE)
        audioformat.setChannelCount(1)
        audioformat.setSampleSize(16)
        audioformat.setCodec("audio/pcm")
        audioformat.setByteOrder(QAudioFormat.LittleEndian)
        audioformat.setSampleType(QAudioFormat.SignedInt)
        audio = QAudioOutput(audioformat, self)
        data = QBuffer(audio)
        data.setData(QByteArray(pcm))
        data.open(QIODevice.ReadOnly)
        self._voices.append((audio, data))
        audio.stateChanged.connect(lambda state, player=audio: self._voice_state(player, state))
        audio.setVolume(0.55)
        audio.start(data)

    def _voice_state(self, player, state):
        if QAudio is not None and state in (QAudio.IdleState, QAudio.StoppedState):
            def remove():
                player.stop()
                self._voices = [v for v in self._voices if v[0] is not player]
                player.deleteLater()
            QTimer.singleShot(0, remove)

    def _toggle_play(self):
        if self.timer.isActive():
            self.timer.stop()
            self.play_btn.setText("▶ Play pattern")
        else:
            self._playhead = 0
            self.timer.start(max(20, round(60000 / (self.tempo.value() * 4))))
            self.play_btn.setText("■ Stop")
            self._tick()
        self._update_grid()

    def _tick(self):
        for track in TRACKS:
            value = self.pattern.events[track][self._playhead]
            if value is not None:
                try:
                    self._audio(synthesize(track, value if track not in DRUMS else None))
                except (ValueError, RuntimeError):
                    self.timer.stop()
                    self.status.setText("Audio playback stopped due to an output error.")
                    break
        self._playhead = (self._playhead + 1) % 16
        self._update_grid()

    def _clear_pattern(self):
        self.pattern = Pattern(bpm=self.tempo.value())
        self._update_grid()
        self.status.setText("Cleared pattern. Previously saved projects are unchanged.")

    def _save_project(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Spider pattern", str(Path.home() / "Music" / "Spider-Pattern.json"),
            "Spider Pattern (*.json)")
        if not filename:
            return
        target = Path(filename)
        temporary = None
        try:
            fd, temporary = tempfile.mkstemp(dir=str(target.parent), prefix=".spider-pattern-", suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(self.pattern.as_dict(), stream, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
            self.status.setText(f"Saved pattern: {target.name}")
        except OSError as error:
            self.status.setText(f"Could not save: {error}")
        finally:
            if temporary is not None:
                Path(temporary).unlink(missing_ok=True)

    def _open_project(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Open Spider pattern",
            str(Path.home() / "Music"), "Spider Pattern (*.json)")
        if not filename:
            return
        try:
            target = Path(filename)
            if target.stat().st_size > 128 * 1024:
                raise ValueError("Project exceeds the supported file size")
            pattern = Pattern.from_dict(json.loads(target.read_text("utf-8")))
            if self.timer.isActive():
                self._toggle_play()
            self.pattern = pattern
            self.tempo.setValue(pattern.bpm)
            self._update_grid()
            self.status.setText(f"Loaded pattern: {target.name}")
        except (ValueError, OSError, UnicodeError, json.JSONDecodeError) as error:
            QMessageBox.warning(self, "Invalid Spider pattern", str(error)[:300])

    def _export_wav(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Spider Audio WAV", str(Path.home() / "Music" / "Spider-Loop.wav"),
            "WAV audio (*.wav)")
        if not filename:
            return
        try:
            pcm = render_loop(self.pattern)
            write_wav(filename, pcm)
            self.status.setText(f"Exported 44.1 kHz / 16-bit mono WAV: {Path(filename).name}")
        except (OSError, ValueError, RuntimeError) as error:
            QMessageBox.warning(self, "Export failed", str(error)[:300])

    def closeEvent(self, event):
        self.timer.stop()
        for audio, data in list(self._voices):
            audio.stop()
        self._voices.clear()
        super().closeEvent(event)
