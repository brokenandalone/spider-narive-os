"""Native song creation and saved-take audition, using an explicit local engine."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading

from PyQt5.QtCore import QThread, QTimer, QUrl, pyqtSignal
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPlainTextEdit, QProgressBar, QPushButton, QSpinBox, QVBoxLayout, QWidget)
from PyQt5.QtCore import Qt

if __package__:
    from .music_backend import LocalMusicClient, SongRequest, MusicError
    from .tools import TOOLS, resolve_tool
    from .arrangement import VOICE_OPTIONS
    from .voice_profile import (start_capture, finish_capture, import_sample, samples, VoiceSampleError)
else:
    from music_backend import LocalMusicClient, SongRequest, MusicError
    from tools import TOOLS, resolve_tool
    from arrangement import VOICE_OPTIONS
    from voice_profile import (start_capture, finish_capture, import_sample, samples, VoiceSampleError)

BROKEN_SORROW = ('Dark Southern gothic metal, post-grunge and modern hard rock; '
    'deep baritone, intimate haunted verses, cracked-clean choruses, selective '
    'controlled screams, heavy seven-string guitars, cinematic piano, organic drums.')


class MusicWorker(QThread):
    progress = pyqtSignal(str)
    result = pyqtSignal(str, str)

    def __init__(self, client, request, output):
        # Survives a bay/window closing; no QThread destruction while running.
        super().__init__(QApplication.instance())
        self.client, self.request, self.output = client, request, output
        self.stop = threading.Event()
        QApplication.instance().aboutToQuit.connect(self.shutdown)

    def shutdown(self):
        self.stop.set()
        self.wait()

    def run(self):
        try:
            if self.request is None:
                self.client.health()
                self.result.emit('', 'Local music engine is responding. A real render is still needed to test readiness.')
            else:
                path = self.client.generate(self.request, self.output, self.stop, self.progress.emit)
                self.result.emit(str(path), 'Takes saved. Select one to listen or export.')
        except Exception as error:
            self.result.emit('', str(error) if isinstance(error, (MusicError, ValueError))
                             else 'Music operation failed. Check the local engine and saved job status.')


class StudioAIPanel(QWidget):
    def __init__(self, output_root=None):
        super().__init__()
        self.output_root = Path(output_root) if output_root else Path.home() / 'Documents/Spider Studio/Music/AI Songs'
        self.worker = None
        self.capture_proc = None
        self.capture_file = None
        self.capture_timer = QTimer(self)
        self.capture_timer.timeout.connect(self.poll_capture)
        layout = QVBoxLayout(self)
        heading = QLabel('Create a song')
        heading.setStyleSheet('font-size:22px; color:#c4b5fd;')
        layout.addWidget(heading)
        self.status = QLabel('Uses your local ACE-Step engine. No engine or model is installed automatically.')
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.PlainText)
        layout.addWidget(self.status)
        form = QFormLayout()
        self.title = QLineEdit(); self.title.setPlaceholderText('Song title')
        self.style = QPlainTextEdit(); self.style.setPlaceholderText('Genre, mood, instruments and vocal direction')
        self.style.setMaximumHeight(85)
        self.lyrics = QPlainTextEdit(); self.lyrics.setPlaceholderText('[Verse]\nYour lyrics\n\n[Chorus]\nYour chorus')
        self.lyrics.setMaximumHeight(140)
        self.instrumental = QCheckBox('Instrumental')
        self.instrumental.toggled.connect(self.lyrics.setDisabled)
        self.duration = QSpinBox(); self.duration.setRange(10, 600); self.duration.setValue(180); self.duration.setSuffix(' seconds')
        self.takes = QSpinBox(); self.takes.setRange(1, 2); self.takes.setValue(2)
        self.bpm = QSpinBox(); self.bpm.setRange(0, 300); self.bpm.setSpecialValueText('Automatic')
        for name, field in (('Title', self.title), ('Style', self.style), ('Lyrics', self.lyrics),
                            ('', self.instrumental), ('Length', self.duration), ('Takes', self.takes), ('Tempo', self.bpm)):
            form.addRow(name, field)
        layout.addLayout(form)

        band_heading = QLabel('Band arrangement')
        band_heading.setStyleSheet('font-size:18px; color:#c4b5fd;')
        layout.addWidget(band_heading)
        notice = QLabel('Singer labels guide original vocal roles, not cloned real voices. '
                        'Guitar parts are mixed in the generated WAV, not independent stems. '
                        'Use [Singer 1], [Singer 2], etc. in lyrics to request handoffs.')
        notice.setWordWrap(True)
        layout.addWidget(notice)
        band = QFormLayout()
        self.voice_boxes = []
        for number, default in ((1, 'Justin Therapy (original baritone)'),
                                (2, 'None'), (3, 'None')):
            combo = QComboBox()
            combo.addItems(VOICE_OPTIONS)
            combo.setCurrentText(default)
            self.voice_boxes.append(combo)
            band.addRow(f'Singer {number}', combo)
        self.voice_notes = QPlainTextEdit()
        self.voice_notes.setPlaceholderText('Optional vocal roles, harmonies or who sings each section. Give Jason/J-Cold an original vocal description here.')
        self.voice_notes.setMaximumHeight(65)
        band.addRow('Singer directions', self.voice_notes)
        self.guitar_one = QLineEdit('Downtuned seven-string rhythm guitar, tight muted riffs and heavy chord accents')
        self.guitar_two = QLineEdit('Distinct melodic lead guitar, soaring harmony lines and expressive solo fills')
        self.two_guitarists = QCheckBox('Include second guitarist')
        self.two_guitarists.setChecked(True)
        self.two_guitarists.toggled.connect(self.guitar_two.setEnabled)
        band.addRow('Guitarist 1', self.guitar_one)
        band.addRow('', self.two_guitarists)
        band.addRow('Guitarist 2', self.guitar_two)
        self.other_instruments = QLineEdit('Bass guitar, live acoustic drums, atmospheric piano')
        band.addRow('Rest of band', self.other_instruments)
        layout.addLayout(band)

        voice_heading = QLabel('My Voice: record first, build a personal voice model next')
        voice_heading.setStyleSheet('font-size:18px; color:#c4b5fd;')
        layout.addWidget(voice_heading)
        voice_disclaimer = QLabel('Recording your voice does not train a singing-voice model. '
            'A stored sample can experimentally influence ACE-Step via reference audio; '
            'matching your identity, improving pitch, and retaining you as lead are NOT guaranteed. '
            'The separate trained voice-conversion stage is pending local model setup and tests.')
        voice_disclaimer.setWordWrap(True)
        layout.addWidget(voice_disclaimer)
        voice_form = QFormLayout()
        self.vocal_mode = QComboBox()
        self.vocal_mode.addItem('Generate original AI lead singer(s)', 'ai_lead')
        self.vocal_mode.addItem('Arrange guest singers around my recording (experimental cover)', 'with_my_vocal')
        self.vocal_mode.addItem('Continue music from my recording (experimental)', 'backing_for_my_vocal')
        voice_form.addRow('Vocal workflow', self.vocal_mode)
        self.source_audio = QLineEdit()
        self.source_audio.setPlaceholderText('Choose an existing vocal WAV/MP3/FLAC recording')
        self.source_browse = QPushButton('Choose recorded vocals')
        self.source_browse.clicked.connect(self.choose_source)
        voice_form.addRow('Input recording', self.source_audio)
        voice_form.addRow('', self.source_browse)
        self.use_voice_reference = QCheckBox('Use latest My Voice sample as experimental style reference')
        voice_form.addRow('', self.use_voice_reference)
        layout.addLayout(voice_form)
        voice_buttons = QHBoxLayout()
        self.record_button = QPushButton('Record 30-second My Voice sample')
        self.record_button.clicked.connect(self.record_voice)
        self.import_button = QPushButton('Import my vocal sample')
        self.import_button.clicked.connect(self.import_voice)
        self.voice_status = QLabel('No trained voice model. Recording is opt-in and kept on this computer.')
        self.voice_status.setWordWrap(True)
        voice_buttons.addWidget(self.record_button)
        voice_buttons.addWidget(self.import_button)
        layout.addLayout(voice_buttons)
        layout.addWidget(self.voice_status)
        QApplication.instance().aboutToQuit.connect(self.cancel_capture)
        self.update_voice_status()
        buttons = QHBoxLayout()
        self.preset = QPushButton('Broken Sorrow preset')
        self.preset.clicked.connect(lambda: self.style.setPlainText(BROKEN_SORROW))
        self.check = QPushButton('Check local engine'); self.check.clicked.connect(lambda: self.start(check_only=True))
        self.generate = QPushButton('Generate song'); self.generate.clicked.connect(lambda: self.start())
        self.stop = QPushButton('Stop waiting'); self.stop.setEnabled(False); self.stop.clicked.connect(self.stop_waiting)
        for button in (self.preset, self.check, self.generate, self.stop):
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.busy = QProgressBar(); self.busy.setRange(0, 1); self.busy.setValue(0); layout.addWidget(self.busy)
        layout.addWidget(QLabel('Saved takes'))
        self.library = QListWidget(); layout.addWidget(self.library)
        actions = QHBoxLayout()
        for label, action in (('Play selected take', self.play), ('Export WAV', self.export), ('Edit in Audacity', self.edit_audio), ('Refresh takes', self.refresh)):
            button = QPushButton(label); button.clicked.connect(action); actions.addWidget(button)
        layout.addLayout(actions)
        self.refresh()

    def update_voice_status(self):
        count = len(samples())
        self.voice_status.setText(f'{count} private My Voice recording(s) collected. '
            'Training and consistent AI singing in your actual voice require a separate voice model.')

    def choose_source(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Select vocal performance',
            str(Path.home() / 'Music'), 'Audio (*.wav *.mp3 *.flac)')
        if path:
            self.source_audio.setText(path)

    def import_voice(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Import a recording of your own voice',
            str(Path.home() / 'Music'), 'Audio (*.wav *.mp3 *.flac)')
        if not path:
            return
        try:
            import_sample(path, consent=True)
            self.update_voice_status()
            self.status.setText('Voice sample saved privately. No model has been trained yet.')
        except (OSError, VoiceSampleError) as error:
            self.status.setText(str(error))

    def record_voice(self):
        if self.capture_proc is not None:
            self.finish_voice(stop=True)
            return
        try:
            self.capture_proc, self.capture_file = start_capture(seconds=30)
            self.record_button.setText('Stop recording and keep sample')
            self.voice_status.setText('Recording your voice for up to 30 seconds. Microphone is active.')
            self.capture_timer.start(500)
        except (OSError, VoiceSampleError) as error:
            self.status.setText(str(error))

    def poll_capture(self):
        if self.capture_proc is not None and self.capture_proc.poll() is not None:
            self.finish_voice(stop=False)

    def finish_voice(self, stop=False):
        self.capture_timer.stop()
        proc, path = self.capture_proc, self.capture_file
        self.capture_proc, self.capture_file = None, None
        if proc is None:
            return
        self.record_button.setText('Record 30-second My Voice sample')
        try:
            finish_capture(proc, path, stop=stop)
            self.update_voice_status()
            self.status.setText('My Voice sample saved. A trained voice model is still needed for identity-matched singing.')
        except (OSError, VoiceSampleError) as error:
            self.status.setText(str(error))

    def cancel_capture(self):
        if self.capture_proc is not None:
            self.finish_voice(stop=True)

    def closeEvent(self, event):
        self.cancel_capture()
        super().closeEvent(event)

    def start(self, check_only=False):
        if self.worker is not None:
            return
        try:
            client = LocalMusicClient(os.environ.get('SPIDER_MUSIC_URL', 'http://127.0.0.1:8001'),
                                      os.environ.get('ACESTEP_API_KEY'))
            singers = tuple(box.currentText() for box in self.voice_boxes
                            if box.currentText() != 'None')
            own = samples() if self.use_voice_reference.isChecked() and not check_only else []
            if self.use_voice_reference.isChecked() and not own and not check_only:
                raise ValueError('Record or import a My Voice sample first.')
            request = None if check_only else SongRequest(
                self.title.text(), self.style.toPlainText(), self.lyrics.toPlainText(),
                self.instrumental.isChecked(), self.duration.value(), self.takes.value(), self.bpm.value(),
                vocal_lineup=singers, vocal_notes=self.voice_notes.toPlainText(),
                guitar_one=self.guitar_one.text(),
                guitar_two=self.guitar_two.text() if self.two_guitarists.isChecked() else '',
                other_instruments=self.other_instruments.text(),
                vocal_mode=self.vocal_mode.currentData(),
                source_audio=self.source_audio.text().strip() if self.vocal_mode.currentData() != 'ai_lead' else '',
                voice_reference=str(own[0]) if own else '')
            if request:
                request.payload()
        except ValueError as error:
            self.status.setText(str(error)); return
        self.worker = MusicWorker(client, request, self.output_root)
        self.worker.progress.connect(self.status.setText)
        self.worker.result.connect(self.completed)
        self.worker.finished.connect(self.finished)
        self.destroyed.connect(lambda _=None, stop=self.worker.stop: stop.set())
        self.check.setEnabled(False); self.generate.setEnabled(False)
        self.stop.setEnabled(not check_only); self.busy.setRange(0, 0)
        self.status.setText('Checking local music engine…')
        self.worker.start()

    def completed(self, folder, message):
        self.status.setText(message)
        self.refresh()

    def finished(self):
        worker, self.worker = self.worker, None
        self.check.setEnabled(True); self.generate.setEnabled(True); self.stop.setEnabled(False)
        self.busy.setRange(0, 1); self.busy.setValue(0)
        if worker is not None:
            worker.deleteLater()

    def stop_waiting(self):
        if self.worker:
            self.worker.stop.set()
            self.stop.setEnabled(False)
            self.status.setText('Stopping this wait. The local engine may continue rendering; its task ID is saved.')

    def refresh(self):
        self.library.clear()
        if not self.output_root.exists():
            return
        for path in sorted(self.output_root.glob('song-*/job.json'), reverse=True):
            try:
                job = json.loads(path.read_text())
                for name in job.get('files', []):
                    if name not in ('take-1.wav', 'take-2.wav'):
                        continue
                    take = path.parent / name
                    if take.is_symlink() or not take.is_file() or self.output_root.resolve() not in take.resolve().parents:
                        continue
                    item = QListWidgetItem(f"{job['request']['title']} • {name} • {path.parent.name}")
                    item.setData(Qt.UserRole, str(take)); self.library.addItem(item)
            except (OSError, ValueError, KeyError, TypeError):
                continue

    def selected(self):
        item = self.library.currentItem()
        return Path(item.data(Qt.UserRole)) if item else None

    def play(self):
        path = self.selected()
        if path and not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
            self.status.setText('No audio player opened. Use Export WAV to open the take in your DAW.')

    def edit_audio(self):
        source = self.selected()
        if not source:
            self.status.setText('Select a take first.'); return
        tool = next(t for t in TOOLS['Recording & mixing'] if t[0] == 'Audacity')
        command = resolve_tool(tool)
        if not command:
            self.status.setText('Audacity is not available. Export WAV for your installed DAW.'); return
        try:
            subprocess.Popen([*command, str(source)])
            self.status.setText('Requested Audacity for the selected take.')
        except OSError:
            self.status.setText('Could not launch Audacity.')

    def export(self):
        source = self.selected()
        if not source:
            self.status.setText('Select a saved take first.'); return
        name, _ = QFileDialog.getSaveFileName(self, 'Export take', source.name, 'WAV audio (*.wav)')
        if name:
            try:
                target = Path(name)
                if source.resolve() != target.resolve():
                    shutil.copyfile(source, target)
                self.status.setText('WAV exported.')
            except OSError:
                self.status.setText('Could not export the take to that location.')
