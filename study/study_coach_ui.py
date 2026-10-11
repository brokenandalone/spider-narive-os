"""Explicit opt-in Webbie tutoring through the existing local Ollama backend."""
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QComboBox, QMessageBox, QCheckBox, QApplication,
)
try:
    from .study_coach import build_coach_prompt, parse_generated_flashcards
    from .homework import webbie_draft
except ImportError:
    from study_coach import build_coach_prompt, parse_generated_flashcards
    from homework import webbie_draft


class CoachWorker(QThread):
    ready = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, prompt, parent=None):
        super().__init__(parent)
        self.prompt = prompt

    def run(self):
        try:
            self.ready.emit(webbie_draft(self.prompt))
        except Exception as error:
            self.failed.emit(str(error))


class StudyCoachDialog(QDialog):
    def __init__(self, parent=None, *, course="", topic="", materials="",
                 notes="", store=None, course_id=None):
        super().__init__(parent)
        self.setWindowTitle("Study | Webbie Learning Coach")
        self.resize(910, 800)
        self.setMinimumSize(730, 570)
        self.store = store
        self.course_id = course_id
        self.session = []
        self.worker = None
        self.pending_request = ""
        self.latest_answer = ""
        self.selected_notes = str(notes)
        layout = QVBoxLayout(self)
        intro = QLabel("Practice with local Webbie. Choose the exact material she sees. "
                       "Generated explanations and quiz answers can be wrong; "
                       "check against verified course sources.")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        form = QFormLayout()
        self.course = QLineEdit(str(course))
        self.course.setReadOnly(True)
        self.topic = QLineEdit(str(topic))
        self.topic.setMaxLength(350)
        self.topic.setPlaceholderText("Concept, chapter or assignment topic")
        self.mode = QComboBox()
        self.mode.addItem("Explain a concept", "explain")
        self.mode.addItem("Socratic questions", "socratic")
        self.mode.addItem("Practice quiz with separate answer key", "quiz")
        self.mode.addItem("Structured study guide", "study_guide")
        self.mode.addItem("Draft flashcards from selected notes", "flashcards")
        self.materials = QTextEdit()
        self.materials.setAcceptRichText(False)
        self.materials.setPlainText(str(materials))
        self.materials.setMaximumHeight(145)
        self.materials.setPlaceholderText("Paste verified excerpts or your own notes. Review everything selected.")
        self.notes_checkbox = QCheckBox("Include selected course notes (currently off)")
        self.notes_checkbox.setChecked(False)
        self.question = QLineEdit()
        self.question.setMaxLength(2000)
        self.question.setPlaceholderText("A question or follow-up, optional if material is supplied")
        for label, widget in [
            ("Course", self.course), ("Topic", self.topic),
            ("Learning mode", self.mode), ("Selected study material", self.materials),
            ("Notes option", self.notes_checkbox), ("Your question", self.question),
        ]:
            form.addRow(label, widget)
        layout.addLayout(form)
        self.response = QTextEdit()
        self.response.setReadOnly(True)
        self.response.setPlaceholderText(
            "Webbie's latest tutoring response appears here after you press Ask Webbie.")
        layout.addWidget(self.response, 1)
        self.status = QLabel("Ready. Webbie receives no material until you press Ask Webbie.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        actions = QHBoxLayout()
        self.ask_button = QPushButton("Ask Webbie")
        self.ask_button.clicked.connect(self.ask)
        actions.addWidget(self.ask_button)
        self.copy_button = QPushButton("Copy answer")
        self.copy_button.clicked.connect(self.copy_response)
        actions.addWidget(self.copy_button)
        self.cards_button = QPushButton("Preview and save flashcards")
        self.cards_button.clicked.connect(self.save_flashcards)
        actions.addWidget(self.cards_button)
        self.clear_button = QPushButton("Clear tutoring history")
        self.clear_button.clicked.connect(self.clear_history)
        actions.addWidget(self.clear_button)
        layout.addLayout(actions)

    def selected_material(self):
        text = self.materials.toPlainText().strip()
        if self.notes_checkbox.isChecked() and self.selected_notes.strip():
            text += ("\n\nCOURSE NOTES SELECTED BY OWNER:\n" +
                     self.selected_notes[:9000])
        return text

    def ask(self):
        if self.worker is not None:
            return
        history = "\n\n".join(self.session[-6:])
        try:
            prompt = build_coach_prompt(
                course=self.course.text(), topic=self.topic.text(),
                material=self.selected_material(), mode=self.mode.currentData(),
                question=self.question.text(), history=history)
        except ValueError as error:
            QMessageBox.warning(self, "Study Coach", str(error))
            return
        self.pending_request = self.question.text()
        self.worker = CoachWorker(prompt, self)
        self.worker.ready.connect(self.answer_ready)
        self.worker.failed.connect(self.answer_failed)
        self.worker.finished.connect(self.release_worker)
        self.ask_button.setEnabled(False)
        self.cards_button.setEnabled(False)
        self.status.setText("Local Webbie is preparing a response. No school data is submitted.")
        self.worker.start()

    def answer_ready(self, answer):
        self.latest_answer = answer
        self.response.setPlainText(answer)
        self.session.append("STUDENT: " + self.pending_request[:2000] +
                            "\nWEBBIE: " + answer[:5000])
        self.session = self.session[-10:]
        self.status.setText("Response ready. Check facts against your actual course materials.")

    def answer_failed(self, error):
        self.status.setText("Webbie tutor unavailable: " + error +
                            ". Your study materials remain in this window.")

    def release_worker(self):
        if self.worker is not None:
            self.worker.deleteLater()
            self.worker = None
        self.ask_button.setEnabled(True)
        self.cards_button.setEnabled(True)

    def copy_response(self):
        if not self.response.toPlainText().strip():
            return
        QApplication.clipboard().setText(self.response.toPlainText())
        self.status.setText("Copied the visible Webbie response to your clipboard.")

    def save_flashcards(self):
        if self.worker is not None:
            return
        if self.store is None or self.course_id is None:
            QMessageBox.information(
                self, "Flashcards", "Choose a course in Study to save practice cards.")
            return
        cards = parse_generated_flashcards(self.response.toPlainText())
        if not cards:
            QMessageBox.information(
                self, "Flashcards", "Ask Webbie for Flashcards and review her Q:/A: pairs first.")
            return
        preview = "\n".join(f"{i+1}. {q[:90]} | {a[:90]}"
                            for i, (q, a) in enumerate(cards))
        answer = QMessageBox.question(
            self, "Review AI-generated study cards",
            f"Add these {len(cards)} cards to the selected course?\n\n{preview}\n\n"
            "AI-generated answers are unverified. Read every card before saving.")
        if answer != QMessageBox.Yes:
            return
        try:
            count = self.store.add_flashcards(self.course_id, cards)
            self.status.setText(
                f"Saved {count} new unverified practice cards locally. "
                f"{len(cards)-count} duplicate cards skipped.")
        except ValueError as error:
            QMessageBox.warning(self, "Flashcards", str(error))

    def clear_history(self):
        self.session.clear()
        self.latest_answer = ""
        self.response.clear()
        self.status.setText("In-memory tutoring history cleared. No file was deleted.")

    def closeEvent(self, event):
        if self.worker is not None:
            event.ignore()
            self.status.setText("Webbie is responding. Close after the request completes.")
            return
        super().closeEvent(event)
