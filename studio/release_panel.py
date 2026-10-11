"""Native Studio Release Desk: controlled release formats and mix audition."""
from pathlib import Path
import threading
import time

from PyQt5.QtCore import QThread, QUrl, Qt, pyqtSignal
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QVBoxLayout, QWidget,
)

if __package__:
    from .release_export import (
        PROFILES, ALL_PROFILES, export_release, list_releases, validate_source,
    )
    from .band_projects import recent_mixes
    from .song_mix import MixError, valid_wav
else:
    from release_export import PROFILES, ALL_PROFILES, export_release, list_releases, validate_source
    from band_projects import recent_mixes
    from song_mix import MixError, valid_wav


class ReleaseWorker(QThread):
    result = pyqtSignal(str, str)

    def __init__(self, source, profiles):
        super().__init__(QApplication.instance())
        self.source = str(source)
        self.profiles = tuple(profiles)
        self.stop = threading.Event()
        QApplication.instance().aboutToQuit.connect(self.shutdown)

    def shutdown(self):
        self.stop.set()
        self.wait()

    def run(self):
        try:
            folder = export_release(self.source, self.profiles, stop=self.stop)
            self.result.emit(str(folder), 'Release formats exported into a new private folder.')
        except (MixError, OSError, ValueError) as error:
            self.result.emit('', str(error))
        except Exception:
            self.result.emit('', 'Release export failed. Check the local FFmpeg logs.')


