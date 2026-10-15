"""Actual song arrangement / mixer panel inside the real Spider Studio bay.

Works with the instrument workbench's current pattern. Song exports happen in
a worker thread; no external audio engine, launcher or privileged command.
"""
from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QMessageBox, QPushButton, QScrollArea,
    QSlider, QSpinBox, QVBoxLayout, QWidget,
)
try:
    from .instruments_engine import TRACKS, Pattern
    from .song_arranger_engine import (
        MAX_BARS, Bar, Channel, Song, export_stems, load_song, save_song,
        song_duration, write_song_wav,
    )
except ImportError:
    from instruments_engine import TRACKS, Pattern
    from song_arranger_engine import (
        MAX_BARS, Bar, Channel, Song, export_stems, load_song, save_song,
        song_duration, write_song_wav,
    )

class SongRenderWorker(QThread):
    completed = pyqtSignal(bool, str)

    def __init__(self, song, destination, stems=False, parent=None):
        super().__init__(parent)
        # Eager validated copy prevents GUI edits racing against the export.
        self.song = Song.from_dict(song.as_dict())
        self.destination = str(destination)
        self.stems = bool(stems)

    def run(self):
        try:
            if self.stems:
                files = export_stems(self.song, self.destination)
                msg = f"Exported {len(files)} independent stereo stem files."
            else:
                write_song_wav(self.song, self.destination)
                msg = "Full song exported as stereo 44.1 kHz WAV."
            self.completed.emit(True, msg)
        except (OSError, ValueError, RuntimeError) as error:
            self.completed.emit(False, str(error)[:350])

