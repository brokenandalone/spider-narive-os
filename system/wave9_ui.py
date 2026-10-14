"""Wave 9 Operations Hub tab: owner-click music, vision, canon and desktop checks.

Nothing runs on startup. All long operations use a bounded worker. Camera or
screen understanding requires new confirmation for every single image.
"""
from __future__ import annotations
import json
from pathlib import Path
import threading

from PyQt5.QtCore import QBuffer, QByteArray, QIODevice, Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout,
    QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMessageBox,
    QPlainTextEdit, QPushButton, QSpinBox, QTabWidget, QVBoxLayout, QWidget,
)

from wave9_music import SongDraft, engine_health, render_song
from wave9_visual import camera_inventory, capture_camera_once, analyze_one_frame
from wave9_canon import canon_proposal_review
from wave9_desktop import desktop_continuity


class UserActionWorker(QThread):
    complete = pyqtSignal(object)
    failed = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, func, args=(), kwargs=None, parent=None):
        super().__init__(parent)
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        self.stop = threading.Event()

    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
            self.complete.emit(result)
        except Exception as error:
            # Do not dump text from selected private documents or backend
            # stack traces into the GUI or terminal.
            self.failed.emit(
                "Operation failed (" + type(error).__name__ + "). "
                "Check local dependencies and the selected files."
            )


