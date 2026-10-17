"""Manual course flashcards and self-check review inside Study."""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTextEdit,
    QMessageBox, QFileDialog, QInputDialog, QListWidget,
)
try:
    from .flashcards import normalize_card, parse_flashcards_csv, next_card
except ImportError:
    from flashcards import normalize_card, parse_flashcards_csv, next_card


class FlashcardsDialog(QDialog):
    def __init__(self, store, course_id, course_folder, parent=None):
        super().__init__(parent)
        self.store = store
        self.course_id = course_id
        self.course_folder = course_folder
        self.deck = []
        self.index = 0
        self.showing_answer = False
        self.setWindowTitle("Study | Course flashcards")
        self.resize(670, 580)
        layout = QVBoxLayout(self)
        self.stats = QLabel()
        layout.addWidget(self.stats)
        self.front = QTextEdit()
        self.front.setReadOnly(True)
        layout.addWidget(self.front, 1)
        self.answer = QTextEdit()
        self.answer.setReadOnly(True)
        layout.addWidget(self.answer, 1)
        nav = QHBoxLayout()
        for title, callback in [
            ("Reveal answer", self.reveal), ("Remembered", self.remembered),
            ("Needs practice", self.practice), ("Next card", self.advance),
        ]:
            button = QPushButton(title)
            button.clicked.connect(callback)
            nav.addWidget(button)
        layout.addLayout(nav)
        edits = QHBoxLayout()
        for title, callback in [
            ("Add card", self.add_card), ("Import CSV", self.import_csv),
            ("Delete current card", self.remove_card), ("Refresh", self.refresh),
        ]:
            button = QPushButton(title)
            button.clicked.connect(callback)
            edits.addWidget(button)
        layout.addLayout(edits)
        layout.addWidget(QLabel(
            "Cards stay in your local Study database. Import is always previewed; "
            "no source material is uploaded." ))
        self.refresh()

    def refresh(self):
        self.deck = next_card(self.store.flashcards(self.course_id))
        self.index = min(self.index, max(0, len(self.deck) - 1))
        self.showing_answer = False
        self.display()

    def display(self):
        length = len(self.deck)
        self.stats.setText(
            f"{length} cards · Viewing {self.index + 1 if length else 0} of {length}")
        if not length:
            self.front.setPlainText("Add a card to begin reviewing.")
            self.answer.setPlainText("")
            return
        self.front.setPlainText("QUESTION:\n\n" + self.deck[self.index]["front"])
        self.answer.setPlainText("ANSWER:\n\n" + self.deck[self.index]["back"]
                                 if self.showing_answer else "Answer hidden. Select Reveal answer.")

    def reveal(self):
        if self.deck:
            self.showing_answer = True
            self.display()

    def advance(self):
        if self.deck:
            self.index = (self.index + 1) % len(self.deck)
            self.showing_answer = False
            self.display()

    def reviewed(self, correct):
        if not self.deck:
            return
        if not self.showing_answer:
            QMessageBox.information(self, "Flashcards", "Reveal the answer before scoring.")
            return
        card = self.deck[self.index]
        self.store.record_flashcard_review(card["id"], correct)
        self.refresh()

    def remembered(self):
        self.reviewed(True)

    def practice(self):
        self.reviewed(False)

    def add_card(self):
        front, ok = QInputDialog.getMultiLineText(self, "New flashcard",
                                                   "Front / question:")
        if not ok:
            return
        back, ok = QInputDialog.getMultiLineText(self, "New flashcard",
                                                  "Back / answer:")
        if not ok:
            return
        try:
            self.store.add_flashcards(self.course_id, [normalize_card(front, back)])
            self.refresh()
        except ValueError as error:
            QMessageBox.warning(self, "Flashcards", str(error))

    def import_csv(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Choose flashcards", str(self.course_folder), "Flashcards (*.csv)")
        if not filename:
            return
        try:
            result = parse_flashcards_csv(filename, self.store.flashcards(self.course_id))
        except (OSError, UnicodeError, ValueError) as error:
            QMessageBox.warning(self, "Flashcards", str(error))
            return
        cards = result["cards"]
        if not cards:
            QMessageBox.information(self, "Flashcards", "No new cards. Duplicates skipped.")
            return
        answer = QMessageBox.question(self, "Confirm import",
                                      f"Add {len(cards)} cards? "
                                      f"{result['skipped']} duplicates were skipped.")
        if answer != QMessageBox.Yes:
            return
        self.store.add_flashcards(self.course_id, cards)
        self.refresh()

    def remove_card(self):
        if not self.deck:
            return
        if QMessageBox.question(self, "Delete flashcard",
                                "Delete the displayed flashcard permanently?") != QMessageBox.Yes:
            return
        self.store.delete_flashcard(self.course_id, self.deck[self.index]["id"])
        self.refresh()
