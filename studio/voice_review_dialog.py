"""Native, human-in-the-loop A/B My Voice audition and scoring window."""
import json
from pathlib import Path
import threading

from PyQt5.QtCore import Qt, QThread, QUrl, pyqtSignal
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QDialog, QFileDialog, QFormLayout,
    QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QSpinBox, QTextEdit, QVBoxLayout,
)

if __package__:
    from .voice_listening import (VoiceSampleError, CRITERIA,
                                  create_voice_trial, save_voice_review)
else:
    from voice_listening import (VoiceSampleError, CRITERIA,
                                create_voice_trial, save_voice_review)


class TrialWorker(QThread):
    result = pyqtSignal(str, str)

    def __init__(self, original, converted):
        super().__init__(QApplication.instance())
        self.original, self.converted = original, converted
        self.stop = threading.Event()
        QApplication.instance().aboutToQuit.connect(self.shutdown)

    def shutdown(self):
        self.stop.set()
        self.wait()

    def run(self):
        try:
            folder = create_voice_trial(self.original, self.converted, stop=self.stop)
            self.result.emit(str(folder), "Blind comparison ready. Listen to A and B, then rate each.")
        except (VoiceSampleError, OSError) as error:
            self.result.emit("", str(error))


class VoiceReviewDialog(QDialog):
    """Blind labels are A/B, while private assignment is disclosed after ratings."""

    def __init__(self, original=None, converted=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Spider Studio: My Voice Listening Review")
        self.resize(770, 560)
        self.trial = None
        self.worker = None
        layout = QVBoxLayout(self)
        message = QLabel(
            "Compare original and converted singing excerpts by listening. "
            "Studio randomly labels them A/B and does not guess speaker identity, "
            "match loudness, or certify a trained model. These should be the "
            "same sung performance with matching timing."
        )
        message.setWordWrap(True)
        layout.addWidget(message)
        input_form = QFormLayout()
        self.source = QLineEdit(str(original) if original else "")
        self.converted = QLineEdit(str(converted) if converted else "")
        input_form.addRow("Original isolated vocal", self.source)
        input_form.addRow("Converted isolated vocal", self.converted)
        layout.addLayout(input_form)
        browse_row = QHBoxLayout()
        self.original_button = QPushButton("Choose original WAV")
        self.original_button.clicked.connect(lambda: self.pick_file(self.source))
        self.converted_button = QPushButton("Choose converted WAV")
        self.converted_button.clicked.connect(lambda: self.pick_file(self.converted))
        self.prepare_button = QPushButton("Create private A/B trial")
        self.prepare_button.clicked.connect(self.start_trial)
        self.cancel_button = QPushButton("Stop preparation")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel)
        for button in (self.original_button, self.converted_button,
                       self.prepare_button, self.cancel_button):
            browse_row.addWidget(button)
        layout.addLayout(browse_row)
        self.status = QLabel("Prepare a trial, listen to both candidates, then record a manual review.")
        self.status.setTextFormat(Qt.PlainText)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        listens = QHBoxLayout()
        self.listen_a = QPushButton("Listen to A")
        self.listen_b = QPushButton("Listen to B")
        self.listen_a.clicked.connect(lambda: self.listen("A"))
        self.listen_b.clicked.connect(lambda: self.listen("B"))
        listens.addWidget(self.listen_a)
        listens.addWidget(self.listen_b)
        layout.addLayout(listens)
        rating_note = QLabel(
            "Rate A and B independently from 1 (poor) to 5 (excellent). "
            "'Artifact-free' means less audible digital noise or warbling, not proof of identity."
        )
        rating_note.setWordWrap(True)
        layout.addWidget(rating_note)
        ratings = QGridLayout()
        ratings.addWidget(QLabel("Listening criterion"), 0, 0)
        ratings.addWidget(QLabel("A"), 0, 1)
        ratings.addWidget(QLabel("B"), 0, 2)
        self.ratings = {}
        for index, category in enumerate(CRITERIA, 1):
            ratings.addWidget(QLabel(category.replace("_", " ").title()), index, 0)
            self.ratings[category] = {}
            for col, label in ((1, "A"), (2, "B")):
                score = QSpinBox()
                score.setRange(1, 5)
                score.setValue(3)
                self.ratings[category][label] = score
                ratings.addWidget(score, index, col)
        layout.addLayout(ratings)
        self.heard = QCheckBox("I have listened to both A and B; these are my own subjective ratings")
        layout.addWidget(self.heard)
        self.notes = QTextEdit()
        self.notes.setMaximumHeight(80)
        self.notes.setPlaceholderText("Optional listening notes, up to 500 characters")
        layout.addWidget(self.notes)
        actions = QHBoxLayout()
        self.save_button = QPushButton("Save private listener review")
        self.save_button.clicked.connect(self.save_review)
        self.open_button = QPushButton("Open trial folder")
        self.open_button.clicked.connect(self.open_trial)
        actions.addWidget(self.save_button)
        actions.addWidget(self.open_button)
        layout.addLayout(actions)
        self._set_trial_ready(False)

    def _set_trial_ready(self, enabled):
        for widget in (self.listen_a, self.listen_b, self.save_button, self.open_button):
            widget.setEnabled(enabled)

    def pick_file(self, field):
        value, _ = QFileDialog.getOpenFileName(
            self, "Choose isolated PCM vocal", str(Path.home()), "WAV audio (*.wav)")
        if value:
            field.setText(value)

    def start_trial(self):
        if self.worker is not None:
            return
        self.trial = None
        self.heard.setChecked(False)
        self._set_trial_ready(False)
        self.prepare_button.setEnabled(False)
        self.original_button.setEnabled(False)
        self.converted_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.status.setText("Preparing private copies with randomized A/B labels...")
        self.worker = TrialWorker(self.source.text().strip(), self.converted.text().strip())
        self.worker.result.connect(self.trial_done)
        self.worker.finished.connect(self.trial_finished)
        self.worker.start()

    def trial_done(self, folder, status):
        self.status.setText(status)
        if folder:
            self.trial = Path(folder)
            self._set_trial_ready(True)

    def trial_finished(self):
        worker, self.worker = self.worker, None
        self.prepare_button.setEnabled(True)
        self.original_button.setEnabled(True)
        self.converted_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        if worker is not None:
            worker.deleteLater()

    def cancel(self):
        if self.worker is not None:
            self.worker.stop.set()
            self.cancel_button.setEnabled(False)
            self.status.setText("Stopping preparation. No original vocal will be altered.")

    def listen(self, label):
        if self.trial is None:
            return
        audio = self.trial / (label + ".wav")
        if (audio.is_symlink() or not audio.is_file()
                or not QDesktopServices.openUrl(QUrl.fromLocalFile(str(audio)))):
            self.status.setText("Could not open the chosen trial WAV in an audio player.")

    def save_review(self):
        if self.trial is None:
            self.status.setText("Create the A/B trial before scoring.")
            return
        rating = {
            label: {kind: self.ratings[kind][label].value() for kind in CRITERIA}
            for label in ("A", "B")
        }
        try:
            receipt = save_voice_review(
                self.trial, rating, listened_to_both=self.heard.isChecked(),
                notes=self.notes.toPlainText())
            data = json.loads(receipt.read_text(encoding="utf-8"))
            assignment = data["assignment_revealed_after_scoring"]
            self.status.setText(
                f"Listener review saved. A was {assignment['A']}; B was {assignment['B']}. "
                "Scores are your subjective impressions, NOT automatic voice-model qualification."
            )
        except (VoiceSampleError, OSError, ValueError) as error:
            self.status.setText(str(error))

    def open_trial(self):
        if self.trial and not self.trial.is_symlink() and self.trial.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.trial)))

    def closeEvent(self, event):
        if self.worker is not None:
            self.worker.shutdown()
        super().closeEvent(event)
