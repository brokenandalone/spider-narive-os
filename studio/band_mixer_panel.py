"""Independent stem mixing workspace for Spider Studio.

Does not run an AI model or alter original tracks. Requires real WAV stems.
"""
from pathlib import Path
import threading

from PyQt5.QtCore import QThread, QUrl, Qt, pyqtSignal
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QDoubleSpinBox, QFileDialog, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget,
)

if __package__:
    from .band_mix import ROLES, DEFAULT_OUTPUT, mix_band_tracks, validate_tracks, validate_mix_options
    from .song_mix import MixError, valid_wav
else:
    from band_mix import ROLES, DEFAULT_OUTPUT, mix_band_tracks, validate_tracks, validate_mix_options
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


class BandMixerWorker(QThread):
    result = pyqtSignal(str, str)

    def __init__(self, tracks, gains, pans, mutes):
        super().__init__(QApplication.instance())
        self.tracks = dict(tracks)
        self.gains = dict(gains)
        self.pans = dict(pans)
        self.mutes = dict(mutes)
        self.stop = threading.Event()
        QApplication.instance().aboutToQuit.connect(self.shutdown)

    def shutdown(self):
        self.stop.set()
        self.wait()

    def run(self):
        try:
            output = mix_band_tracks(
                self.tracks, gains=self.gains, pans=self.pans, mutes=self.mutes,
                stop=self.stop,
            )
            self.result.emit(str(output), 'Band mix exported. Originals have not been changed.')
        except (MixError, OSError, ValueError) as exc:
            self.result.emit('', str(exc))
        except Exception:
            self.result.emit('', 'Band mixing failed. Check the private render log.')