class Wave9Panel(QWidget):
    def __init__(self, publish, parent=None):
        super().__init__(parent)
        self.publish = publish
        self.worker = None
        self.current_operation = ""
        self.draft = None
        self.destination = None
        self.canon_files = [None, None]
        self.canon_folder = None
        outer = QVBoxLayout(self)
        title = QLabel("WAVE 9  /  LOCAL CREATIVE + VISUAL WORKSPACE")
        title.setStyleSheet("font-weight:bold;font-size:16px;color:#d7baff;")
        outer.addWidget(title)
        notice = QLabel(
            "Actions below are optional. Vision is one frame at a time; "
            "song generation uses an existing localhost ACE-Step engine. "
            "No background capture, model download or unattended desktop control."
        )
        notice.setWordWrap(True)
        outer.addWidget(notice)
        self.sections = QTabWidget()
        self.sections.setUsesScrollButtons(True)
        outer.addWidget(self.sections, 1)
        self._music_page()
        self._visual_page()
        self._canon_page()
        self._desktop_page()
        footer = QHBoxLayout()
        self.status = QLabel("Ready. Nothing is executing.")
        self.status.setWordWrap(True)
        footer.addWidget(self.status, 1)
        self.stop_button = QPushButton("Stop waiting")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_waiting)
        footer.addWidget(self.stop_button)
        outer.addLayout(footer)
        self.report = QPlainTextEdit()
        self.report.setReadOnly(True)
        self.report.setMaximumHeight(220)
        outer.addWidget(self.report)

    def _page(self, name, help_text):
        page = QWidget()
        layout = QVBoxLayout(page)
        explanation = QLabel(help_text)
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        self.sections.addTab(page, name)
        return layout

    def _music_page(self):
        layout = self._page("Studio AI", "Preview a song, check local ACE-Step, "
                            "or deliberately submit a render. Generated takes "
                            "are placed only in an output folder you select.")
        form = QFormLayout()
        layout.addLayout(form)
        self.song_title = QLineEdit()
        self.song_title.setMaxLength(200)
        self.song_title.setPlaceholderText("Song title")
        form.addRow("Title", self.song_title)
        self.song_style = QPlainTextEdit()
        self.song_style.setMaximumHeight(76)
        self.song_style.setPlainText(
            "Dark Southern gothic metal, post-grunge, modern hard rock, "
            "deep baritone, seven-string guitar, cinematic piano."
        )
        form.addRow("Style", self.song_style)
        self.song_lyrics = QPlainTextEdit()
        self.song_lyrics.setMaximumHeight(118)
        self.song_lyrics.setPlaceholderText("Original lyrics, or choose instrumental")
        form.addRow("Lyrics", self.song_lyrics)
        self.instrumental = QCheckBox("Instrumental (no lyrics needed)")
        form.addRow("", self.instrumental)
        self.endpoint = QLineEdit("http://127.0.0.1:8001")
        self.endpoint.setPlaceholderText("Loopback music engine URL")
        form.addRow("Local engine", self.endpoint)
        self.duration = QSpinBox()
        self.duration.setRange(10, 600)
        self.duration.setValue(180)
        form.addRow("Seconds", self.duration)
        self.takes = QSpinBox()
        self.takes.setRange(1, 2)
        self.takes.setValue(1)
        form.addRow("Takes", self.takes)
        self.bpm = QSpinBox()
        self.bpm.setRange(0, 300)
        self.bpm.setValue(0)
        self.bpm.setSpecialValueText("Auto")
        form.addRow("BPM", self.bpm)
        row = QHBoxLayout()
        layout.addLayout(row)
        preview = QPushButton("Preview request")
        preview.clicked.connect(self.preview_music)
        row.addWidget(preview)
        health = QPushButton("Check local engine")
        health.clicked.connect(
            lambda: self._start(
                "Studio engine readiness", engine_health, self.endpoint.text()
            )
        )
        row.addWidget(health)
        generate = QPushButton("GENERATE (ask before submit)")
        generate.clicked.connect(self.generate_music)
        row.addWidget(generate)
        layout.addStretch(1)

    def _draft(self):
        return SongDraft(
            title=self.song_title.text(),
            style=self.song_style.toPlainText(),
            lyrics=self.song_lyrics.toPlainText(),
            instrumental=self.instrumental.isChecked(),
            seconds=self.duration.value(),
            takes=self.takes.value(),
            bpm=self.bpm.value(),
            endpoint=self.endpoint.text().strip(),
        )

    def preview_music(self):
        if self.is_busy():
            return
        try:
            self.draft = self._draft()
            result = self.draft.preview()
        except (ValueError, RuntimeError, OSError) as error:
            self._warn("Studio", type(error).__name__ + ": " + str(error)[:220])
            return
        self._publish("Studio", result)

    def generate_music(self):
        if self.is_busy():
            return
        try:
            draft = self._draft()
            draft.validate()
        except (ValueError, RuntimeError, OSError) as error:
            self._warn("Studio", type(error).__name__ + ": " + str(error)[:220])
            return
        folder = QFileDialog.getExistingDirectory(
            self, "Choose an existing folder for newly generated song takes",
            str(Path.home()),
        )
        if not folder:
            return
        answer = QMessageBox.question(
            self, "Submit a LOCAL music generation?",
            "Generate " + str(draft.takes) + " original take(s) of " +
            str(draft.seconds) + " seconds using the local ACE-Step engine?\n"
            "This will create new WAV files and an engine job manifest in "
            "your selected folder. The request may continue on the server "
            "after you press Stop waiting.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        self._start_render(draft, folder)

    def _start_render(self, draft, folder):
        if self.is_busy():
            return
        self.worker = UserActionWorker(
            lambda: render_song(
                draft, folder, owner_approved=True, stop=self.worker.stop,
                progress=self.worker.progress.emit,
            ), parent=self,
        )
        self._wire("Studio audio render", cancellable=True)

    def _visual_page(self):
        layout = self._page(
            "Webbie Vision", "Single-shot camera or screen descriptions "
            "using existing Webbie camera capture and LOCAL Ollama vision. "
            "Only click when the room and screen contain nothing you do not "
            "intend the local model to process. No automatic observation."
        )
        self.vision_model = QLineEdit("qwen3-vl:2b-instruct")
        layout.addWidget(QLabel("Existing local Ollama vision model:"))
        layout.addWidget(self.vision_model)
        row = QHBoxLayout()
        layout.addLayout(row)
        inventory = QPushButton("List camera devices")
        inventory.clicked.connect(lambda: self._start(
            "Camera inventory", camera_inventory
        ))
        row.addWidget(inventory)
        camera = QPushButton("Describe ONE camera frame")
        camera.clicked.connect(self.start_camera)
        row.addWidget(camera)
        screen = QPushButton("Describe ONE screen snapshot")
        screen.clicked.connect(self.start_screen)
        row.addWidget(screen)
        layout.addStretch(1)

    def start_camera(self):
        if self.is_busy():
            return
        try:
            available = camera_inventory()["devices"]
        except (OSError, ValueError, RuntimeError) as error:
            self._warn("Webbie Vision", type(error).__name__)
            return
        if not available:
            self._warn("Webbie Vision", "No available /dev/video camera found.")
            return
        device, ok = QInputDialog.getItem(
            self, "Select existing camera", "Camera device", available,
            0, False,
        )
        if not ok:
            return
        if QMessageBox.question(
            self, "Allow ONE camera capture?",
            "Capture ONE 640×480 camera image and describe it with a model "
            "running on THIS computer? No photo will be saved automatically.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        self._start(
            "Webbie camera frame", capture_camera_once, device,
            user_approved=True, model=self.vision_model.text().strip(),
        )

    def start_screen(self):
        if self.is_busy():
            return
        if QMessageBox.question(
            self, "Allow ONE screen capture?",
            "Capture your visible PRIMARY screen once and send that image "
            "ONLY to locally running Ollama? This may include private "
            "windows, passwords or notifications. Close anything sensitive.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        screen = QApplication.primaryScreen()
        if screen is None:
            self._warn("Screen", "No graphical primary display.")
            return
        pixmap = screen.grabWindow(0)
        if pixmap.isNull():
            self._warn("Screen", "Screen capture was not available.")
            return
        scaled = pixmap.scaled(
            1024, 768, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        buffer = QBuffer()
        buffer.open(QIODevice.WriteOnly)
        if not scaled.save(buffer, "JPEG", 75):
            self._warn("Screen", "JPEG conversion failed.")
            return
        jpeg = bytes(buffer.data())
        buffer.close()
        del pixmap, scaled
        self._start(
            "Webbie single-screen description", analyze_one_frame, jpeg,
            user_approved=True, source="screen",
            model=self.vision_model.text().strip(),
        )

    def _canon_page(self):
        layout = self._page(
            "Author Canon", "Compare an approved JSON canon ledger and a "
            "separate proposal ledger against an explicitly selected chapter "
            "folder. This creates review warnings, not canon changes."
        )
        row = QHBoxLayout()
        layout.addLayout(row)
        for index, label in ((0, "Approved claims JSON..."),
                             (1, "Proposed claims JSON...")):
            button = QPushButton(label)
            button.clicked.connect(
                lambda checked=False, slot=index: self.choose_canon_file(slot)
            )
            row.addWidget(button)
        self.canon_labels = [QLabel("Not selected."), QLabel("Not selected.")]
        for label in self.canon_labels:
            layout.addWidget(label)
        folder_btn = QPushButton("Choose manuscript chapter folder...")
        folder_btn.clicked.connect(self.choose_canon_folder)
        layout.addWidget(folder_btn)
        self.canon_folder_label = QLabel("No chapter folder selected.")
        layout.addWidget(self.canon_folder_label)
        review = QPushButton("Review possible canon disagreements")
        review.clicked.connect(self.review_canon)
        layout.addWidget(review)
        layout.addStretch(1)

    def choose_canon_file(self, index):
        if self.is_busy():
            return
        chosen, _ = QFileDialog.getOpenFileName(
            self, "Choose a local canon claims file",
            str(Path.home()), "Canon JSON (*.json)"
        )
        if chosen:
            self.canon_files[index] = chosen
            self.canon_labels[index].setText(Path(chosen).name)

    def choose_canon_folder(self):
        if self.is_busy():
            return
        chosen = QFileDialog.getExistingDirectory(
            self, "Choose book chapter folder", str(Path.home())
        )
        if chosen:
            self.canon_folder = chosen
            self.canon_folder_label.setText(Path(chosen).name)

    def review_canon(self):
        if self.is_busy():
            return
        if not (all(self.canon_files) and self.canon_folder):
            self._warn("Author", "Select both JSON files and a chapter folder.")
            return
        self._start("Broken World canon review", canon_proposal_review,
                    *self.canon_files, self.canon_folder)

    def _desktop_page(self):
        layout = self._page(
            "The Web", "Inspect existing Studio, Author, Study, Forage and "
            "Kali launcher wiring and desktop session status. Do not start "
            "a second shell or modify desktop shortcuts."
        )
        inspect = QPushButton("Check workspace launchers")
        inspect.clicked.connect(lambda: self._start(
            "The Web workspace continuity", desktop_continuity
        ))
        layout.addWidget(inspect)
        layout.addStretch(1)

    def _start(self, name, function, *args, **kwargs):
        if self.is_busy():
            return
        self.worker = UserActionWorker(function, args=args, kwargs=kwargs,
                                       parent=self)
        self._wire(name, cancellable=False)

    def _wire(self, name, cancellable):
        self.current_operation = name
        worker = self.worker
        worker.complete.connect(self._finished_report)
        worker.failed.connect(self._failed)
        worker.progress.connect(self.status.setText)
        worker.finished.connect(self._finish)
        self.stop_button.setEnabled(cancellable)
        self.status.setText(name + " is running. No other operation starts concurrently.")
        worker.start()

    def _publish(self, name, report):
        self.report.setPlainText(json.dumps(
            report, indent=2, ensure_ascii=False, sort_keys=True
        ))
        self.status.setText(name + ": complete.")
        self.publish("Wave 9", report)

    def _finished_report(self, report):
        self._publish(self.current_operation, report)

    def _failed(self, message):
        self.status.setText(self.current_operation + ": " + message)

    def _finish(self):
        self.stop_button.setEnabled(False)

    def is_busy(self):
        return bool(self.worker is not None and self.worker.isRunning())

    def stop_waiting(self):
        if self.is_busy() and self.stop_button.isEnabled():
            self.worker.stop.set()
            self.status.setText(
                "Stop requested. Waiting will end, but ACE-Step may still "
                "finish its already-submitted server job."
            )

    def _warn(self, name, message):
        self.status.setText(name + ": " + str(message)[:250])
        QMessageBox.warning(self, name, str(message)[:250])
