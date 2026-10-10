"""Qt smoke checks for the requested Webbie academic writing controls."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from PyQt5.QtWidgets import QApplication

from study.homework_ui import HomeworkDialog

app = QApplication.instance() or QApplication([])


class HomeworkUiTests(unittest.TestCase):
    def test_course_context_and_opt_in_notes(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("study.homework_ui.load_style", return_value=""):
                dialog = HomeworkDialog(
                    course="PSY-328", assignment="Module 6",
                    notes="Private course notes", folder=Path(folder))
            self.assertEqual(dialog.course.text(), "PSY-328")
            self.assertEqual(dialog.assignment.text(), "Module 6")
            self.assertFalse(dialog.include_notes.isChecked())
            dialog.directions.setPlainText("Write a discussion response.")
            with patch("study.homework_ui.DraftWorker") as worker:
                dialog.generate("discussion")
                prompt = worker.call_args.args[0]
                self.assertNotIn("Private course notes", prompt)
                self.assertIn("PSY-328", prompt)
            dialog.worker = None
            dialog.include_notes.setChecked(True)
            with patch("study.homework_ui.DraftWorker") as worker:
                dialog.generate("draft")
                prompt = worker.call_args.args[0]
                self.assertIn("Private course notes", prompt)
            dialog.worker = None
            dialog.close()

    def test_empty_rubric_does_not_contact_model(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("study.homework_ui.load_style", return_value=""):
                dialog = HomeworkDialog(folder=Path(folder))
            with patch("study.homework_ui.DraftWorker") as worker, \
                 patch("study.homework_ui.QMessageBox.warning") as warning:
                dialog.generate("draft")
                worker.assert_not_called()
                warning.assert_called_once()
            dialog.close()

    def test_imported_material_is_visible_and_editable_before_model_use(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("study.homework_ui.load_style", return_value=""):
                dialog = HomeworkDialog(folder=Path(folder))
            dialog.add_selected_material("instructions",
                                         "SCHOOL ONEDRIVE FILE: rubric.txt\nWrite 300 words.")
            dialog.add_selected_material("materials",
                                         "SCHOOL ONEDRIVE FILE: reading.txt\nCourse evidence.")
            dialog.add_selected_material("style", "My previous discussion post.")
            self.assertIn("Write 300 words.", dialog.directions.toPlainText())
            self.assertIn("Course evidence.", dialog.materials.toPlainText())
            self.assertEqual(dialog.style.toPlainText(), "My previous discussion post.")
            dialog.directions.setPlainText("Revised instructor directions.")
            self.assertEqual(dialog.directions.toPlainText(), "Revised instructor directions.")
            dialog.close()

    def test_school_material_picker_requires_explicit_accept(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("study.homework_ui.load_style", return_value=""):
                dialog = HomeworkDialog(folder=Path(folder))
            with patch("study.school_material_picker.SchoolMaterialPicker") as picker_type:
                picker = picker_type.return_value
                picker.exec_.return_value = 0
                picker.selected_material = ("materials", "Private document")
                dialog.import_school_material()
                self.assertNotIn("Private document", dialog.materials.toPlainText())
                picker.exec_.return_value = 1
                dialog.import_school_material()
                self.assertIn("Private document", dialog.materials.toPlainText())
            dialog.close()

    def test_rewriting_a_draft_saves_old_text_before_replacement(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("study.homework_ui.load_style", return_value=""):
                dialog = HomeworkDialog(assignment="Reflection", folder=Path(folder))
            dialog.draft.setPlainText("My original words.")
            dialog.draft_ready("Webbie's revised version.")
            self.assertEqual(dialog.draft.toPlainText(), "Webbie's revised version.")
            saved = list((Path(folder) / "Assignments" / "Drafts").glob("*.txt"))
            self.assertEqual(len(saved), 1)
            self.assertEqual(saved[0].read_text(), "My original words.")
            dialog.close()

    def test_failed_backup_never_discards_existing_draft(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("study.homework_ui.load_style", return_value=""):
                dialog = HomeworkDialog(folder=Path(folder))
            dialog.draft.setPlainText("Important draft that must survive.")
            with patch("study.homework_ui.save_snapshot", side_effect=OSError("disk full")):
                dialog.draft_ready("New generated work.")
            self.assertEqual(dialog.draft.toPlainText(), "Important draft that must survive.")
            self.assertIn("could not be backed up", dialog.status.text())
            dialog.close()

    def test_school_upload_requires_fresh_export_and_never_runs_on_edit(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("study.homework_ui.load_style", return_value=""):
                dialog = HomeworkDialog(folder=Path(folder))
            with patch("study.homework_ui.QMessageBox.warning") as warning:
                dialog.upload_apa_to_school()
                warning.assert_called_once()
            dialog.last_exported_path = Path(folder) / "paper.docx"
            dialog.draft.setPlainText("Draft changed after export.")
            self.assertIsNone(dialog.last_exported_path)
            with patch("study.school_upload.SchoolDraftUploadDialog") as uploader:
                dialog.upload_apa_to_school()
                uploader.assert_not_called()
                dialog.last_exported_path = Path(folder) / "paper.docx"
                dialog.upload_apa_to_school()
                uploader.assert_called_once()
            dialog.close()

    def test_draft_is_editable_before_export(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("study.homework_ui.load_style", return_value=""):
                dialog = HomeworkDialog(folder=Path(folder))
            dialog.draft.setPlainText("Student-editable draft.")
            self.assertFalse(dialog.draft.isReadOnly())
            self.assertEqual(dialog.draft.toPlainText(), "Student-editable draft.")
            dialog.close()


if __name__ == "__main__":
    unittest.main()
