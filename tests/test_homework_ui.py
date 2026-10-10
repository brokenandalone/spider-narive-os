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
