"""Independent, non-destructive Spider Studio eight-track band mixer.

Source WAV files are never overwritten. Every Studio project revision is private.
"""
from pathlib import Path
import threading
import time

from PyQt5.QtCore import QThread, QUrl, Qt, pyqtSignal
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog,
    QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QSpinBox, QVBoxLayout, QWidget,
)

if __package__:
    from .band_mix import (
        ROLES, DEFAULT_OUTPUT, inspect_tracks, mix_band_tracks,
        validate_tracks, validate_mix_options, validate_offsets,
    )
    from .band_projects import (
        PROJECTS_ROOT, save_project, load_project, list_projects, recent_mixes,
    )
    from .multitrack_dialog import MultitrackDialog
    from .mix_presets import PRESETS, PRESET_IDS, preset_mix_values
    from .song_mix import MixError, valid_wav
else:
    from band_mix import (
        ROLES, DEFAULT_OUTPUT, inspect_tracks, mix_band_tracks,
        validate_tracks, validate_mix_options, validate_offsets,
    )
    from band_projects import (
        PROJECTS_ROOT, save_project, load_project, list_projects, recent_mixes,
    )
    from multitrack_dialog import MultitrackDialog
    from mix_presets import PRESETS, PRESET_IDS, preset_mix_values
    from song_mix import MixError, valid_wav

ROLE_LABELS = {
    'backing': 'Instrumental bed',
    'lead_vocal': 'Lead vocal / My Voice',
    'guest_vocal': 'Guest / female vocalist',
    'rhythm_guitar': 'Rhythm guitar',
    'lead_guitar': 'Lead guitar',
    'bass': 'Bass',
    'drums': 'Drums',
    'keys': 'Piano / keys',
}
DAW_ROLES = {
    'backing': 'instrumental_bed', 'lead_vocal': 'lead_vocal',
    'guest_vocal': 'backing_vocal', 'rhythm_guitar': 'rhythm_guitar',
    'lead_guitar': 'lead_guitar', 'bass': 'bass', 'drums': 'drums',
    'keys': 'piano_keys',
}


class BandMixerWorker(QThread):
    result = pyqtSignal(str, str)

    def __init__(self, tracks, gains, pans, mutes, offsets_ms=None):
        super().__init__(QApplication.instance())
        self.tracks = dict(tracks)
        self.gains = dict(gains)
        self.pans = dict(pans)
        self.mutes = dict(mutes)
        self.offsets_ms = dict(offsets_ms or {})
        self.stop = threading.Event()
        QApplication.instance().aboutToQuit.connect(self.shutdown)

    def shutdown(self):
        self.stop.set()
        self.wait()

    def run(self):
        try:
            output = mix_band_tracks(
                self.tracks, gains=self.gains, pans=self.pans,
                mutes=self.mutes, offsets_ms=self.offsets_ms, stop=self.stop,
            )
            self.result.emit(str(output), 'New 48 kHz stereo WAV exported. Originals preserved.')
        except (MixError, OSError, ValueError) as exc:
            self.result.emit('', str(exc))
        except Exception:
            self.result.emit('', 'Band mix failed. Inspect the private FFmpeg job log.')