class SongProductionPanel(QWidget):
    def __init__(self, workbench, parent=None):
        super().__init__(parent)
        self.workbench = workbench
        self.song = Song(bpm=workbench.tempo.value())
        self.worker = None
        self.setObjectName("spiderSongProductionPanel")
        self.setStyleSheet("""
            QWidget#spiderSongProductionPanel {background:#100c1d;color:#eae2fa;}
            QLabel {color:#e9defb;}
            QPushButton {background:#292039;color:#f5ebff;border:1px solid #69538b;
              border-radius:7px;padding:8px;min-height:30px;}
            QPushButton:hover {background:#533a77;}
            QLineEdit,QSpinBox,QListWidget {background:#1c162b;color:#f8f1ff;
              border:1px solid #684b96;padding:6px;}
            QSlider::groove:horizontal {height:7px;background:#3b2a50;}
            QSlider::handle:horizontal {background:#b991ff;width:14px;}
        """)
        main = QVBoxLayout(self)
        main.addWidget(QLabel("SONG ARRANGER / MULTITRACK MIXER"))
        main.addWidget(QLabel(
            "Capture bars from Play Instruments, arrange their order, mix each instrument, "
            "and export a stereo song or individual stems. No original files are modified."))
        header = QHBoxLayout()
        self.title = QLineEdit(self.song.title)
        self.title.setMaxLength(100)
        self.title.setPlaceholderText("Song title")
        header.addWidget(self.title, 1)
        self.tempo = QSpinBox()
        self.tempo.setRange(40, 240)
        self.tempo.setValue(self.song.bpm)
        self.tempo.setSuffix(" BPM")
        self.tempo.valueChanged.connect(self._tempo_changed)
        header.addWidget(self.tempo)
        main.addLayout(header)

        layout = QHBoxLayout()
        main.addLayout(layout, 1)
        column = QVBoxLayout()
        layout.addLayout(column, 2)
        column.addWidget(QLabel("SONG STRUCTURE · up to 32 editable bars"))
        self.bars = QListWidget()
        self.bars.currentRowChanged.connect(self._select_bar)
        column.addWidget(self.bars, 1)
        commands = QGridLayout()
        for index, (name, callback) in enumerate([
            ("+ Capture instrument pattern", self.capture_bar),
            ("Load bar into instruments", self.load_bar),
            ("Update bar from instruments", self.update_bar),
            ("Duplicate bar", self.duplicate_bar),
            ("Move earlier", lambda: self.move_bar(-1)),
            ("Move later", lambda: self.move_bar(1)),
            ("Remove bar", self.remove_bar),
            ("Clear song", self.clear_song),
        ]):
            b = QPushButton(name)
            b.clicked.connect(callback)
            commands.addWidget(b, index // 2, index % 2)
        column.addLayout(commands)

        mixer_side = QVBoxLayout()
        layout.addLayout(mixer_side, 3)
        mixer_side.addWidget(QLabel("MIXING CONSOLE · track gain / stereo pan / mute / solo"))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        strip = QGridLayout(container)
        strip.addWidget(QLabel("TRACK"), 0, 0)
        strip.addWidget(QLabel("GAIN"), 0, 1)
        strip.addWidget(QLabel("PAN"), 0, 2)
        strip.addWidget(QLabel("MUTE"), 0, 3)
        strip.addWidget(QLabel("SOLO"), 0, 4)
        self.controls = {}
        for row, track in enumerate(TRACKS, 1):
            strip.addWidget(QLabel(track.upper()), row, 0)
            gain = QSlider(Qt.Horizontal)
            gain.setRange(0, 100)
            gain.setValue(80)
            gain.setAccessibleName(track + " gain")
            pan = QSlider(Qt.Horizontal)
            pan.setRange(-100, 100)
            pan.setValue(0)
            pan.setAccessibleName(track + " stereo pan")
            mute = QCheckBox()
            mute.setAccessibleName(track + " mute")
            solo = QCheckBox()
            solo.setAccessibleName(track + " solo")
            strip.addWidget(gain, row, 1)
            strip.addWidget(pan, row, 2)
            strip.addWidget(mute, row, 3)
            strip.addWidget(solo, row, 4)
            self.controls[track] = (gain, pan, mute, solo)
            gain.valueChanged.connect(lambda value, t=track: self._mixer_changed(t, "gain", value))
            pan.valueChanged.connect(lambda value, t=track: self._mixer_changed(t, "pan", value))
            mute.toggled.connect(lambda checked, t=track: self._mixer_changed(t, "mute", checked))
            solo.toggled.connect(lambda checked, t=track: self._mixer_changed(t, "solo", checked))
        scroll.setWidget(container)
        mixer_side.addWidget(scroll, 1)
        output = QGridLayout()
        for index, (label, handler) in enumerate([
            ("Save song project", self.save),
            ("Open song project", self.open),
            ("Export stereo WAV", self.export_mix),
            ("Export all 7 stems", self.export_stems),
        ]):
            button = QPushButton(label)
            button.clicked.connect(handler)
            output.addWidget(button, index // 2, index % 2)
        mixer_side.addLayout(output)
        self.status = QLabel("Capture a drum, guitar, bass or keys pattern to begin arranging.")
        self.status.setWordWrap(True)
        main.addWidget(self.status)
        self._refresh_bars()

    def _song_validated(self):
        self.song.title = self.title.text().strip()
        self.song.bpm = self.tempo.value()
        return Song.from_dict(self.song.as_dict())

    def _tempo_changed(self, tempo):
        self.song.bpm = tempo
        for bar in self.song.bars:
            bar.pattern.bpm = tempo
        self._refresh_bars()

    def _mixer_changed(self, track, key, value):
        setattr(self.song.mixer[track], key, value)

    def _refresh_bars(self, selected=None):
        if selected is None:
            selected = self.bars.currentRow()
        self.bars.blockSignals(True)
        self.bars.clear()
        for i, bar in enumerate(self.song.bars, 1):
            count = sum(value is not None for track in TRACKS for value in bar.pattern.events[track])
            self.bars.addItem(f"{i:02d}  {bar.name}    · {count} notes/hits")
        if 0 <= selected < self.bars.count():
            self.bars.setCurrentRow(selected)
        self.bars.blockSignals(False)
        if self.song.bars:
            self.status.setText(
                f"{len(self.song.bars)} bars / {song_duration(self.song):.1f} seconds "
                f"at {self.song.bpm} BPM · save your project to preserve edits.")

    def _select_bar(self, selected):
        if 0 <= selected < len(self.song.bars):
            self.status.setText(
                f"Selected {self.song.bars[selected].name}. Use Load bar to edit it in Play Instruments.")

    def _selected_index(self):
        value = self.bars.currentRow()
        if not 0 <= value < len(self.song.bars):
            self.status.setText("Select a song bar first.")
            return None
        return value

    def capture_bar(self):
        if len(self.song.bars) >= MAX_BARS:
            self.status.setText("Maximum 32 bars. Duplicate or remove existing bars to reorganize.")
            return
        name = self.workbench.tabs.tabText(self.workbench.tabs.currentIndex())
        label = "Verse" if name.startswith("Drum") else name.split(" ")[0]
        try:
            self.song.capture(label, self.workbench.pattern)
            self._refresh_bars(len(self.song.bars) - 1)
        except ValueError as error:
            self.status.setText(str(error))

    def load_bar(self):
        selected = self._selected_index()
        if selected is None:
            return
        bar = self.song.bars[selected]
        # Explicit clone: no live binding while editing.
        self.workbench.pattern = Pattern.from_dict(bar.pattern.as_dict())
        self.workbench.tempo.setValue(self.song.bpm)
        self.workbench._update_grid()
        self.status.setText(
            f"Loaded {bar.name} into Play Instruments. Switch to that tab; "
            "use Update bar when you've finished changing its pattern.")

    def update_bar(self):
        selected = self._selected_index()
        if selected is None:
            return
        try:
            new_pattern = Pattern.from_dict(self.workbench.pattern.as_dict())
            new_pattern.bpm = self.song.bpm
            self.song.bars[selected].pattern = new_pattern
            self._refresh_bars(selected)
        except ValueError as error:
            self.status.setText(str(error))

    def duplicate_bar(self):
        selected = self._selected_index()
        if selected is None or len(self.song.bars) >= MAX_BARS:
            return
        source = self.song.bars[selected]
        self.song.bars.insert(selected + 1, Bar.from_dict(source.as_dict()))
        self._refresh_bars(selected + 1)

    def move_bar(self, direction):
        selected = self._selected_index()
        if selected is None:
            return
        target = selected + direction
        if 0 <= target < len(self.song.bars):
            self.song.bars[selected], self.song.bars[target] = (
                self.song.bars[target], self.song.bars[selected])
            self._refresh_bars(target)

    def remove_bar(self):
        selected = self._selected_index()
        if selected is None:
            return
        del self.song.bars[selected]
        self._refresh_bars(min(selected, len(self.song.bars) - 1))

    def clear_song(self):
        answer = QMessageBox.question(self, "Clear song?",
            "Discard the current song arrangement? Saved projects are unaffected.",
            QMessageBox.Yes | QMessageBox.No)
        if answer == QMessageBox.Yes:
            self.song.bars.clear()
            self._refresh_bars()
            self.status.setText("Cleared unsaved song arrangement.")

    def save(self):
        destination, _ = QFileDialog.getSaveFileName(
            self, "Save Spider song", str(Path.home() / "Music" / "Spider-Song.json"),
            "Spider Song (*.json)")
        if not destination:
            return
        try:
            song = self._song_validated()
            save_song(song, destination)
            self.status.setText(f"Saved: {Path(destination).name}")
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Save failed", str(error)[:300])

    def open(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open Spider song", str(Path.home() / "Music"),
            "Spider Song (*.json)")
        if not filename:
            return
        try:
            song = load_song(filename)
            self.song = song
            self.title.setText(song.title)
            self.tempo.setValue(song.bpm)
            for track in TRACKS:
                gain, pan, mute, solo = self.controls[track]
                channel = song.mixer[track]
                gain.setValue(channel.gain)
                pan.setValue(channel.pan)
                mute.setChecked(channel.mute)
                solo.setChecked(channel.solo)
            self._refresh_bars(0)
            self.status.setText(f"Opened: {Path(filename).name}")
        except (OSError, ValueError, UnicodeError) as error:
            QMessageBox.warning(self, "Open failed", str(error)[:300])

    def _start_export(self, destination, stems=False):
        if self.worker is not None and self.worker.isRunning():
            return
        try:
            song = self._song_validated()
            if not song.bars:
                raise ValueError("Add a song bar before exporting")
            self.worker = SongRenderWorker(song, destination, stems=stems, parent=self)
            self.worker.completed.connect(self._finish_export)
            self.worker.start()
            self.status.setText("Rendering safely in a worker. Your original project is untouched.")
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Cannot export", str(error)[:300])

    def _finish_export(self, ok, message):
        self.status.setText(message if ok else "Export failed: " + message)

    def export_mix(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Export Spider song WAV",
            str(Path.home() / "Music" / "Spider-Song.wav"), "WAV audio (*.wav)")
        if filename:
            self._start_export(filename)

    def export_stems(self):
        folder = QFileDialog.getExistingDirectory(self, "Select EMPTY folder for 7 WAV stems",
            str(Path.home() / "Music"))
        if folder:
            self._start_export(folder, stems=True)

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            event.ignore()
        else:
            super().closeEvent(event)
