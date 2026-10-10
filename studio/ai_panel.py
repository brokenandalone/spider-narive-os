"""Native song creation and saved-take audition, using an explicit local engine."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading

from PyQt5.QtCore import QThread, QTimer, QUrl, QProcess, pyqtSignal
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QDoubleSpinBox,
    QPlainTextEdit, QProgressBar, QPushButton, QSpinBox, QVBoxLayout, QWidget, QMessageBox)
from PyQt5.QtCore import Qt

if __package__:
    from .music_backend import LocalMusicClient, SongRequest, MusicError
    from .tools import TOOLS, resolve_tool
    from .arrangement import VOICE_OPTIONS
    from .voice_profile import (start_capture, finish_capture, import_sample, samples, VoiceSampleError)
    from .voice_conversion import convert_vocal, ConversionError
    from .voice_dataset import prepare_training_set, inspect_samples, MIN_TRAIN_SECONDS
    from .song_mix import mix_vocals, MixError, valid_wav
    from .stem_separation import separate, SeparationError
else:
    from music_backend import LocalMusicClient, SongRequest, MusicError
    from tools import TOOLS, resolve_tool
    from arrangement import VOICE_OPTIONS
    from voice_profile import (start_capture, finish_capture, import_sample, samples, VoiceSampleError)
    from voice_conversion import convert_vocal, ConversionError
    from voice_dataset import prepare_training_set, inspect_samples, MIN_TRAIN_SECONDS
    from song_mix import mix_vocals, MixError, valid_wav
    from stem_separation import separate, SeparationError

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


class VoiceConvertWorker(QThread):
    result = pyqtSignal(str, str)

    def __init__(self, model, vocal, index):
        super().__init__(QApplication.instance())
        self.model, self.vocal, self.index = model, vocal, index
        self.stop = threading.Event()
        QApplication.instance().aboutToQuit.connect(self.shutdown)

    def shutdown(self):
        self.stop.set()
        self.wait()

    def run(self):
        try:
            target = convert_vocal(self.model, self.vocal, index=self.index or None,
                                   stop=self.stop)
            self.result.emit(str(target), 'Converted isolated vocal saved. Mix it with the original backing in your DAW.')
        except Exception as error:
            self.result.emit('', str(error) if isinstance(error, ConversionError)
                             else 'Voice conversion failed. Check your trained model and local engine.')


class SeparationWorker(QThread):
    result = pyqtSignal(str, object, str)

    def __init__(self, source):
        super().__init__(QApplication.instance())
        self.source = source
        self.stop = threading.Event()
        QApplication.instance().aboutToQuit.connect(self.shutdown)

    def shutdown(self):
        self.stop.set()
        self.wait()

    def run(self):
        try:
            directory, stems = separate(self.source, stop=self.stop)
            self.result.emit(str(directory), [str(path) for path in stems],
                             f"Extracted {len(stems)} WAV candidates. Listen to each before assigning its role.")
        except Exception as error:
            self.result.emit("", [], str(error) if isinstance(error, SeparationError)
                             else "Stem separation failed. Check the installed RVC/PyMSS engine.")


class VoiceMixWorker(QThread):
    result = pyqtSignal(str, str)

    def __init__(self, backing, vocal, vocal_gain, backing_gain):
        super().__init__(QApplication.instance())
        self.backing, self.vocal = backing, vocal
        self.vocal_gain, self.backing_gain = vocal_gain, backing_gain
        self.stop = threading.Event()
        QApplication.instance().aboutToQuit.connect(self.shutdown)

    def shutdown(self):
        self.stop.set()
        self.wait()

    def run(self):
        try:
            output = mix_vocals(self.backing, self.vocal, vocal_gain=self.vocal_gain,
                                backing_gain=self.backing_gain, stop=self.stop)
            self.result.emit(str(output), "New final WAV mix saved; original backing and vocals unchanged.")
        except Exception as error:
            self.result.emit("", str(error) if isinstance(error, MixError)
                             else "Mix failed. Check FFmpeg and your selected audio files.")


class EngineCheckWorker(QThread):
    result = pyqtSignal(str)

    def __init__(self, script):
        super().__init__(QApplication.instance())
        self.script = str(script)
        QApplication.instance().aboutToQuit.connect(self.wait)

    def run(self):
        try:
            report = subprocess.run(['bash', self.script, '--check'],
                capture_output=True, text=True, timeout=12, check=True)
            self.result.emit(report.stdout[-3000:] or 'No readiness information was returned.')
        except (OSError, subprocess.TimeoutExpired, subprocess.CalledProcessError) as error:
            self.result.emit('Local voice-engine check failed: ' + str(error))


class TrainingReadinessWorker(QThread):
    result = pyqtSignal(object)

    def __init__(self):
        super().__init__(QApplication.instance())
        QApplication.instance().aboutToQuit.connect(self.wait)

    def run(self):
        try:
            self.result.emit(inspect_samples())
        except (OSError, VoiceSampleError) as error:
            self.result.emit({'error': str(error)})


class DatasetWorker(QThread):
    result = pyqtSignal(bool, str)

    def __init__(self):
        super().__init__(QApplication.instance())
        QApplication.instance().aboutToQuit.connect(self.wait)

    def run(self):
        try:
            folder = prepare_training_set(consent=True)
            self.result.emit(True, str(folder))
        except (OSError, VoiceSampleError) as error:
            self.result.emit(False, str(error))


class StudioAIPanel(QWidget):
    def __init__(self, output_root=None):
        super().__init__()
        self.output_root = Path(output_root) if output_root else Path.home() / 'Documents/Spider Studio/Music/AI Songs'
        self.worker = None
        self.rvc_worker = None
        self.dataset_worker = None
        self.readiness_worker = None
        self.engine_worker = None
        self.trainer = None
        self.training_script = Path(__file__).resolve().parent / 'package' / 'voice-engine.sh'
        self.last_training_set = None
        self.mix_worker = None
        self.separation_worker = None
        self.separation_directory = None
        self.separation_files = set()
        self.finish_after_conversion = False
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
        self.readiness_button = QPushButton('Check My Voice training readiness')
        self.readiness_button.clicked.connect(self.check_voice_readiness)
        self.readiness_details = QLabel('Select Check to measure usable singing recordings against the 10-minute minimum.')
        self.readiness_details.setWordWrap(True)
        self.dataset_button = QPushButton('Prepare private RVC training dataset')
        self.dataset_button.clicked.connect(self.prepare_dataset)
        self.voice_status = QLabel('No trained voice model. Recording is opt-in and kept on this computer.')
        self.voice_status.setWordWrap(True)
        voice_buttons.addWidget(self.record_button)
        voice_buttons.addWidget(self.import_button)
        layout.addLayout(voice_buttons)
        layout.addWidget(self.readiness_button)
        layout.addWidget(self.readiness_details)
        trainer_header = QLabel('Private voice trainer')
        trainer_header.setStyleSheet('font-size:18px; color:#c4b5fd;')
        layout.addWidget(trainer_header)
        self.engine_status = QLabel('Training requires the local RVC engine and a prepared, owner-approved dataset.')
        self.engine_status.setWordWrap(True)
        self.engine_status.setTextFormat(Qt.PlainText)
        layout.addWidget(self.engine_status)
        training_actions = QHBoxLayout()
        self.engine_check_button = QPushButton('Check training setup')
        self.engine_check_button.clicked.connect(self.check_training_engine)
        training_actions.addWidget(self.engine_check_button)
        self.training_launch_button = QPushButton('Open local RVC training interface')
        self.training_launch_button.clicked.connect(self.launch_trainer)
        training_actions.addWidget(self.training_launch_button)
        self.training_stop_button = QPushButton('Stop local trainer')
        self.training_stop_button.clicked.connect(self.stop_trainer)
        self.training_stop_button.setEnabled(False)
        training_actions.addWidget(self.training_stop_button)
        layout.addLayout(training_actions)
        layout.addWidget(self.dataset_button)
        training_set_actions = QHBoxLayout()
        self.open_dataset_button = QPushButton('Open prepared training set')
        self.open_dataset_button.setEnabled(False)
        self.open_dataset_button.clicked.connect(self.open_dataset)
        training_set_actions.addWidget(self.open_dataset_button)
        self.copy_dataset_button = QPushButton('Copy RVC training audio folder')
        self.copy_dataset_button.setEnabled(False)
        self.copy_dataset_button.clicked.connect(self.copy_dataset_path)
        training_set_actions.addWidget(self.copy_dataset_button)
        layout.addLayout(training_set_actions)
        layout.addWidget(self.voice_status)
        QApplication.instance().aboutToQuit.connect(self.cancel_capture)
        self.update_voice_status()

        rvc_heading = QLabel('Trained My Voice: offline vocal conversion')
        rvc_heading.setStyleSheet('font-size:18px; color:#c4b5fd;')
        layout.addWidget(rvc_heading)
        rvc_notice = QLabel('Requires a separately trained, trusted local RVC .pth model, optional .index, '
            'RVC dependencies and an isolated vocal WAV. It changes vocal timbre; it does not create '
            'new lyrics, correct bad notes, or automatically remix a complete song. Never load untrusted model files.')
        rvc_notice.setWordWrap(True)
        layout.addWidget(rvc_notice)
        convert_form = QFormLayout()
        self.rvc_model = QLineEdit()
        self.rvc_model.setPlaceholderText('Select your trained voice .pth file')
        self.rvc_index = QLineEdit()
        self.rvc_index.setPlaceholderText('Optional model .index file')
        self.rvc_vocal = QLineEdit()
        self.rvc_vocal.setPlaceholderText('Select an isolated vocal WAV, not a full music mix')
        convert_form.addRow('My Voice model', self.rvc_model)
        convert_form.addRow('RVC index', self.rvc_index)
        convert_form.addRow('Isolated singing', self.rvc_vocal)
        layout.addLayout(convert_form)
        conversion_actions = QHBoxLayout()
        for label, field, flt in (('Choose voice model', self.rvc_model, 'RVC model (*.pth)'),
                                   ('Choose voice index', self.rvc_index, 'RVC index (*.index)'),
                                   ('Choose isolated vocal', self.rvc_vocal, 'WAV vocals (*.wav)')):
            choose = QPushButton(label)
            choose.clicked.connect(lambda _=False, target=field, extension=flt: self.pick_conversion_file(target, extension))
            conversion_actions.addWidget(choose)
        layout.addLayout(conversion_actions)
        self.convert_button = QPushButton('Convert isolated vocal to My Voice')
        self.convert_button.clicked.connect(self.start_conversion)
        layout.addWidget(self.convert_button)
        self.finish_song_button = QPushButton('Convert My Voice and make final mix')
        self.finish_song_button.clicked.connect(self.start_song_finish)
        layout.addWidget(self.finish_song_button)

        separator_heading = QLabel("Separate generated-song vocals and backing")
        separator_heading.setStyleSheet("font-size:18px; color:#c4b5fd;")
        layout.addWidget(separator_heading)
        separator_description = QLabel("Select a generated WAV, extract stems with your local RVC/PyMSS model, "
            "then audition the output files before assigning them as lead vocal or backing. "
            "First use may download model weights.")
        separator_description.setWordWrap(True)
        layout.addWidget(separator_description)
        self.separation_source = QLineEdit()
        self.separation_source.setPlaceholderText("Generated full-song WAV")
        layout.addWidget(self.separation_source)
        separation_buttons = QHBoxLayout()
        self.select_separation = QPushButton("Choose generated WAV")
        self.select_separation.clicked.connect(lambda: self.pick_conversion_file(self.separation_source, "WAV (*.wav)"))
        separation_buttons.addWidget(self.select_separation)
        self.separate_button = QPushButton("Separate vocals and backing")
        self.separate_button.clicked.connect(self.start_separation)
        separation_buttons.addWidget(self.separate_button)
        layout.addLayout(separation_buttons)
        stem_review_notice = QLabel("Review the extracted WAV files. Listen before marking which one is the "
                                    "singing vocal and which is instrumental. Names alone are not proof.")
        stem_review_notice.setWordWrap(True)
        layout.addWidget(stem_review_notice)
        self.stem_candidates = QListWidget()
        self.stem_candidates.setMaximumHeight(135)
        layout.addWidget(self.stem_candidates)
        stem_review_actions = QHBoxLayout()
        for label, handler in (("Listen to stem", self.listen_stem),
                               ("Use as singing vocal", self.assign_vocal_stem),
                               ("Use as instrumental", self.assign_instrumental_stem),
                               ("Open stems folder", self.open_separated_folder)):
            action = QPushButton(label)
            action.clicked.connect(handler)
            stem_review_actions.addWidget(action)
        layout.addLayout(stem_review_actions)
        mix_heading = QLabel("Final song: combine My Voice with instrumental backing")
        mix_heading.setStyleSheet("font-size:18px; color:#c4b5fd;")
        layout.addWidget(mix_heading)
        mix_note = QLabel("Supply an instrumental WAV and the isolated converted vocal WAV. "
            "This makes a new mixed WAV without changing either source. "
            "A complete AI song still needs verified stem separation before using this.")
        mix_note.setWordWrap(True)
        layout.addWidget(mix_note)
        mix_form = QFormLayout()
        self.mix_backing = QLineEdit()
        self.mix_backing.setPlaceholderText("Select clean instrumental backing WAV")
        self.mix_vocal = QLineEdit()
        self.mix_vocal.setPlaceholderText("Converted My Voice WAV from RVC")
        self.mix_voice_gain = QDoubleSpinBox()
        self.mix_voice_gain.setRange(0.0, 2.0)
        self.mix_voice_gain.setSingleStep(0.05)
        self.mix_voice_gain.setValue(1.0)
        self.mix_back_gain = QDoubleSpinBox()
        self.mix_back_gain.setRange(0.0, 2.0)
        self.mix_back_gain.setSingleStep(0.05)
        self.mix_back_gain.setValue(1.0)
        for name, control in (("Instrumental WAV", self.mix_backing),
                              ("Converted vocal WAV", self.mix_vocal),
                              ("Vocal level", self.mix_voice_gain),
                              ("Backing level", self.mix_back_gain)):
            mix_form.addRow(name, control)
        layout.addLayout(mix_form)
        pick_mix = QHBoxLayout()
        for name, field in (("Choose backing", self.mix_backing),
                            ("Choose converted vocal", self.mix_vocal)):
            pick = QPushButton(name)
            pick.clicked.connect(lambda _=False, target=field: self.pick_conversion_file(target, "WAV (*.wav)"))
            pick_mix.addWidget(pick)
        layout.addLayout(pick_mix)
        self.mix_button = QPushButton("Export final WAV with My Voice")
        self.mix_button.clicked.connect(self.start_mix)
        layout.addWidget(self.mix_button)
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

    def pick_conversion_file(self, field, pattern):
        path, _ = QFileDialog.getOpenFileName(self, 'Select local voice asset',
                                              str(Path.home()), pattern)
        if path:
            field.setText(path)

    def start_song_finish(self):
        if self.rvc_worker is not None or self.mix_worker is not None:
            self.status.setText('An audio job is already running.')
            return
        try:
            backing = valid_wav(self.mix_backing.text().strip(), 'instrumental backing')
            vocal = valid_wav(self.rvc_vocal.text().strip(), 'isolated original vocal')
            if backing == vocal:
                raise MixError('Choose separate instrumental and vocal WAV files.')
            if not self.rvc_model.text().strip():
                raise MixError('Choose a trained local My Voice model first.')
        except (MixError, OSError) as error:
            self.status.setText(str(error))
            return
        # Validate the trained model before starting any background job.
        model = Path(self.rvc_model.text().strip()).expanduser()
        if model.is_symlink() or not model.is_file() or model.suffix.lower() != '.pth':
            self.status.setText('Choose an existing, trusted, trained My Voice .pth model.')
            return
        self.finish_after_conversion = True
        self.finish_song_button.setEnabled(False)
        self.start_conversion()

    def start_conversion(self):
        if self.rvc_worker is not None:
            return
        self.rvc_worker = VoiceConvertWorker(self.rvc_model.text(),
            self.rvc_vocal.text(), self.rvc_index.text())
        self.rvc_worker.result.connect(self.conversion_done)
        self.rvc_worker.finished.connect(self.conversion_finished)
        self.convert_button.setEnabled(False)
        self.status.setText('Converting isolated vocal with locally trained RVC model…')
        self.rvc_worker.start()

    def conversion_done(self, target, message):
        self.status.setText(message + ((' Saved: ' + target) if target else ''))
        if target:
            self.mix_vocal.setText(target)
        if self.finish_after_conversion:
            self.finish_after_conversion = False
            if target:
                self.start_mix()
            else:
                self.finish_song_button.setEnabled(True)

    def conversion_finished(self):
        worker, self.rvc_worker = self.rvc_worker, None
        self.convert_button.setEnabled(True)
        if worker is not None:
            worker.deleteLater()

    def start_separation(self):
        if self.separation_worker is not None:
            return
        try:
            source = str(valid_wav(self.separation_source.text().strip(), "generated song"))
        except (OSError, MixError) as error:
            self.status.setText(str(error))
            return
        self.separation_directory = None
        self.separation_files.clear()
        self.stem_candidates.clear()
        self.separation_worker = SeparationWorker(source)
        self.separation_worker.result.connect(self.separation_done)
        self.separation_worker.finished.connect(self.separation_finished)
        self.separate_button.setEnabled(False)
        self.status.setText("Extracting stems locally. Existing files are unchanged…")
        self.separation_worker.start()

    def separation_done(self, directory, candidates, message):
        self.status.setText(message + ((" Folder: " + directory) if directory else ""))
        self.stem_candidates.clear()
        self.separation_files.clear()
        self.separation_directory = None
        if not directory:
            return
        folder = Path(directory).expanduser()
        if folder.is_symlink() or not folder.is_dir():
            self.status.setText('Separated audio folder is missing or not safe to inspect.')
            return
        self.separation_directory = folder.resolve()
        for candidate in candidates:
            try:
                path = valid_wav(candidate, 'separated track')
                if self.separation_directory not in path.parents:
                    continue
                self.separation_files.add(path)
                item = QListWidgetItem(path.name)
                item.setData(Qt.UserRole, str(path))
                self.stem_candidates.addItem(item)
            except (OSError, MixError):
                continue
        if not self.separation_files:
            self.status.setText('No valid WAV stems were found. Inspect the private separator job log.')

    def selected_stem(self):
        item = self.stem_candidates.currentItem()
        if item is None:
            self.status.setText('Select a separated WAV track to review first.')
            return None
        try:
            path = valid_wav(item.data(Qt.UserRole), 'separated track')
            if path not in self.separation_files or self.separation_directory not in path.parents:
                raise MixError('Selected file is not one of this job\'s WAV stems.')
            return path
        except (OSError, MixError) as error:
            self.status.setText(str(error))
            return None

    def listen_stem(self):
        path = self.selected_stem()
        if path and not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
            self.status.setText('No audio player opened. Audition the stem with your installed DAW.')

    def assign_vocal_stem(self):
        path = self.selected_stem()
        if path is None:
            return
        if self.mix_backing.text().strip() == str(path):
            self.status.setText('This is already assigned as backing. Select a different vocal WAV.')
            return
        self.rvc_vocal.setText(str(path))
        self.mix_vocal.clear()
        self.status.setText('Singing vocal selected for RVC. Review it before converting; this is not a trained model.')

    def assign_instrumental_stem(self):
        path = self.selected_stem()
        if path is None:
            return
        if self.rvc_vocal.text().strip() == str(path):
            self.status.setText('This is already assigned as vocal. Select a different backing WAV.')
            return
        self.mix_backing.setText(str(path))
        self.status.setText('Instrumental backing selected. Your original audio stays unchanged.')

    def open_separated_folder(self):
        if self.separation_directory and self.separation_directory.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.separation_directory)))

    def separation_finished(self):
        worker, self.separation_worker = self.separation_worker, None
        self.separate_button.setEnabled(True)
        if worker is not None:
            worker.deleteLater()

    def start_mix(self):
        if self.mix_worker is not None:
            return
        try:
            backing = str(valid_wav(self.mix_backing.text().strip(), "instrumental backing"))
            vocal = str(valid_wav(self.mix_vocal.text().strip(), "converted singing vocal"))
            if backing == vocal:
                raise MixError("Choose different backing and converted-vocal WAV files.")
        except (OSError, MixError) as error:
            self.status.setText(str(error))
            return
        self.mix_worker = VoiceMixWorker(backing, vocal,
                                         self.mix_voice_gain.value(), self.mix_back_gain.value())
        self.mix_worker.result.connect(self.mix_done)
        self.mix_worker.finished.connect(self.mix_finished)
        self.mix_button.setEnabled(False)
        self.status.setText("Combining backing and converted voice into a new WAV…")
        self.mix_worker.start()

    def mix_done(self, output, message):
        self.status.setText(message + ((" " + output) if output else ""))

    def mix_finished(self):
        worker, self.mix_worker = self.mix_worker, None
        self.mix_button.setEnabled(True)
        self.finish_song_button.setEnabled(True)
        if worker is not None:
            worker.deleteLater()

    def check_training_engine(self):
        if self.engine_worker is not None:
            return
        if not self.training_script.is_file() or self.training_script.is_symlink():
            self.engine_status.setText('The Spider Studio voice-engine helper has not been installed.')
            return
        self.engine_check_button.setEnabled(False)
        self.engine_status.setText('Checking CPU, disk, local RVC installation and audio tools…')
        self.engine_worker = EngineCheckWorker(self.training_script)
        self.engine_worker.result.connect(self.engine_status.setText)
        self.engine_worker.finished.connect(self.engine_check_finished)
        self.engine_worker.start()

    def engine_check_finished(self):
        worker, self.engine_worker = self.engine_worker, None
        self.engine_check_button.setEnabled(True)
        if worker is not None:
            worker.deleteLater()

    def launch_trainer(self):
        if self.trainer is not None:
            return
        if not self.training_script.is_file() or self.training_script.is_symlink():
            self.engine_status.setText('Training launcher is missing from Studio installation.')
            return
        answer = QMessageBox.question(self, 'Start private My Voice trainer',
            'Start the local-only RVC training interface? This can use significant CPU/GPU/RAM. '
            'It will not automatically record you, begin model training or download voice data. '
            'Only train with your own or authorized vocal recordings.',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        runner = QProcess(self)
        runner.setProcessChannelMode(QProcess.MergedChannels)
        runner.setProgram('bash')
        runner.setArguments([str(self.training_script), '--launch-local'])
        runner.setWorkingDirectory(str(self.training_script.parent))
        runner.readyReadStandardOutput.connect(self.trainer_output)
        runner.errorOccurred.connect(self.trainer_error)
        runner.finished.connect(self.trainer_finished)
        self.trainer = runner
        self.training_launch_button.setEnabled(False)
        self.training_stop_button.setEnabled(True)
        self.engine_status.setText('Starting private local RVC trainer. The engine may require dependencies or model weights.')
        runner.start()

    def trainer_output(self):
        if self.trainer:
            raw = bytes(self.trainer.readAllStandardOutput()).decode('utf-8', errors='replace').strip()
            if raw:
                self.engine_status.setText(raw[-1400:])

    def trainer_error(self, _error):
        if self.trainer is not None:
            self.engine_status.setText('Could not launch the local trainer. Check the RVC setup and Python environment.')

    def trainer_finished(self, _exit_code, _exit_status):
        runner, self.trainer = self.trainer, None
        self.training_stop_button.setEnabled(False)
        self.training_launch_button.setEnabled(True)
        if runner is not None:
            runner.deleteLater()

    def stop_trainer(self):
        if self.trainer and self.trainer.state() != QProcess.NotRunning:
            self.engine_status.setText('Stopping the local training interface…')
            self.trainer.terminate()
            QTimer.singleShot(3000, self.force_stop_trainer)

    def force_stop_trainer(self):
        if self.trainer and self.trainer.state() != QProcess.NotRunning:
            self.trainer.kill()

    def check_voice_readiness(self):
        if self.readiness_worker is not None:
            return
        self.readiness_button.setEnabled(False)
        self.readiness_details.setText('Checking local recording durations…')
        self.readiness_worker = TrainingReadinessWorker()
        self.readiness_worker.result.connect(self.voice_readiness_done)
        self.readiness_worker.finished.connect(self.voice_readiness_finished)
        self.readiness_worker.start()

    def voice_readiness_done(self, report):
        if 'error' in report:
            self.readiness_details.setText('Cannot measure My Voice recordings: ' + report['error'])
            return
        seconds = float(report['total_seconds'])
        usable = int(report['usable_clips'])
        rejected = int(report['rejected_clips'])
        remaining = max(0.0, MIN_TRAIN_SECONDS - seconds)
        message = f'Usable: {seconds / 60:.1f} of {MIN_TRAIN_SECONDS / 60:.0f} minutes ({usable} clips).'
        if rejected:
            message += f' {rejected} recording(s) rejected: review or re-record.'
        if report['ready_to_prepare']:
            message += ' Ready to prepare a PRIVATE training set. No model has been trained.'
        else:
            message += f' Need {remaining / 60:.1f} more usable minutes before dataset preparation.'
        self.readiness_details.setText(message)

    def voice_readiness_finished(self):
        worker, self.readiness_worker = self.readiness_worker, None
        self.readiness_button.setEnabled(True)
        if worker is not None:
            worker.deleteLater()

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

    def prepare_dataset(self):
        if self.dataset_worker is not None:
            return
        answer = QMessageBox.question(
            self, 'My Voice recording consent',
            'I confirm these recordings are my own voice or recordings I have permission to use for model training. '
            'Prepare private local copies for RVC? This does not train a model or upload audio.',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        self.dataset_button.setEnabled(False)
        self.dataset_worker = DatasetWorker()
        self.dataset_worker.result.connect(self.dataset_result)
        self.dataset_worker.finished.connect(self.dataset_finished)
        self.dataset_worker.start()
        self.voice_status.setText('Checking recording lengths and preparing private training data…')

    def dataset_result(self, success, message):
        prepared = Path(message) if success else None
        valid = bool(prepared and not prepared.is_symlink()
                     and prepared.is_dir()
                     and (prepared / 'manifest.json').is_file()
                     and (prepared / 'audio').is_dir())
        if valid:
            self.last_training_set = prepared.resolve()
            self.voice_status.setText('Private RVC training set: ' + str(prepared)
                                      + '. No voice model has been trained yet.')
        else:
            self.voice_status.setText('Training set not available: ' + str(message))
        self.open_dataset_button.setEnabled(valid)
        self.copy_dataset_button.setEnabled(valid)

    def open_dataset(self):
        if self.last_training_set and self.last_training_set.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.last_training_set)))

    def copy_dataset_path(self):
        audio = self.last_training_set / 'audio' if self.last_training_set else None
        if audio and audio.is_dir() and not audio.is_symlink():
            QApplication.clipboard().setText(str(audio))
            self.voice_status.setText('RVC training audio folder copied. Paste it into the local training interface. '
                                      'No model training has started.')

    def dataset_finished(self):
        worker, self.dataset_worker = self.dataset_worker, None
        self.dataset_button.setEnabled(True)
        if worker is not None:
            worker.deleteLater()

    def cancel_capture(self):
        if self.capture_proc is not None:
            self.finish_voice(stop=True)

    def closeEvent(self, event):
        self.stop_trainer()
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