class BandMixerPanel(QWidget):
    """Separate WAV paths, mix levels, panning, mute, solo and timing offset."""

    def __init__(self, ai_panel=None, parent=None):
        super().__init__(parent)
        self.ai_panel = ai_panel
        self.worker = None
        self.last_mix = None
        self.track_fields, self.gains, self.pans = {}, {}, {}
        self.mutes, self.solos, self.offsets = {}, {}, {}
        layout = QVBoxLayout(self)
        heading = QLabel('BAND MIXER  |  STUDIO PROJECTS')
        heading.setStyleSheet('font-size:22px; color:#c4b5fd; font-weight:bold;')
        layout.addWidget(heading)
        description = QLabel(
            'Use separate recorded or verified isolated WAV files. Adjust two real '
            'guitar tracks, guest and My Voice, bass, drums, piano and backing. '
            'No AI model, download or service starts from this mixer. '
            'Solo and muted tracks affect a render, not your original recordings.'
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        project = QHBoxLayout()
        self.project_title = QLineEdit('New Spider Studio Project')
        self.project_title.setPlaceholderText('Project title')
        self.project_title.setObjectName('band_project_title')
        project.addWidget(QLabel('Project'))
        project.addWidget(self.project_title, 1)
        self.save_project_button = QPushButton('Save new revision')
        self.save_project_button.clicked.connect(self.save_current_project)
        project.addWidget(self.save_project_button)
        layout.addLayout(project)

        recall = QHBoxLayout()
        self.project_library = QComboBox()
        self.project_library.setMinimumWidth(240)
        self.project_library.setObjectName('band_project_library')
        self.project_refresh = QPushButton('Refresh projects')
        self.project_refresh.clicked.connect(self.refresh_projects)
        self.project_load = QPushButton('Load selected project')
        self.project_load.clicked.connect(self.load_selected_project)
        recall.addWidget(self.project_library, 1)
        recall.addWidget(self.project_refresh)
        recall.addWidget(self.project_load)
        layout.addLayout(recall)

        preset_row = QHBoxLayout()
        self.mix_preset = QComboBox()
        for key in PRESET_IDS:
            self.mix_preset.addItem(PRESETS[key]['name'], key)
        self.mix_preset.setCurrentIndex(self.mix_preset.findData('broken_sorrow'))
        self.apply_preset_button = QPushButton('Apply starting mix preset')
        self.apply_preset_button.clicked.connect(self.apply_mix_preset)
        preset_row.addWidget(QLabel('Quick mix'))
        preset_row.addWidget(self.mix_preset, 1)
        preset_row.addWidget(self.apply_preset_button)
        layout.addLayout(preset_row)

        self.track_heading = QLabel('INDEPENDENT WAV TRACKS')
        self.track_heading.setStyleSheet('font-size:17px; color:#c4b5fd; font-weight:bold;')
        layout.addWidget(self.track_heading)
        for role in ROLES:
            label = QLabel(ROLE_LABELS[role])
            label.setStyleSheet('font-size:15px; font-weight:bold; color:#f3e8ff;')
            layout.addWidget(label)
            path_row = QHBoxLayout()
            audio = QLineEdit()
            audio.setObjectName('band_audio_' + role)
            audio.setPlaceholderText('Select an independent WAV for ' + ROLE_LABELS[role])
            browse = QPushButton('Choose WAV')
            browse.clicked.connect(lambda checked=False, key=role: self.choose_wav(key))
            path_row.addWidget(audio, 1)
            path_row.addWidget(browse)
            layout.addLayout(path_row)
            controls = QHBoxLayout()
            gain = QDoubleSpinBox()
            gain.setRange(0, 2)
            gain.setSingleStep(.05)
            gain.setValue(1)
            gain.setPrefix('Level ')
            gain.setObjectName('band_gain_' + role)
            pan = QDoubleSpinBox()
            pan.setRange(-1, 1)
            pan.setSingleStep(.1)
            pan.setPrefix('Pan ')
            pan.setObjectName('band_pan_' + role)
            if role == 'rhythm_guitar':
                pan.setValue(-.35)
            elif role == 'lead_guitar':
                pan.setValue(.35)
            mute = QCheckBox('Mute')
            mute.setObjectName('band_mute_' + role)
            solo = QCheckBox('Solo')
            solo.setObjectName('band_solo_' + role)
            delay = QSpinBox()
            delay.setRange(0, 60000)
            delay.setSingleStep(10)
            delay.setSuffix(' ms')
            delay.setPrefix('Start +')
            delay.setObjectName('band_delay_' + role)
            for field in (gain, pan, mute, solo, delay):
                controls.addWidget(field)
            controls.addStretch()
            layout.addLayout(controls)
            self.track_fields[role] = audio
            self.gains[role] = gain
            self.pans[role] = pan
            self.mutes[role] = mute
            self.solos[role] = solo
            self.offsets[role] = delay

        self.status = QLabel(
            'Choose 2 to 8 real WAV stems. Pan -1 = left, +1 = right. '
            'Start offset is positive delay, not automatic beat alignment.'
        )
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.PlainText)
        layout.addWidget(self.status)

        tools = QHBoxLayout()
        self.import_button = QPushButton('Import Studio AI selections')
        self.import_button.clicked.connect(self.import_ai_selections)
        self.import_button.setEnabled(ai_panel is not None)
        self.inspect_button = QPushButton('Audit track timing / rates')
        self.inspect_button.clicked.connect(self.audit_tracks)
        self.daw_button = QPushButton('Prepare DAW multitrack session')
        self.daw_button.clicked.connect(self.open_daw_session)
        for action in (self.import_button, self.inspect_button, self.daw_button):
            tools.addWidget(action)
        layout.addLayout(tools)

        actions = QHBoxLayout()
        self.mix_button = QPushButton('Render new band mix')
        self.mix_button.clicked.connect(self.start_mix)
        self.cancel_button = QPushButton('Stop rendering')
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_mix)
        self.play_button = QPushButton('Listen to last mix')
        self.play_button.setEnabled(False)
        self.play_button.clicked.connect(self.play_mix)
        for button in (self.mix_button, self.cancel_button, self.play_button):
            actions.addWidget(button)
        layout.addLayout(actions)

        history = QHBoxLayout()
        self.mix_history = QComboBox()
        self.mix_history.setMinimumWidth(230)
        self.mix_history.setObjectName('band_mix_history')
        self.history_refresh = QPushButton('Refresh past mixes')
        self.history_refresh.clicked.connect(self.refresh_history)
        self.history_listen = QPushButton('Listen to selected previous mix')
        self.history_listen.clicked.connect(self.play_previous)
        self.folder_button = QPushButton('Open last mix folder')
        self.folder_button.setEnabled(False)
        self.folder_button.clicked.connect(self.open_exported_folder)
        for element in (self.mix_history, self.history_refresh,
                        self.history_listen, self.folder_button):
            history.addWidget(element)
        layout.addLayout(history)

        footer = QLabel(
            'New revisions: ' + str(PROJECTS_ROOT) +
            '\nRendered stereo WAVs and per-track mix receipts: ' + str(DEFAULT_OUTPUT) +
            '\nProjects contain paths/settings, not copies of your audio.'
        )
        footer.setWordWrap(True)
        layout.addWidget(footer)
        layout.addStretch()
        self.refresh_projects()
        self.refresh_history()

    def apply_mix_preset(self):
        if self.worker is not None:
            self.status.setText('Finish the current render before changing mix levels.')
            return
        try:
            gains, pans = preset_mix_values(self.mix_preset.currentData())
        except ValueError as exc:
            self.status.setText(str(exc))
            return
        for role in ROLES:
            self.gains[role].setValue(gains[role])
            self.pans[role].setValue(pans[role])
        self.status.setText(
            'Mix starting preset applied to levels and pan only. '
            'Existing WAV paths, mute, solo and timing offsets are unchanged. '
            'Save a new project revision to keep these settings.'
        )

    def choose_wav(self, role):
        selected, _ = QFileDialog.getOpenFileName(
            self, 'Choose ' + ROLE_LABELS[role] + ' WAV',
            str(Path.home()), 'WAV audio (*.wav)',
        )
        if selected:
            self.track_fields[role].setText(selected)

    def import_ai_selections(self):
        ai = self.ai_panel
        if ai is None:
            self.status.setText('Open Studio AI and select real stems first.')
            return
        count = 0
        for role in ROLES:
            if role not in ai.band_track_fields:
                continue
            source = ai.band_track_fields[role].text().strip()
            if source:
                self.track_fields[role].setText(source)
                if role in ai.band_track_gains:
                    self.gains[role].setValue(ai.band_track_gains[role].value())
                count += 1
        self.status.setText(
            str(count) + ' track paths imported; audit stems before rendering.'
            if count else 'No WAV stem selections are currently set in Studio AI.'
        )

    def current_tracks(self):
        return {role: field.text().strip()
                for role, field in self.track_fields.items() if field.text().strip()}

    def render_options(self, tracks):
        gains = {role: self.gains[role].value() for role in tracks}
        pans = {role: self.pans[role].value() for role in tracks}
        offsets = {role: self.offsets[role].value() for role in tracks}
        solo_roles = {role for role in tracks if self.solos[role].isChecked()}
        # When Solo is active, mute every track not soloed, overriding normal mute.
        mutes = {role: (role not in solo_roles if solo_roles else self.mutes[role].isChecked())
                 for role in tracks}
        return gains, pans, mutes, offsets

    def start_mix(self):
        if self.worker is not None:
            return
        tracks = self.current_tracks()
        gains, pans, mutes, offsets = self.render_options(tracks)
        try:
            validate_tracks(tracks, gains)
            validate_mix_options(tracks, pans, mutes)
            validate_offsets(tracks, offsets)
        except (MixError, OSError, ValueError) as exc:
            self.status.setText(str(exc))
            return
        self.worker = BandMixerWorker(tracks, gains, pans, mutes, offsets)
        self.worker.result.connect(self.mix_done)
        self.worker.finished.connect(self.mix_finished)
        self.mix_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.status.setText('Rendering with FFmpeg. Source recordings will not change.')
        self.worker.start()

    def cancel_mix(self):
        if self.worker is not None:
            self.worker.stop.set()
            self.cancel_button.setEnabled(False)
            self.status.setText('Stopping render. Input recordings remain unchanged.')

    def mix_done(self, output, message):
        self.last_mix = Path(output) if output else None
        self.play_button.setEnabled(bool(output))
        self.folder_button.setEnabled(bool(output))
        self.status.setText(message + (' ' + output if output else ''))
        if output:
            self.refresh_history()

    def mix_finished(self):
        worker, self.worker = self.worker, None
        self.mix_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        if worker is not None:
            worker.deleteLater()

    def play_mix(self):
        self._listen(self.last_mix)

    def _listen(self, path):
        if not path:
            self.status.setText('Select an existing local mix first.')
            return
        try:
            audio = valid_wav(path, 'band mix')
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(audio))):
                self.status.setText('Audio player did not open; try your DAW.')
        except (OSError, MixError):
            self.status.setText('Mix was moved or cannot be played.')

    def refresh_history(self):
        self.mix_history.clear()
        try:
            for data in recent_mixes():
                stamp = time.strftime('%Y-%m-%d %H:%M', time.localtime(data['created_at_unix']))
                label = stamp + ' | ' + str(data['track_count']) + ' tracks'
                self.mix_history.addItem(label, data['file'])
        except (MixError, OSError) as exc:
            self.status.setText('Could not inspect mix history: ' + str(exc))

    def play_previous(self):
        self._listen(self.mix_history.currentData())

    def open_exported_folder(self):
        if self.last_mix and self.last_mix.parent.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.last_mix.parent)))

    def audit_tracks(self):
        try:
            report = inspect_tracks(self.current_tracks())
            summaries = [
                f"{ROLE_LABELS[role]}: {data['duration_seconds']:.2f}s, "
                f"{data['sample_rate']} Hz, {data['channels']} channel(s)"
                for role, data in report['tracks'].items()
            ]
            summaries += report['warnings'] or ['Track headers look consistent; verify musical alignment by ear.']
            self.status.setText('\n'.join(summaries))
        except (MixError, OSError, ValueError) as exc:
            self.status.setText(str(exc))

    def project_state(self):
        tracks = {}
        for role, path in self.current_tracks().items():
            tracks[role] = {
                'path': path, 'gain': self.gains[role].value(),
                'pan': self.pans[role].value(), 'muted': self.mutes[role].isChecked(),
                'solo': self.solos[role].isChecked(), 'offset_ms': self.offsets[role].value(),
            }
        return tracks

    def save_current_project(self):
        if self.worker is not None:
            self.status.setText('Finish or stop this render before saving new settings.')
            return
        try:
            filename = save_project(self.project_title.text(), self.project_state())
            self.refresh_projects()
            index = self.project_library.findData(str(filename))
            if index >= 0:
                self.project_library.setCurrentIndex(index)
            self.status.setText('New private project revision saved: ' + str(filename))
        except (MixError, OSError, ValueError) as exc:
            self.status.setText(str(exc))

    def refresh_projects(self):
        self.project_library.clear()
        try:
            for data in list_projects():
                self.project_library.addItem(
                    data['title'] + ' | ' + data['path'].split('/')[-2],
                    data['path'],
                )
        except (MixError, OSError) as exc:
            self.status.setText('Project library unavailable: ' + str(exc))

    def load_selected_project(self):
        if self.worker is not None:
            self.status.setText('Do not replace settings while a render is running.')
            return
        selected = self.project_library.currentData()
        if not selected:
            self.status.setText('Save a project revision before loading it.')
            return
        try:
            data = load_project(selected)
        except (MixError, OSError, ValueError) as exc:
            self.status.setText(str(exc))
            return
        for role in ROLES:
            details = data['tracks'].get(role, {})
            self.track_fields[role].setText(details.get('path', ''))
            self.gains[role].setValue(details.get('gain', 1))
            self.pans[role].setValue(details.get('pan', 0))
            self.mutes[role].setChecked(details.get('muted', False))
            self.solos[role].setChecked(details.get('solo', False))
            self.offsets[role].setValue(details.get('offset_ms', 0))
        self.project_title.setText(data['title'])
        warning = ', '.join(data['missing_sources'])
        self.status.setText(
            'Project settings restored. Missing WAV stems: ' + warning
            if warning else 'Project settings restored. Audit and listen before rendering.'
        )

    def open_daw_session(self):
        if self.worker is not None:
            self.status.setText('Finish the current render before creating a DAW session.')
            return
        entries = [
            {'path': path, 'role': DAW_ROLES[role], 'label': ROLE_LABELS[role]}
            for role, path in self.current_tracks().items()
        ]
        if not entries:
            self.status.setText('Choose at least one WAV to prepare a multitrack session.')
            return
        try:
            dialog = MultitrackDialog(entries, title=self.project_title.text(), parent=self)
            self.status.setText(
                'DAW sessions copy real WAVs at time zero. '
                'Reapply pan, gain and offset in the DAW if needed.'
            )
            dialog.exec_()
        except (OSError, ValueError) as exc:
            self.status.setText('Unable to prepare DAW handoff: ' + str(exc))

    def closeEvent(self, event):
        if self.worker is not None:
            self.worker.shutdown()
        super().closeEvent(event)
