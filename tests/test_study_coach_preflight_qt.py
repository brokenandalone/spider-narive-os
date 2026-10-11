"""Native Qt controls are opt-in; use no Ollama or SNHU services in CI."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PyQt5.QtWidgets import QApplication, QMessageBox, QDialog
from study import store as store_module
from study.study_coach_ui import CoachWorker, StudyCoachDialog
from study.assignment_workspace_ui import AssignmentWorkspaceDialog
from study.paper_dialog import PaperDialog

app = QApplication.instance() or QApplication([])


class CoachQtTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.patchers = [
            patch.object(store_module, "DATA_DIR", root / "config"),
            patch.object(store_module, "DB_PATH", root / "config/study.db"),
            patch.object(store_module, "DOCUMENTS_ROOT", root / "Documents"),
        ]
        for patcher in self.patchers:
            patcher.start()
        self.store = store_module.StudyStore()
        self.course_id = self.store.add_course("PSY-328")
        self.store.add_assignment(self.course_id, "Journal", "2026-10-18")
        self.assignment_id = self.store.assignments(self.course_id)[0]["id"]

    def tearDown(self):
        self.store.close()
        for patcher in reversed(self.patchers):
            patcher.stop()
        self.tmp.cleanup()

    def test_study_coach_starts_only_with_explicit_button(self):
        with patch.object(CoachWorker, "start") as start:
            dialog = StudyCoachDialog(
                course="PSY-328", topic="Personality", materials="Owner notes",
                notes="Course notes", store=self.store, course_id=self.course_id)
            self.assertFalse(dialog.notes_checkbox.isChecked())
            self.assertIsNone(dialog.worker)
            start.assert_not_called()
            dialog.ask()
            start.assert_called_once()
            self.assertFalse(dialog.ask_button.isEnabled())
            dialog.answer_ready("Webbie local educational response")
            self.assertIn("Webbie local", dialog.response.toPlainText())
            dialog.release_worker()
            dialog.close()
        self.assertEqual(len(self.store.flashcards(self.course_id)), 0)

    def test_card_import_requires_user_confirmation(self):
        dialog = StudyCoachDialog(
            course="PSY-328", topic="Personality", materials="Owner notes",
            store=self.store, course_id=self.course_id)
        dialog.response.setPlainText("Q: What is personality?\nA: A set of patterns.")
        with patch.object(QMessageBox, "question", return_value=QMessageBox.No):
            dialog.save_flashcards()
        self.assertEqual(len(self.store.flashcards(self.course_id)), 0)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
            dialog.save_flashcards()
        self.assertEqual(len(self.store.flashcards(self.course_id)), 1)
        dialog.close()

    def test_assignment_apa_preflight_is_read_only(self):
        dialog = AssignmentWorkspaceDialog(
            self.store, self.assignment_id,
            self.store.course_folder(self.course_id))
        dialog.editors["draft"].setPlainText("A statement (Smith, 2020).")
        dialog.editors["references"].setPlainText("Smith, J. (2020). Owner source.")
        with patch.object(QDialog, "exec_", return_value=QDialog.Accepted):
            dialog.apa_preflight()
        self.assertEqual(dialog.editors["draft"].toPlainText(),
                         "A statement (Smith, 2020).")
        dialog.close()

    def test_export_requires_confirmation_for_unmatched_source(self):
        dialog = AssignmentWorkspaceDialog(
            self.store, self.assignment_id,
            self.store.course_folder(self.course_id))
        dialog.editors["draft"].setPlainText("Unverified (Smith, 2020).")
        dialog.editors["references"].setPlainText("Jones, K. (2019). Other source.")
        with patch.object(QMessageBox, "question", return_value=QMessageBox.No) as ask, \
             patch.object(PaperDialog, "exec_", return_value=QDialog.Accepted) as paper:
            dialog.export_apa()
            ask.assert_called_once()
            paper.assert_not_called()
        dialog.close()

    def test_assignment_tutor_sees_context_before_asking(self):
        dialog = AssignmentWorkspaceDialog(
            self.store, self.assignment_id,
            self.store.course_folder(self.course_id))
        dialog.editors["instructions"].setPlainText("Evaluate temperament.")
        dialog.editors["research"].setPlainText("Verified textbook note here.")
        captured = {}
        def fake_exec(coach):
            captured["material"] = coach.materials.toPlainText()
            captured["notes_checked"] = coach.notes_checkbox.isChecked()
            return QDialog.Rejected
        with patch.object(StudyCoachDialog, "exec_", fake_exec):
            dialog.study_with_webbie()
        self.assertIn("Evaluate temperament.", captured["material"])
        self.assertIn("Verified textbook note here.", captured["material"])
        self.assertFalse(captured["notes_checked"])
        dialog.close()


if __name__ == "__main__":
    unittest.main()