class BandMixerPanel(QWidget):
    """Eight separate WAV inputs with gain, stereo pan, and mute per part."""

    def __init__(self, ai_panel=None, parent=None):
        super().__init__(parent)
        self.ai_panel = ai_panel
        self.worker = None
        self.last_mix = None
        self.track_fields = {}
        self.gains = {}
        self.pans = {}
        self.mutes = {}

        layout = QVBoxLayout(self)
        title = QLabel('BAND MIXER')
        title.setStyleSheet('font-size:22px; color:#c4b5fd; font-weight:bold;')
        layout.addWidget(title)
        notice = QLabel(
            'Mix actual independent WAV stems. Use the existing Studio AI tab to '
            'generate a song or prepare and separate vocals. Prompted guitar parts '
            'inside one AI song are not independent recordings. For full DAW editing '
            'use the existing multitrack session exporter. Neither models nor '
            'other software are installed automatically.'
        )
        notice.setWordWrap(True)
        layout.addWidget(notice)

        tracks_form = QFormLayout()
        tracks_form.setSpacing(10)
        for role in ROLES:
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)
            path = QLineEdit()
            path.setPlaceholderText('Choose an independent WAV for ' + ROLE_LABELS[role])
            path.setObjectName('band_audio_' + role)
            browse = QPushButton('Choose WAV')
            browse.clicked.connect(lambda checked=False, key=role: self.choose_wav(key))
            gain = QDoubleSpinBox()
            gain.setRange(0, 2)
            gain.setSingleStep(.05)
            gain.setDecimals(2)
            gain.setValue(1)
            gain.setPrefix('Level ')
            gain.setObjectName('band_gain_' + role)
            pan = QDoubleSpinBox()
            pan.setRange(-1, 1)
            pan.setSingleStep(.1)
            pan.setDecimals(2)
            pan.setPrefix('Pan ')
            pan.setObjectName('band_pan_' + role)
            if role == 'rhythm_guitar':
                pan.setValue(-.35)
            elif role == 'lead_guitar':
                pan.setValue(.35)
            mute = QCheckBox('Mute')
            mute.setObjectName('band_mute_' + role)
            for field in (path, browse, gain, pan, mute):
                h.addWidget(field)
            h.setStretchFactor(path, 1)
            tracks_form.addRow(ROLE_LABELS[role], row)
            self.track_fields[role] = path
            self.gains[role] = gain
            self.pans[role] = pan
            self.mutes[role] = mute
        layout.addLayout(tracks_form)

        self.status = QLabel('Choose two to eight distinct WAV files. Pan -1 is left; +1 is right.')
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.PlainText)
        layout.addWidget(self.status)

        actions = QHBoxLayout()
        self.import_button = QPushButton('Import Studio AI selections')
        self.import_button.clicked.connect(self.import_ai_selections)
        self.import_button.setEnabled(ai_panel is not None)
        self.mix_button = QPushButton('Render band mix')
        self.mix_button.clicked.connect(self.start_mix)
        self.cancel_button = QPushButton('Stop rendering')
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_mix)
        for btn in (self.import_button, self.mix_button, self.cancel_button):
            actions.addWidget(btn)
        layout.addLayout(actions)

        output_actions = QHBoxLayout()
        self.play_button = QPushButton('Listen to last mix')
        self.play_button.setEnabled(False)
        self.play_button.clicked.connect(self.play_mix)
        self.folder_button = QPushButton('Open exported mix folder')
        self.folder_button.setEnabled(False)
        self.folder_button.clicked.connect(self.open_exported_folder)
        output_actions.addWidget(self.play_button)
        output_actions.addWidget(self.folder_button)
        layout.addLayout(output_actions)
        note = QLabel('Exports are 48 kHz stereo WAV, with a private track-settings receipt, under ' + str(DEFAULT_OUTPUT))
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch()

    def choose_wav(self, role):
        selected, _ = QFileDialog.getOpenFileName(
            self, 'Choose ' + ROLE_LABELS[role] + ' WAV', str(Path.home()),
            'WAV audio (*.wav)',
        )
        if selected:
            self.track_fields[role].setText(selected)

    def import_ai_selections(self):
        ai = self.ai_panel
        if ai is None:
            self.status.setText('Open Studio AI to assign real WAV stems first.')
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
            str(count) + ' source selections imported. Check them before rendering.'
            if count else 'There are no selected WAV stems in Studio AI yet.'
        )

    def start_mix(self):
        if self.worker is not None:
            return
        tracks = {role: field.text().strip()
                  for role, field in self.track_fields.items() if field.text().strip()}
        gains = {role: self.gains[role].value() for role in tracks}
        pans = {role: self.pans[role].value() for role in tracks}
        mutes = {role: self.mutes[role].isChecked() for role in tracks}
        try:
            validate_tracks(tracks, gains)
            validate_mix_options(tracks, pans, mutes)
        except (MixError, OSError, ValueError) as exc:
            self.status.setText(str(exc))
            return
        self.worker = BandMixerWorker(tracks, gains, pans, mutes)
        self.worker.result.connect(self.mix_done)
        self.worker.finished.connect(self.mix_finished)
        self.mix_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.status.setText('Rendering local WAV stems with FFmpeg. Your input files are preserved.')
        self.worker.start()

    def cancel_mix(self):
        if self.worker is not None:
            self.worker.stop.set()
            self.cancel_button.setEnabled(False)
            self.status.setText('Stopping the render. Original recordings are safe.')

    def mix_done(self, output, message):
        self.last_mix = Path(output) if output else None
        self.play_button.setEnabled(bool(output))
        self.folder_button.setEnabled(bool(output))
        self.status.setText(message + (' ' + output if output else ''))

    def mix_finished(self):
        worker, self.worker = self.worker, None
        self.mix_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        if worker is not None:
            worker.deleteLater()

    def play_mix(self):
        if self.last_mix is None:
            return
        try:
            path = valid_wav(self.last_mix, 'last band mix')
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
                self.status.setText('No audio player opened. Use your installed DAW.')
        except (OSError, MixError):
            self.status.setText('The exported WAV was moved or is no longer valid.')

    def open_exported_folder(self):
        if self.last_mix and self.last_mix.parent.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.last_mix.parent)))

    def closeEvent(self, event):
        if self.worker is not None:
            self.worker.shutdown()
        super().closeEvent(event)
