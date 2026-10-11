"""Assignment-specific notebook and Webbie handoff inside Spider OS Study.

All sections are local, editable and explicitly saved; the idle autosave only
writes to the existing Study database. Cloud transfer and SNHU submission are
never initiated here.
"""
from pathlib import Path
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QDialog, QTabWidget, QTextEdit, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QMessageBox, QFileDialog,
)

try:
    from .assignment_workflow import (WORK_FIELDS, normalized_fields,
                                      readiness_report, webbie_directions,
                                      webbie_materials)
except ImportError:
    from assignment_workflow import (WORK_FIELDS, normalized_fields,
                                     readiness_report, webbie_directions,
                                     webbie_materials)


LABELS = {
    "instructions": "Instructions",
    "rubric": "Rubric",
    "research": "Research notes",
    "outline": "Outline",
    "draft": "My draft",
    "references": "References",
    "feedback": "Feedback",
}


class AssignmentWorkspaceDialog(QDialog):
    def __init__(self, store, assignment_id, course_folder, parent=None):
        super().__init__(parent)
        self.store = store
        self.assignment_id = assignment_id
        self.assignment = store.assignment_record(assignment_id)
        if self.assignment is None:
            raise ValueError("The selected assignment no longer exists.")
        self.folder = Path(course_folder)
        self.original = store.get_assignment_workspace(assignment_id)
        self.setWindowTitle("Study | " + self.assignment["title"])
        self.resize(1000, 810)
        self.setMinimumSize(750, 580)
        layout = QVBoxLayout(self)
        self.subtitle = QLabel(
            self.assignment["course"] + "  ·  Due: " +
            (self.assignment["due"] or "not specified") +
            "  ·  " + self.assignment["status"])
        self.subtitle.setWordWrap(True)
        layout.addWidget(self.subtitle)
        self.tabs = QTabWidget(self)
        self.editors = {}
        for name in WORK_FIELDS:
            editor = QTextEdit(self.tabs)
            editor.setAcceptRichText(False)
            editor.setPlainText(self.original[name])
            editor.setPlaceholderText("Add " + LABELS[name].lower() +
                                      " here. Saved locally for this assignment.")
            editor.textChanged.connect(self.changed)
            self.tabs.addTab(editor, LABELS[name])
            self.editors[name] = editor
        layout.addWidget(self.tabs, 1)
        self.status = QLabel("Assignment workspace opened. No school files have been transferred.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        top = QHBoxLayout()
        for caption, callback in [
            ("Save workspace", self.save),
            ("Check draft", self.check),
            ("Plan steps", self.open_steps),
            ("Research sources", self.open_sources),
            ("Work with Webbie", self.use_webbie),
            ("Export APA Word", self.export_apa),
            ("Open course folder", self.open_folder),
        ]:
            button = QPushButton(caption)
            button.clicked.connect(callback)
            top.addWidget(button)
        layout.addLayout(top)
        study_actions = QHBoxLayout()
        apa_check = QPushButton("APA and source preflight")
        apa_check.clicked.connect(self.apa_preflight)
        study_actions.addWidget(apa_check)
        tutor = QPushButton("Learn with Webbie")
        tutor.clicked.connect(self.study_with_webbie)
        study_actions.addWidget(tutor)
        layout.addLayout(study_actions)
        close = QPushButton("Close workspace")
        close.clicked.connect(self.accept)
        layout.addWidget(close)
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(4000)
        self.save_timer.timeout.connect(self.save)

    def values(self):
        return {name: editor.toPlainText() for name, editor in self.editors.items()}

    def changed(self):
        self.save_timer.start()
        self.status.setText("Unsaved edits; a local autosave will run shortly.")

    def save(self):
        self.save_timer.stop()
        try:
            values = normalized_fields(self.values())
            if values == self.original:
                self.status.setText("Workspace is already saved.")
                return True
            self.store.save_assignment_workspace(self.assignment_id, values)
            self.original = values
            self.status.setText("Assignment saved locally in Study.")
            return True
        except (ValueError, OSError, Exception) as error:
            self.status.setText("Could not save workspace: " + str(error))
            return False

    def check(self):
        try:
            report = readiness_report(self.values())
        except ValueError as error:
            QMessageBox.warning(self, "Draft check", str(error))
            return
        notes = "\n• ".join(report["missing"]) if report["missing"] else "No basic issues flagged."
        QMessageBox.information(
            self, "Draft readiness (not grading)",
            f"Draft words: {report['words']}\n"
            f"Owner-entered reference lines: {report['reference_lines']}\n\n"
            f"{notes}\n\nThis check does not verify references, APA accuracy, "
            "academic integrity, rubric satisfaction or grade.")

    def apa_preflight(self):
        """Review heuristics, not remote verification or an academic grade."""
        try:
            if __package__:
                from .apa_preflight import analyze_apa_preflight, format_apa_preflight
            else:
                from apa_preflight import analyze_apa_preflight, format_apa_preflight
            values = self.values()
            result = analyze_apa_preflight(
                draft=values["draft"], references=values["references"],
                instructions=values["instructions"] + "\n" + values["rubric"])
            dialog = QDialog(self)
            dialog.setWindowTitle("Study | APA and source preflight")
            dialog.resize(700, 520)
            layout = QVBoxLayout(dialog)
            text = QTextEdit()
            text.setReadOnly(True)
            text.setPlainText(format_apa_preflight(result))
            layout.addWidget(text)
            close = QPushButton("Return to assignment")
            close.clicked.connect(dialog.accept)
            layout.addWidget(close)
            dialog.exec_()
        except ValueError as error:
            QMessageBox.warning(self, "APA preflight", str(error))

    def study_with_webbie(self):
        """Open a local tutor with owner-visible, explicitly selected material."""
        if not self.save():
            QMessageBox.warning(self, "Study Coach", "Save your assignment before tutoring.")
            return
        try:
            if __package__:
                from .study_coach_ui import StudyCoachDialog
            else:
                from study_coach_ui import StudyCoachDialog
            fields = self.values()
            selected = "\n\n".join(
                f"{name.upper()}:\n{fields[name]}"
                for name in ("instructions", "rubric", "research")
                if fields[name].strip()
            )
            coach = StudyCoachDialog(
                self, course=self.assignment["course"],
                topic=self.assignment["title"], materials=selected,
                notes=self.store.get_notes(self.assignment["course_id"]),
                store=self.store, course_id=self.assignment["course_id"])
            coach.exec_()
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Study Coach", str(error))

    def open_steps(self):
        """Manage optional owner-entered steps without calling an AI or website."""
        try:
            if __package__:
                from .milestones_ui import MilestonesDialog
            else:
                from milestones_ui import MilestonesDialog
            MilestonesDialog(self.store, self.assignment_id, self).exec_()
        except (ValueError, OSError) as error:
            QMessageBox.warning(self, "Checklist", str(error))

    def open_sources(self):
        """Append owner-entered reference text only if explicitly selected."""
        try:
            if __package__:
                from .source_library_ui import AssignmentSourcesDialog
            else:
                from source_library_ui import AssignmentSourcesDialog
            dialog = AssignmentSourcesDialog(self.store, self.assignment_id, self)
            if dialog.exec_() != QDialog.Accepted or not dialog.selected_reference:
                return
            reference = dialog.selected_reference
            editor = self.editors["references"]
            prior = editor.toPlainText()
            entries = [line.strip() for line in prior.splitlines() if line.strip()]
            if reference in entries:
                self.status.setText("Reference already appears in this assignment.")
                return
            editor.setPlainText(prior.rstrip() + ("\n" if prior.strip() else "") + reference)
            self.tabs.setCurrentWidget(editor)
            if not self.save():
                QMessageBox.warning(self, "References", "Reference copy could not be saved.")
        except (ValueError, OSError) as error:
            QMessageBox.warning(self, "Research sources", str(error))

    def use_webbie(self):
        try:
            directions = webbie_directions(self.values())
        except ValueError as error:
            QMessageBox.warning(self, "Webbie", str(error))
            return
        if not self.save():
            QMessageBox.warning(self, "Webbie", "Save your work before opening Webbie.")
            return
        try:
            if __package__:
                from .homework_ui import HomeworkDialog
                from .draft_storage import save_snapshot
            else:
                from homework_ui import HomeworkDialog
                from draft_storage import save_snapshot
            before = self.editors["draft"].toPlainText()
            assistant = HomeworkDialog(
                self, course=self.assignment["course"],
                assignment=self.assignment["title"],
                notes=self.store.get_notes(self.assignment["course_id"]),
                folder=self.folder,
            )
            assistant.directions.setPlainText(directions)
            assistant.materials.setPlainText(webbie_materials(self.values()))
            assistant.draft.setPlainText(before)
            assistant.exec_()
            candidate = assistant.draft.toPlainText()
            if candidate != before and candidate.strip():
                answer = QMessageBox.question(
                    self, "Copy Webbie draft",
                    "Copy the edited Webbie draft back to your assignment workspace? "
                    "A snapshot of your earlier draft will be kept.")
                if answer == QMessageBox.Yes:
                    if before.strip():
                        save_snapshot(self.folder, self.assignment["title"], before)
                    self.editors["draft"].setPlainText(candidate)
                    self.tabs.setCurrentWidget(self.editors["draft"])
                    if not self.save():
                        QMessageBox.warning(self, "Workspace save", "Could not save the Webbie draft.")
        except Exception as error:
            QMessageBox.warning(self, "Webbie", str(error))

    def export_apa(self):
        if not self.save():
            QMessageBox.warning(self, "APA export", "Save your assignment first.")
            return
        if not self.values()["draft"].strip():
            QMessageBox.warning(self, "APA export", "Write or import a draft first.")
            return
        try:
            if __package__:
                from .apa_preflight import analyze_apa_preflight
            else:
                from apa_preflight import analyze_apa_preflight
            scan = analyze_apa_preflight(
                draft=self.values()["draft"],
                references=self.values()["references"],
                instructions=self.values()["instructions"])
            if (scan["unmatched_pairs"] or scan["markers"] or not scan["reference_lines"]):
                answer = QMessageBox.question(
                    self, "Review references before APA export",
                    f"Offline source preflight found {len(scan['unmatched_pairs'])} "
                    f"possible citation mismatches, {scan['markers']} unresolved "
                    f"placeholders, and {scan['reference_lines']} reference lines.\n\n"
                    "You can continue making a DRAFT, but you must check actual "
                    "sources and APA format before submission. Export anyway?")
                if answer != QMessageBox.Yes:
                    return
        except ValueError as error:
            QMessageBox.warning(self, "APA export", str(error))
            return
        try:
            if __package__:
                from .paper_dialog import PaperDialog
                from .apa import create_paper
            else:
                from paper_dialog import PaperDialog
                from apa import create_paper
            form = PaperDialog(self, self.assignment["course"])
            form.fields["title"].setText(self.assignment["title"])
            form.body.setPlainText(self.values()["draft"])
            if form.exec_() != QDialog.Accepted:
                return
            values = form.values()
            if any(not str(values[key]).strip() for key in
                   ("title", "author", "institution", "course", "instructor", "due")):
                QMessageBox.warning(self, "APA export", "Complete the title page first.")
                return
            paragraphs = [p.strip() for p in self.values()["draft"].split("\n\n") if p.strip()]
            references = [p.strip() for p in self.values()["references"].splitlines()
                          if p.strip()]
            values["paragraphs"] = paragraphs
            values["references"] = references
            destination = self.folder / "Assignments"
            destination.mkdir(parents=True, exist_ok=True)
            path, _ = QFileDialog.getSaveFileName(
                self, "Export APA Word draft", str(destination / "assignment-draft.docx"),
                "Word (*.docx)")
            if not path:
                return
            if not path.lower().endswith(".docx"):
                path += ".docx"
            # Never replace an existing file via this dialog. Pick a new name.
            create_paper(path, **values, overwrite=False)
            self.status.setText("APA Word document saved: " + path +
                                ". Review APA details and verify your references.")
        except (ImportError, OSError, ValueError) as error:
            QMessageBox.warning(self, "APA export", str(error))

    def open_folder(self):
        from PyQt5.QtCore import QUrl
        from PyQt5.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.folder)))

    def accept(self):
        if self.save():
            super().accept()
        else:
            QMessageBox.warning(self, "Unsaved edits",
                                "Study could not save your edits. Close was cancelled.")

    def reject(self):
        self.accept()

    def closeEvent(self, event):
        if self.save():
            event.accept()
        else:
            event.ignore()
            QMessageBox.warning(self, "Unsaved edits",
                                "Study could not save your edits. Keep the workspace open.")