class ReleasePanel(QWidget):
    """A deliberate export workflow; never generates, uploads or publishes songs."""

    def __init__(self, band_mixer=None, parent=None):
        super().__init__(parent)
        self.band_mixer = band_mixer
        self.worker = None
        self.last_folder = None
        layout = QVBoxLayout(self)
        title = QLabel('STUDIO RELEASE DESK')
        title.setStyleSheet('font-size:22px; color:#c4b5fd; font-weight:bold;')
        layout.addWidget(title)
        notice = QLabel(
            'Turn a finished WAV into music delivery formats. This is conversion, '
            'not automatic mastering or loudness certification. Choose a source '
            'you have listened to and retain the original. Nothing uploads to '
            'streaming services, modifies Spider Media Center or starts an AI engine.'
        )
        notice.setWordWrap(True)
        layout.addWidget(notice)

        source_row = QHBoxLayout()
        self.source = QLineEdit()
        self.source.setObjectName('release_source')
        self.source.setPlaceholderText('Choose an existing finished WAV mix')
        browse = QPushButton('Choose finished WAV')
        browse.clicked.connect(self.browse_source)
        self.use_last_mix = QPushButton('Use last Band Mixer mix')
        self.use_last_mix.clicked.connect(self.import_last_mix)
        self.use_last_mix.setEnabled(band_mixer is not None)
        source_row.addWidget(self.source, 1)
        source_row.addWidget(browse)
        source_row.addWidget(self.use_last_mix)
        layout.addLayout(source_row)

        layout.addWidget(QLabel('Export formats'))
        self.profile_boxes = {}
        for key in ALL_PROFILES:
            box = QCheckBox(PROFILES[key]['label'])
            box.setObjectName('release_profile_' + key)
            box.setChecked(key == 'studio_wav')
            self.profile_boxes[key] = box
            layout.addWidget(box)
        self.status = QLabel(
            'The 24-bit WAV is selected by default. MP3 encoding requires libmp3lame.'
        )
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.PlainText)
        layout.addWidget(self.status)

        controls = QHBoxLayout()
        self.start_button = QPushButton('Export selected release formats')
        self.start_button.clicked.connect(self.start_export)
        self.stop_button = QPushButton('Stop export')
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_export)
        self.folder_button = QPushButton('Open last release folder')
        self.folder_button.setEnabled(False)
        self.folder_button.clicked.connect(self.open_last_folder)
        for btn in (self.start_button, self.stop_button, self.folder_button):
            controls.addWidget(btn)
        layout.addLayout(controls)

        layout.addWidget(QLabel('Completed release bundles'))
        history = QHBoxLayout()
        self.release_history = QComboBox()
        self.release_history.setObjectName('release_history')
        self.refresh_button = QPushButton('Refresh releases')
        self.refresh_button.clicked.connect(self.refresh_releases)
        self.open_release_button = QPushButton('Open selected release folder')
        self.open_release_button.clicked.connect(self.open_history_folder)
        self.open_release_button.setEnabled(False)
        history.addWidget(self.release_history, 1)
        history.addWidget(self.refresh_button)
        history.addWidget(self.open_release_button)
        layout.addLayout(history)

        layout.addWidget(QLabel('Compare previous Band Mixer WAVs (play one at a time)'))
        compare = QHBoxLayout()
        self.compare_a = QComboBox()
        self.compare_b = QComboBox()
        self.compare_a.setObjectName('release_compare_a')
        self.compare_b.setObjectName('release_compare_b')
        self.play_a = QPushButton('Listen A')
        self.play_a.clicked.connect(lambda: self.audition(self.compare_a.currentData()))
        self.play_b = QPushButton('Listen B')
        self.play_b.clicked.connect(lambda: self.audition(self.compare_b.currentData()))
        self.refresh_comparison = QPushButton('Refresh mixes')
        self.refresh_comparison.clicked.connect(self.refresh_comparisons)
        for element in (self.compare_a, self.play_a, self.compare_b,
                        self.play_b, self.refresh_comparison):
            compare.addWidget(element)
        layout.addLayout(compare)
        layout.addStretch()
        self.refresh_releases()
        self.refresh_comparisons()

    def browse_source(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 'Choose a completed WAV mix', str(Path.home()), 'WAV audio (*.wav)',
        )
        if path:
            self.source.setText(path)

    def import_last_mix(self):
        if self.band_mixer is None or not self.band_mixer.last_mix:
            self.status.setText('Render a Band Mixer WAV first.')
            return
        try:
            source = validate_source(self.band_mixer.last_mix)
            self.source.setText(str(source))
            self.status.setText('Band Mixer output selected. Choose the formats to export.')
        except (MixError, OSError) as error:
            self.status.setText(str(error))

    def selected_profiles(self):
        return tuple(key for key in ALL_PROFILES if self.profile_boxes[key].isChecked())

    def start_export(self):
        if self.worker is not None:
            return
        try:
            source = validate_source(self.source.text().strip())
            selected = self.selected_profiles()
            if not selected:
                raise MixError('Select at least one release format.')
        except (MixError, OSError, ValueError) as error:
            self.status.setText(str(error))
            return
        self.worker = ReleaseWorker(source, selected)
        self.worker.result.connect(self.export_done)
        self.worker.finished.connect(self.export_finished)
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status.setText('Encoding selected formats locally. Original WAV is unchanged.')
        self.worker.start()

    def stop_export(self):
        if self.worker is not None:
            self.worker.stop.set()
            self.stop_button.setEnabled(False)
            self.status.setText('Stopping release export. Original WAV is unchanged.')

    def export_done(self, folder, message):
        self.last_folder = Path(folder) if folder else None
        self.folder_button.setEnabled(bool(folder))
        self.status.setText(message + (' ' + folder if folder else ''))
        if folder:
            self.refresh_releases()

    def export_finished(self):
        worker, self.worker = self.worker, None
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        if worker is not None:
            worker.deleteLater()

    def refresh_releases(self):
        self.release_history.clear()
        try:
            for entry in list_releases():
                stamp = time.strftime('%Y-%m-%d %H:%M',
                                      time.localtime(entry['created_at_unix']))
                kinds = ', '.join(item['profile'] for item in entry['exports'])
                self.release_history.addItem(stamp + ' | ' + kinds, entry['folder'])
        except (OSError, ValueError, MixError) as error:
            self.status.setText('Cannot read private release history: ' + str(error))
        self.open_release_button.setEnabled(self.release_history.count() > 0)

    def open_history_folder(self):
        selected = self.release_history.currentData()
        if selected and Path(selected).is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(selected))

    def open_last_folder(self):
        if self.last_folder and self.last_folder.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.last_folder)))

    def refresh_comparisons(self):
        self.compare_a.clear()
        self.compare_b.clear()
        try:
            for entry in recent_mixes(limit=50):
                stamp = time.strftime('%Y-%m-%d %H:%M',
                                      time.localtime(entry['created_at_unix']))
                label = stamp + ' | ' + str(entry['track_count']) + ' stems'
                self.compare_a.addItem(label, entry['file'])
                self.compare_b.addItem(label, entry['file'])
            if self.compare_b.count() > 1:
                self.compare_b.setCurrentIndex(1)
        except (OSError, ValueError, MixError) as error:
            self.status.setText('Cannot list previous mixes: ' + str(error))

    def audition(self, source):
        if not source:
            self.status.setText('Select a previous mix to listen to.')
            return
        try:
            audio = valid_wav(source, 'previous mix')
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(audio))):
                self.status.setText('The audio player did not open. Use your installed DAW.')
        except (OSError, MixError):
            self.status.setText('Previous mix audio was moved or cannot be opened.')

    def closeEvent(self, event):
        if self.worker is not None:
            self.worker.shutdown()
        super().closeEvent(event)
