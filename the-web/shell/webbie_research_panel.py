"""Webbie research desk inside her existing native bay.

Owner-controlled question queue linked to the same resident Webbie chat.
Newly added source links are *not* verified citations. No silent scraping.
"""
from pathlib import Path
import sys

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QTextEdit, QComboBox, QMessageBox,
    QInputDialog,
)

WEBBIE_ROOT = Path(__file__).resolve().parents[2] / "webbie/brain"
if str(WEBBIE_ROOT) not in sys.path:
    sys.path.insert(0, str(WEBBIE_ROOT))
from research_agenda import ResearchAgenda, STATES


class WebbieResearchPanel(QWidget):
    questionRequested = pyqtSignal(str)

    def __init__(self, parent=None, agenda=None):
        super().__init__(parent)
        self.agenda = agenda if agenda is not None else ResearchAgenda()
        self.entries = []
        layout = QVBoxLayout(self)
        title = QLabel("WEBBIE / RESEARCH MIND")
        title.setStyleSheet("font-size:20px;font-weight:bold")
        layout.addWidget(title)
        explanation = QLabel(
            "Ask anything. Keep questions, sources, uncertainty and follow-ups "
            "organized locally. Webbie can investigate when you request it; "
            "adding a web address is NOT verification of that source.")
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        row = QHBoxLayout()
        self.question = QLineEdit()
        self.question.setPlaceholderText("What should Webbie investigate next?")
        self.question.returnPressed.connect(self.add_question)
        row.addWidget(self.question, 1)
        add = QPushButton("Queue question")
        add.clicked.connect(self.add_question)
        row.addWidget(add)
        layout.addLayout(row)

        self.questions = QListWidget()
        self.questions.setMinimumHeight(160)
        self.questions.currentItemChanged.connect(self.selected_changed)
        layout.addWidget(self.questions, 1)

        ask_row = QHBoxLayout()
        self.ask_button = QPushButton("Investigate with resident Webbie")
        self.ask_button.clicked.connect(self.ask)
        ask_row.addWidget(self.ask_button)
        self.state = QComboBox()
        self.state.addItems(list(STATES))
        ask_row.addWidget(self.state)
        set_state = QPushButton("Save status")
        set_state.clicked.connect(self.save_state)
        ask_row.addWidget(set_state)
        layout.addLayout(ask_row)

        layout.addWidget(QLabel("Findings / answer draft (not automatically verified)"))
        self.finding = QTextEdit()
        self.finding.setMinimumHeight(90)
        layout.addWidget(self.finding)
        layout.addWidget(QLabel("Uncertainty / conflicting evidence"))
        self.uncertainty = QTextEdit()
        self.uncertainty.setMinimumHeight(65)
        layout.addWidget(self.uncertainty)
        save = QPushButton("Save findings and uncertainty")
        save.clicked.connect(self.save_findings)
        layout.addWidget(save)

        source_row = QHBoxLayout()
        self.url = QLineEdit()
        self.url.setPlaceholderText("Public HTTPS research source link")
        source_row.addWidget(self.url, 1)
        add_source = QPushButton("Record source (unverified)")
        add_source.clicked.connect(self.add_source)
        source_row.addWidget(add_source)
        layout.addLayout(source_row)
        follow = QPushButton("Add a follow-up question")
        follow.clicked.connect(self.add_followup)
        layout.addWidget(follow)

        self.evidence = QTextEdit()
        self.evidence.setReadOnly(True)
        self.evidence.setMaximumHeight(110)
        layout.addWidget(self.evidence)
        self.info = QLabel("")
        layout.addWidget(self.info)
        self.refresh()

    def selected(self):
        item = self.questions.currentItem()
        ident = item.data(Qt.UserRole) if item else None
        return next((e for e in self.entries if e["id"] == ident), None)

    def alert(self, error):
        QMessageBox.warning(self, "Webbie research", str(error))

    def refresh(self):
        try:
            previous = self.selected()
            previous_id = previous["id"] if previous else None
            self.entries = self.agenda.read()
            self.questions.clear()
            selected_row = 0
            for index, entry in enumerate(self.entries):
                item = QListWidgetItem(
                    "[" + entry["status"] + "] " + entry["question"])
                item.setData(Qt.UserRole, entry["id"])
                self.questions.addItem(item)
                if entry["id"] == previous_id:
                    selected_row = index
            if self.entries:
                self.questions.setCurrentRow(selected_row)
            self.info.setText("{} questions saved privately".format(len(self.entries)))
            self.selected_changed()
        except (OSError, ValueError, TypeError) as error:
            self.info.setText("Research agenda unavailable: " + str(error))

    def selected_changed(self, *_):
        entry = self.selected()
        self.ask_button.setEnabled(entry is not None)
        if not entry:
            self.finding.clear()
            self.uncertainty.clear()
            self.evidence.clear()
            return
        self.state.setCurrentText(entry["status"])
        self.finding.setPlainText(entry["finding"])
        self.uncertainty.setPlainText(entry["uncertainty"])
        self.evidence.setPlainText(
            "Sources (unverified unless independently checked):\n" +
            ("\n".join(item["url"] for item in entry["sources"]) or "None yet") +
            "\nFollow-ups:\n" + ("\n".join(entry["followups"]) or "None yet")
        )

    def add_question(self):
        try:
            self.agenda.add(self.question.text())
            self.question.clear()
            self.refresh()
        except (OSError, ValueError) as error:
            self.alert(error)

    def ask(self):
        entry = self.selected()
        if not entry:
            return
        try:
            self.agenda.edit(entry["id"], status="investigating")
            self.refresh()
            # No auto-granted computer access. The existing Webbie socket and
            # owner-controlled assistant GUI handle this intentional request.
            self.questionRequested.emit(
                "Research this question and explain evidence, sources, "
                "limitations and what should be investigated next: " + entry["question"])
        except (OSError, ValueError, KeyError) as error:
            self.alert(error)

    def save_state(self):
        entry = self.selected()
        if entry:
            try:
                self.agenda.edit(entry["id"], status=self.state.currentText())
                self.refresh()
            except (OSError, ValueError, KeyError) as error:
                self.alert(error)

    def save_findings(self):
        entry = self.selected()
        if entry:
            try:
                self.agenda.edit(entry["id"], finding=self.finding.toPlainText(),
                                 uncertainty=self.uncertainty.toPlainText())
                self.refresh()
            except (OSError, ValueError, KeyError) as error:
                self.alert(error)

    def add_source(self):
        entry = self.selected()
        if entry:
            try:
                self.agenda.add_source(entry["id"], self.url.text().strip())
                self.url.clear()
                self.refresh()
            except (OSError, ValueError, KeyError) as error:
                self.alert(error)

    def add_followup(self):
        entry = self.selected()
        if not entry:
            return
        question, yes = QInputDialog.getText(
            self, "Next research question", "Follow-up question:")
        if yes and question.strip():
            try:
                self.agenda.add_followup(entry["id"], question)
                self.refresh()
            except (OSError, ValueError, KeyError) as error:
                self.alert(error)
