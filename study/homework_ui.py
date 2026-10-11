"""Webbie Homework Assistant for Study Bay.

All requested material is displayed before it is sent to a local Ollama model.
The user controls sample storage, revision, APA export, and later cloud uploads.
"""
from pathlib import Path
from PyQt5.QtCore import QThread, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QFileDialog, QPushButton, QTextEdit, QVBoxLayout,
)
try:
    from .homework import (load_style, save_style, clear_style, sample_from_file,
                           build_prompt, webbie_draft, MAX_CONTEXT, MAX_TASK)
    from .course_materials import read_course_document
    from .paper_dialog import PaperDialog
    from .apa import create_paper
    from .draft_storage import drafts_folder, save_snapshot, read_snapshot
    from .assignment_review import draft_checklist, build_review_prompt
except ImportError:
    from homework import (load_style, save_style, clear_style, sample_from_file,
                          build_prompt, webbie_draft, MAX_CONTEXT, MAX_TASK)
    from course_materials import read_course_document
    from paper_dialog import PaperDialog
    from apa import create_paper
    from draft_storage import drafts_folder, save_snapshot, read_snapshot
    from assignment_review import draft_checklist, build_review_prompt


class DraftWorker(QThread):
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


class HomeworkDialog(QDialog):
    def __init__(self, parent=None, *, course="", assignment="", notes="", folder=None):
        super().__init__(parent)
        self.setWindowTitle("Webbie | Homework Assistant")
        self.resize(850, 830)
        self.course_folder = Path(folder) if folder else Path.home() / "Documents"
        self.notes = str(notes)
        self.worker = None
        self.last_mode = "draft"
        self.last_exported_path = None
        self.review_source_draft = None
        self.review_is_stale = False
        self.last_saved_text = ""
        outer = QVBoxLayout(self)
        intro = QLabel("Webbie drafts and revises at your request using local AI. "
                       "You choose what course material and writing samples she sees. "
                       "Review accuracy, citations and school rules before submitting.")
        intro.setWordWrap(True)
        outer.addWidget(intro)
        form = QFormLayout()
        self.course = QLineEdit(course)
        self.assignment = QLineEdit(assignment)
        self.directions = QTextEdit()
        self.directions.setAcceptRichText(False)
        self.directions.setMinimumHeight(115)
        self.directions.setPlaceholderText(
            "Paste the assignment prompt, rubric, required length, and instructor directions.")
        self.materials = QTextEdit()
        self.materials.setAcceptRichText(False)
        self.materials.setMaximumHeight(95)
        self.materials.setPlaceholderText(
            "Optional excerpts or verified source notes that you choose to provide.")
        self.include_notes = QCheckBox("Include my selected course notes")
        self.include_notes.setChecked(False)
        self.style = QTextEdit()
        self.style.setAcceptRichText(False)
        self.style.setMaximumHeight(95)
        self.style.setPlaceholderText("Paste a paragraph from your own previous writing.")
        self.style.setPlainText(load_style())
        self.revision = QLineEdit()
        self.revision.setPlaceholderText("What should Webbie change in the next draft?")
        for label, widget in [
            ("Course", self.course), ("Assignment", self.assignment),
            ("Instructions / rubric", self.directions),
            ("Optional materials", self.materials),
            ("Course notes", self.include_notes),
            ("Your writing style sample", self.style),
            ("Revision instructions", self.revision),
        ]:
            form.addRow(label, widget)
        outer.addLayout(form)
        sample_buttons = QHBoxLayout()
        for label, action in [
            ("Import my writing", self.import_style),
            ("Save my style locally", self.save_style),
            ("Forget my saved style", self.delete_style),
        ]:
            button = QPushButton(label)
            button.clicked.connect(action)
            sample_buttons.addWidget(button)
        outer.addLayout(sample_buttons)
        materials_buttons = QHBoxLayout()
        for label, handler in [
            ("Import local course document", self.import_local_material),
            ("Use school OneDrive document", self.import_school_material),
        ]:
            button = QPushButton(label)
            button.clicked.connect(handler)
            materials_buttons.addWidget(button)
        outer.addLayout(materials_buttons)
        actions = QHBoxLayout()
        self.generate_buttons = []
        for label, mode in [
            ("Write draft", "draft"),
            ("Discussion post", "discussion"),
            ("Create outline", "outline"),
            ("Revise draft", "revise"),
        ]:
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, kind=mode: self.generate(kind))
            actions.addWidget(button)
            self.generate_buttons.append(button)
        outer.addLayout(actions)
        review_actions = QHBoxLayout()
        self.check_button = QPushButton("Check word count and sources")
        self.check_button.clicked.connect(self.check_draft)
        review_actions.addWidget(self.check_button)
        self.review_button = QPushButton("Ask Webbie to review rubric")
        self.review_button.clicked.connect(self.review_draft)
        review_actions.addWidget(self.review_button)
        outer.addLayout(review_actions)
        self.draft = QTextEdit()
        self.draft.setAcceptRichText(False)
        self.draft.textChanged.connect(self.invalidate_export)
        self.draft.textChanged.connect(self.note_draft_changed)
        self.draft.setPlaceholderText("Webbie's editable draft appears here. No automatic submission.")
        outer.addWidget(self.draft, 1)
        review_heading = QLabel("Rubric feedback and source checks (not an official grade)")
        review_heading.setWordWrap(True)
        outer.addWidget(review_heading)
        self.review_notes = QTextEdit()
        self.review_notes.setReadOnly(True)
        self.review_notes.setMaximumHeight(170)
        self.review_notes.setPlaceholderText(
            "Run an offline draft check or request Webbie's separate rubric feedback.")
        outer.addWidget(self.review_notes)
        footer = QHBoxLayout()
        save_button = QPushButton("Save local draft")
        save_button.clicked.connect(self.save_local_draft)
        footer.addWidget(save_button)
        restore_button = QPushButton("Restore a draft")
        restore_button.clicked.connect(self.restore_local_draft)
        footer.addWidget(restore_button)
        export = QPushButton("Export as APA Word paper")
        export.clicked.connect(self.export_apa)
        footer.addWidget(export)
        upload_button = QPushButton("Upload APA Word to school OneDrive")
        upload_button.clicked.connect(self.upload_apa_to_school)
        footer.addWidget(upload_button)
        close = QPushButton("Close")
        close.clicked.connect(self.close)
        footer.addWidget(close)
        outer.addLayout(footer)
        self.status = QLabel("Ready. Nothing is sent to Webbie until you request a draft.")
        self.status.setWordWrap(True)
        outer.addWidget(self.status)
        # A local file is created only after the draft changes. Never sync it
        # to personal or university cloud accounts.
        self.autosave_timer = QTimer(self)
        self.autosave_timer.setInterval(180000)
        self.autosave_timer.timeout.connect(self.autosave_draft)
        self.autosave_timer.start()

    def note_draft_changed(self):
        # Saving is deferred so typing stays responsive.
        if self.draft.toPlainText() != self.last_saved_text:
            self.status.setText("Draft has unsaved local edits. Autosave runs every 3 minutes.")

    def autosave_draft(self):
        current = self.draft.toPlainText()
        if not current.strip() or current == self.last_saved_text:
            return
        try:
            path = save_snapshot(self.course_folder, self.assignment.text(), current)
        except (OSError, ValueError) as error:
            self.status.setText("Autosave failed; existing drafts are safe. " + str(error))
            return
        self.last_saved_text = current
        self.status.setText("Draft autosaved locally: " + str(path))

    def invalidate_export(self):
        # A Word export is only eligible while the editable draft matches it.
        self.last_exported_path = None
        prior = self.review_source_draft
        if (prior is not None and self.draft.toPlainText() != prior
                and not self.review_is_stale):
            self.review_is_stale = True
            self.review_notes.setPlainText(
                "Your draft changed after this review was requested. "
                "Run the check or rubric review again for the current version.")

    def save_local_draft(self):
        try:
            path = save_snapshot(self.course_folder, self.assignment.text(),
                                 self.draft.toPlainText())
            self.last_saved_text = self.draft.toPlainText()
            self.status.setText("New local draft saved: " + str(path))
        except (ValueError, OSError) as error:
            QMessageBox.warning(self, "Save draft", str(error))

    def restore_local_draft(self):
        try:
            folder = drafts_folder(self.course_folder)
        except (ValueError, OSError) as error:
            QMessageBox.warning(self, "Restore draft", str(error))
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Restore a saved draft", str(folder), "Draft text (*.txt)")
        if not path:
            return
        try:
            restored = read_snapshot(path, self.course_folder)
            current = self.draft.toPlainText()
            if current.strip() and current != restored:
                save_snapshot(self.course_folder, self.assignment.text(), current)
            self.draft.setPlainText(restored)
            self.status.setText("Previous draft restored; current changes were preserved in a new snapshot.")
        except (ValueError, OSError, UnicodeError) as error:
            QMessageBox.warning(self, "Restore draft", str(error))

    def upload_apa_to_school(self):
        if self.last_exported_path is None:
            QMessageBox.warning(
                self, "School OneDrive",
                "First export your current homework draft as an APA Word file.")
            return
        try:
            if __package__:
                from .school_upload import SchoolDraftUploadDialog
            else:
                from school_upload import SchoolDraftUploadDialog
            dialog = SchoolDraftUploadDialog(
                self, self.course_folder, self.last_exported_path)
            dialog.exec_()
        except (ValueError, OSError, RuntimeError, ImportError) as error:
            QMessageBox.warning(self, "School OneDrive", str(error))

    def import_style(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select your own writing sample", str(self.course_folder),
            "Writing samples (*.txt *.md *.docx)")
        if not path:
            return
        try:
            self.style.setPlainText(sample_from_file(path))
            self.status.setText("Sample loaded for this session. Save it only if you want Webbie to remember it.")
        except (OSError, ValueError, ImportError) as error:
            QMessageBox.warning(self, "Writing sample", str(error))

    def add_selected_material(self, kind, text):
        """The selected source is visible and editable before any model request."""
        if kind == "style":
            # Use as style only. Never silently persist a school document.
            self.style.setPlainText(text[:12000])
            self.status.setText("Selected sample loaded for style only. Save it separately if desired.")
            return
        target = self.directions if kind == "instructions" else self.materials
        current = target.toPlainText().strip()
        separator = "\n\n" if current else ""
        limit = MAX_TASK if kind == "instructions" else MAX_CONTEXT
        if len(current) + len(separator) + len(text) > limit:
            QMessageBox.warning(
                self, "Document import",
                "This document exceeds the context limit when combined "
                "with the existing text. Shorten or replace the earlier excerpt first.")
            return
        target.setPlainText(current + separator + text)
        self.status.setText("Selected source added for review. Webbie has not been contacted.")

    def import_local_material(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose a local school document", str(self.course_folder),
            "School documents (*.txt *.md *.docx *.pdf)")
        if not path:
            return
        try:
            body = read_course_document(path)
        except (ValueError, OSError, RuntimeError, ImportError,
                UnicodeError, TimeoutError) as error:
            QMessageBox.warning(self, "Course document", str(error))
            return
        self.add_selected_material("materials",
            "LOCAL COURSE FILE: " + Path(path).name +
            "\nUser-selected text, not a verified bibliographic citation:\n" + body)

    def import_school_material(self):
        try:
            if __package__:
                from .school_material_picker import SchoolMaterialPicker
            else:
                from school_material_picker import SchoolMaterialPicker
            picker = SchoolMaterialPicker(self, self.course_folder)
            if picker.exec_() == QDialog.Accepted and picker.selected_material:
                kind, text = picker.selected_material
                self.add_selected_material(kind, text)
        except (ValueError, OSError, RuntimeError, ImportError) as error:
            QMessageBox.warning(self, "School OneDrive", str(error))

    def save_style(self):
        try:
            save_style(self.style.toPlainText())
            self.status.setText("Your writing style sample is stored privately on this PC.")
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Writing style", str(error))

    def delete_style(self):
        clear_style()
        self.style.clear()
        self.status.setText("Saved style sample cleared. Webbie can still draft normally.")

    def selected_materials(self):
        materials = self.materials.toPlainText().strip()
        if self.include_notes.isChecked() and self.notes.strip():
            materials += "\n\nSELECTED COURSE NOTES:\n" + self.notes[:10000]
        return materials

    def check_draft(self):
        """Deterministic local checks; no network or language-model call."""
        try:
            report = draft_checklist(
                self.directions.toPlainText(), self.draft.toPlainText(),
                materials=self.selected_materials())
        except ValueError as error:
            QMessageBox.warning(self, "Homework review", str(error))
            return
        self.review_source_draft = self.draft.toPlainText()
        self.review_is_stale = False
        self.review_notes.setPlainText(report)
        self.status.setText("Local preflight complete. No grade or source verification is implied.")

    def review_draft(self):
        """Separate Webbie feedback; never replace the user's draft."""
        if self.worker is not None:
            self.status.setText("Webbie is already processing a homework request.")
            return
        try:
            checklist = draft_checklist(
                self.directions.toPlainText(), self.draft.toPlainText(),
                materials=self.selected_materials())
            prompt = build_review_prompt(
                course=self.course.text(), assignment=self.assignment.text(),
                instructions=self.directions.toPlainText(),
                draft=self.draft.toPlainText(),
                materials=self.selected_materials(),
                sample=self.style.toPlainText())
        except ValueError as error:
            QMessageBox.warning(self, "Homework review", str(error))
            return
        self.review_source_draft = self.draft.toPlainText()
        self.review_is_stale = False
        self.review_notes.setPlainText(checklist + "\n\nWebbie is reviewing the selected rubric...")
        self.worker = DraftWorker(prompt, self)
        self.worker.ready.connect(lambda response: self.review_ready(checklist, response))
        self.worker.failed.connect(self.review_failed)
        self.worker.finished.connect(self.release_worker)
        for button in self.generate_buttons:
            button.setEnabled(False)
        self.check_button.setEnabled(False)
        self.review_button.setEnabled(False)
        self.status.setText("Webbie is reviewing locally. Your draft will not be changed.")
        self.worker.start()

    def review_ready(self, checklist, response):
        if self.review_is_stale:
            self.review_notes.setPlainText(
                "Webbie completed feedback on an earlier version. "
                "The current draft changed while review was running. "
                "Request a new review before using this feedback.\n\n" +
                checklist + "\n\nREVIEW OF THE EARLIER VERSION:\n" + response)
            self.status.setText("Review is outdated because the draft changed.")
            return
        self.review_notes.setPlainText(checklist + "\n\nWEBBIE'S RUBRIC REVIEW:\n" + response)
        self.status.setText("Review ready. Feedback is advisory; verify the rubric and references.")

    def review_failed(self, error):
        self.status.setText("Webbie could not complete rubric review: " + error)
        # Keep the deterministic checklist available if the local model fails.

    def generate(self, mode):
        if self.worker is not None:
            self.status.setText("Webbie is already drafting.")
            return
        materials = self.selected_materials()
        try:
            prompt = build_prompt(
                course=self.course.text(), assignment=self.assignment.text(),
                instructions=self.directions.toPlainText(), materials=materials,
                sample=self.style.toPlainText(), existing_draft=self.draft.toPlainText(),
                revision=self.revision.text(), mode=mode)
        except ValueError as error:
            QMessageBox.warning(self, "Assignment details", str(error))
            return
        self.last_mode = mode
        self.worker = DraftWorker(prompt, self)
        self.worker.ready.connect(self.draft_ready)
        self.worker.failed.connect(self.draft_failed)
        self.worker.finished.connect(self.release_worker)
        for button in self.generate_buttons:
            button.setEnabled(False)
        self.check_button.setEnabled(False)
        self.review_button.setEnabled(False)
        self.status.setText("Webbie is writing locally. Existing work remains editable after completion.")
        self.worker.start()

    def release_worker(self):
        # Never destroy a QThread before its finished signal fires.
        if self.worker is not None:
            self.worker.deleteLater()
            self.worker = None
        for button in self.generate_buttons:
            button.setEnabled(True)
        self.check_button.setEnabled(True)
        self.review_button.setEnabled(True)

    def draft_ready(self, text):
        if text.strip():
            previous = self.draft.toPlainText()
            if previous.strip() and previous != text:
                try:
                    save_snapshot(self.course_folder, self.assignment.text(), previous)
                except (ValueError, OSError) as error:
                    self.status.setText("Existing work could not be backed up: " + str(error) +
                                        ". New text was not applied.")
                    return
            self.draft.setPlainText(text)
            self.status.setText(
                "Draft ready. Prior version backed up when applicable. "
                "Review facts, citations and your assignment requirements.")
        else:
            self.status.setText("Webbie returned no draft.")

    def draft_failed(self, error):
        self.status.setText("Webbie could not draft: " + error)

    def export_apa(self):
        if not self.draft.toPlainText().strip():
            QMessageBox.warning(self, "APA export", "Generate or paste an editable draft first.")
            return
        form = PaperDialog(self, self.course.text())
        form.fields["title"].setText(self.assignment.text())
        form.body.setPlainText(self.draft.toPlainText())
        if form.exec_() != QDialog.Accepted:
            return
        values = form.values()
        if any(not values[key] for key in
               ("title", "author", "institution", "course", "instructor", "due")):
            QMessageBox.warning(self, "APA export", "Complete all title-page fields.")
            return
        destination = self.course_folder / "Assignments"
        destination.mkdir(parents=True, exist_ok=True)
        file, _ = QFileDialog.getSaveFileName(self, "Save homework draft",
                                              str(destination / "homework-draft.docx"),
                                              "Word documents (*.docx)")
        if not file:
            return
        if not file.lower().endswith(".docx"):
            file += ".docx"
        try:
            create_paper(file, **values, overwrite=False)
        except (OSError, ValueError, ImportError, FileExistsError) as error:
            QMessageBox.warning(self, "APA export", str(error))
            return
        self.last_exported_path = Path(file)
        self.status.setText("APA draft saved locally: " + file + ". School upload requires a separate action.")

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            self.status.setText("Webbie is finishing this request. You can close after her response.")
            event.ignore()
            return
        current = self.draft.toPlainText()
        if current.strip() and current != self.last_saved_text:
            try:
                save_snapshot(self.course_folder, self.assignment.text(), current)
                self.last_saved_text = current
            except (OSError, ValueError) as error:
                QMessageBox.warning(
                    self, "Homework not saved",
                    "Local draft backup failed. The editor will stay open "
                    "so you can copy your work or free disk space.\n" + str(error))
                event.ignore()
                return
        self.autosave_timer.stop()
        super().closeEvent(event)
