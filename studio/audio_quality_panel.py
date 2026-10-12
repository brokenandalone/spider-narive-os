"""Spider Studio v11: non-destructive audio-quality checks for local WAV takes.

This panel never records audio, runs an AI model, changes files, or publishes.
"""
import threading
from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QPlainTextEdit, QVBoxLayout, QWidget,
)

if __package__:
    from .audio_quality import QualityError, audit_assets
    from .production_board import ROLES
else:
    from audio_quality import QualityError, audit_assets
    from production_board import ROLES


class AudioQualityWorker(QThread):
    result = pyqtSignal(object, str)

    def __init__(self, assets):
        super().__init__(QApplication.instance())
        self.assets = dict(assets)
        self.stop = threading.Event()
        QApplication.instance().aboutToQuit.connect(self.shutdown)

    def shutdown(self):
        self.stop.set()
        self.wait()

    def run(self):
        try:
            self.result.emit(audit_assets(self.assets, stop=self.stop), '')
        except (QualityError, ValueError, OSError) as error:
            self.result.emit(None, str(error))
        except Exception:
            self.result.emit(None, 'Audio preflight failed. Check the source WAV files.')


class AudioQualityPanel(QWidget):
    def __init__(self, production_board=None, parent=None):
        super().__init__(parent)
        self.production_board = production_board
        self.worker = None
        self.sources = {}
        layout = QVBoxLayout(self)
        heading = QLabel('STUDIO AUDIO QUALITY CHECK')
        heading.setStyleSheet('font-size:22px; color:#c4b5fd; font-weight:bold;')
        layout.addWidget(heading)
        note = QLabel(
            'Read-only PCM audio sampling: sample peak, RMS, possible near-full-scale '
            'samples, silence, DC bias, duration and sample-rate warnings. '
            'Checks the first and last eight seconds only. NOT LUFS, true-peak '
            'mastering, hearing-based evaluation, automatic timing or stem verification.'
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        for role in ROLES:
            row = QHBoxLayout()
            label = QLabel(role.replace('_', ' ').title())
            field = QLineEdit()
            field.setObjectName('qc_source_' + role)
            field.setPlaceholderText('Optional owner-selected WAV')
            browse = QPushButton('Choose WAV')
            browse.clicked.connect(lambda checked=False, key=role: self.browse_source(key))
            row.addWidget(label)
            row.addWidget(field, 1)
            row.addWidget(browse)
            layout.addLayout(row)
            self.sources[role] = field

        row = QHBoxLayout()
        self.import_button = QPushButton('Copy Production Board selections')
        self.import_button.clicked.connect(self.import_board)
        self.import_button.setEnabled(production_board is not None)
        self.start_button = QPushButton('Inspect selected WAVs')
        self.start_button.clicked.connect(self.start_check)
        self.cancel_button = QPushButton('Stop analysis')
        self.cancel_button.clicked.connect(self.cancel_check)
        self.cancel_button.setEnabled(False)
        for button in (self.import_button, self.start_button, self.cancel_button):
            row.addWidget(button)
        layout.addLayout(row)
        self.status = QLabel('No audio has been inspected.')
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.PlainText)
        layout.addWidget(self.status)
        self.report = QPlainTextEdit()
        self.report.setReadOnly(True)
        self.report.setObjectName('quality_report')
        self.report.setPlaceholderText('The read-only audio quality report appears here.')
        self.report.setMinimumHeight(270)
        layout.addWidget(self.report)

    def browse_source(self, role):
        selected, _ = QFileDialog.getOpenFileName(
            self, 'Select existing WAV to inspect', str(Path.home()), 'PCM WAV (*.wav)',
        )
        if selected:
            self.sources[role].setText(selected)

    def import_board(self):
        if self.worker is not None:
            self.status.setText('Complete or stop the current inspection first.')
            return
        if self.production_board is None:
            self.status.setText('Production Board is unavailable.')
            return
        for role in ROLES:
            self.sources[role].setText(self.production_board.sources[role].text())
        self.status.setText(
            'Selected WAV paths copied locally. No recordings changed or approved.'
        )

    def selected(self):
        return {role: field.text().strip() for role, field in self.sources.items()
                if field.text().strip()}

    def start_check(self):
        if self.worker is not None:
            return
        assets = self.selected()
        if not assets:
            self.status.setText('Select one or more WAV recordings first.')
            return
        self.worker = AudioQualityWorker(assets)
        self.worker.result.connect(self.check_done)
        self.worker.finished.connect(self.check_finished)
        self.start_button.setEnabled(False)
        self.import_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.report.clear()
        self.status.setText('Reading short PCM windows without changing source audio.')
        self.worker.start()

    def cancel_check(self):
        if self.worker is not None:
            self.worker.stop.set()
            self.cancel_button.setEnabled(False)
            self.status.setText('Audio quality analysis is stopping.')

    def check_done(self, data, error):
        if error:
            self.status.setText(error)
            return
        lines = ['READ-ONLY AUDIO QC | First and last 8 seconds of each WAV', '']
        for role, item in data['tracks'].items():
            lines.extend([
                role.replace('_', ' ').title(),
                f"Duration: {item['duration_seconds']:.2f}s  "
                f"Rate: {item['sample_rate']} Hz  "
                f"Channels: {item['channels']}  "
                f"Depth: {item['sample_width_bits']}-bit",
                f"Sample peak: {item['sample_peak_dbfs']} dBFS  "
                f"RMS: {item['rms_dbfs']} dBFS  "
                f"Near-full-scale samples: {item['near_full_scale_samples']}",
            ])
            lines += ['Review: ' + warning for warning in item['warnings']]
            lines.append('')
        lines += ['Across tracks: ' + note for note in data['session_warnings']]
        lines += ['Manual listening and human approval are still required.']
        self.report.setPlainText('\n'.join(lines))
        self.status.setText(
            f"Read-only quality check finished: {len(data['tracks'])} file(s). "
            'No files were changed.'
        )

    def check_finished(self):
        worker, self.worker = self.worker, None
        self.start_button.setEnabled(True)
        self.import_button.setEnabled(self.production_board is not None)
        self.cancel_button.setEnabled(False)
        if worker is not None:
            worker.deleteLater()

    def closeEvent(self, event):
        if self.worker is not None:
            self.worker.shutdown()
        super().closeEvent(event)
