"""Optional local face-enrollment UI for two consenting people.

No enrollment is required to use Webbie's microphone, room vision or chat.
Face similarity is not voice verification and cannot approve commands.
"""
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QMessageBox
)
from webbie_camera import capture_jpeg
from webbie_faces import FaceProfiles, PROFILES, encode_face, find_enrolled_faces


class FaceWork(QThread):
    enrolled = pyqtSignal(list)
    matched = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, operation, device=None, frame=None, parent=None):
        super().__init__(parent)
        self.operation = operation
        self.device = device
        self.frame = frame

    def run(self):
        try:
            if self.operation == 'enroll':
                data = encode_face(capture_jpeg(self.device))
                if not self.isInterruptionRequested():
                    self.enrolled.emit(data)
            elif self.operation == 'match':
                data = find_enrolled_faces(self.frame, FaceProfiles())
                if not self.isInterruptionRequested():
                    self.matched.emit(data)
        except (OSError, ValueError, RuntimeError) as error:
            if not self.isInterruptionRequested():
                self.failed.emit(str(error))
        except Exception:
            if not self.isInterruptionRequested():
                self.failed.emit('Optional face matching is unavailable.')


class FaceProfileControls(QWidget):
    """Face samples belong to each individual and can be deleted separately."""

    def __init__(self, device_callback, allowed_callback, parent=None):
        super().__init__(parent)
        self.device_callback = device_callback
        self.allowed_callback = allowed_callback
        self.profiles = FaceProfiles()
        self.worker = None
        self.selected_enrollment = None
        self.last_match = ''
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        self.status = QLabel('')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        row = QHBoxLayout(); layout.addLayout(row)
        self.person = QComboBox(); self.person.addItems(PROFILES)
        row.addWidget(self.person, 1)
        self.enroll_button = QPushButton('Enroll face')
        self.enroll_button.clicked.connect(self.start_enrollment)
        row.addWidget(self.enroll_button)
        self.forget_button = QPushButton('Forget face')
        self.forget_button.clicked.connect(self.forget)
        row.addWidget(self.forget_button)
        self.refresh_status()

    def refresh_status(self):
        parts = [f'{name}: {count} sample(s)' for name, count in self.profiles.status().items()]
        self.status.setText((self.profiles.load_error or 'Optional familiar faces') + ' | ' + ' | '.join(parts) +
            ((' | Possible match: ' + self.last_match) if self.last_match else
             ' | Both profiles can stay unconfigured.'))

    def start_enrollment(self):
        if not self.allowed_callback() or not self.device_callback():
            self.status.setText('Turn the webcam on while Webbie is awake to enroll a face.')
            return
        if self.worker is not None:
            self.status.setText('Finish the current camera recognition task first.')
            return
        name = self.person.currentText()
        answer = QMessageBox.question(
            self, 'Voluntary local face enrollment',
            name + ' must be present and personally agree. Only face features '
            'are saved locally, never a photograph. A probable match does not '
            'verify the voice or authorize Spider OS commands. Enroll one sample?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if answer != QMessageBox.Yes:
            return
        self.selected_enrollment = name
        self.enroll_button.setEnabled(False)
        self.status.setText('Capturing one face sample for ' + name + '…')
        self.worker = FaceWork('enroll', device=self.device_callback(), parent=self)
        self.worker.enrolled.connect(self.on_enrolled)
        self.worker.failed.connect(self.on_failed)
        self.worker.finished.connect(self.finish)
        self.worker.start()

    def on_enrolled(self, descriptor):
        if not self.allowed_callback() or self.selected_enrollment is None:
            return
        try:
            self.profiles.enroll_descriptor(self.selected_enrollment, descriptor)
            self.refresh_status()
        except (ValueError, OSError, RuntimeError) as error:
            self.on_failed(str(error))

    def forget(self):
        name = self.person.currentText()
        if QMessageBox.question(
            self, 'Delete familiar-face samples',
            'Delete all local face samples for ' + name +
            '? This will not change Webbie’s microphone or room awareness.',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        ) != QMessageBox.Yes:
            return
        try:
            self.profiles.forget(name)
            self.last_match = ''
            self.refresh_status()
        except (ValueError, OSError) as error:
            self.on_failed(str(error))

    def inspect_frame(self, jpeg):
        if not self.allowed_callback() or not self.profiles.any_enrolled():
            return
        if self.worker is not None:
            return
        self.worker = FaceWork('match', frame=jpeg, parent=self)
        self.worker.matched.connect(self.on_matched)
        self.worker.failed.connect(self.on_failed)
        self.worker.finished.connect(self.finish)
        self.worker.start()

    def on_matched(self, labels):
        if not self.allowed_callback():
            return
        self.last_match = ', '.join(labels) if labels else ''
        self.refresh_status()

    def on_failed(self, message):
        self.status.setText('Face recognition is optional: ' + str(message))

    def finish(self):
        thread = self.sender()
        if thread is not None:
            thread.wait(300)
            thread.deleteLater()
            if self.worker is thread:
                self.worker = None
        self.selected_enrollment = None
        self.enroll_button.setEnabled(True)

    def clear_view(self):
        self.last_match = ''
        if self.worker is not None:
            self.worker.requestInterruption()
        self.refresh_status()

    def active(self):
        return self.worker is not None and self.worker.isRunning()
