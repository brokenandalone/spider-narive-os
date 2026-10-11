"""Native Qt smoke tests with no school login or model process."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PyQt5.QtWidgets import QApplication, QMessageBox
from study import store as store_module
from study.assignment_workspace_ui import AssignmentWorkspaceDialog
from study.flashcards_ui import FlashcardsDialog

app = QApplication.instance() or QApplication([])


class StudyQtWorkspaces(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.patches = [
            patch.object(store_module, "DATA_DIR", root / "settings"),
            patch.object(store_module, "DB_PATH", root / "settings/study.db"),
            patch.object(store_module, "DOCUMENTS_ROOT", root / "Documents"),
        ]
        for patcher in self.patches:
            patcher.start()
        self.store = store_module.StudyStore()
        self.course = self.store.add_course("SOC-112")
        self.folder = self.store.course_folder(self.course)
        self.store.add_assignment(self.course, "Final", "")
        self.assignment = self.store.assignments(self.course)[0]["id"]

    def tearDown(self):
        self.store.close()
        for patcher in reversed(self.patches):
            patcher.stop()
        self.temp.cleanup()

    def test_assignment_autosave_and_reload(self):
        dialog = AssignmentWorkspaceDialog(self.store, self.assignment, self.folder)
        dialog.editors["instructions"].setPlainText("Make an argument.")
        dialog.editors["draft"].setPlainText("My opening paragraph.")
        self.assertTrue(dialog.save())
        dialog.accept()
        again = AssignmentWorkspaceDialog(self.store, self.assignment, self.folder)
        self.assertEqual(again.editors["draft"].toPlainText(), "My opening paragraph.")
        again.accept()

    def test_empty_webbie_instructions_do_not_launch(self):
        dialog = AssignmentWorkspaceDialog(self.store, self.assignment, self.folder)
        with patch.object(QMessageBox, "warning") as warning:
            dialog.use_webbie()
            warning.assert_called_once()
        dialog.accept()

    def test_cards_reveal_and_score(self):
        self.store.add_flashcards(self.course, [("Prompt", "Response")])
        dialog = FlashcardsDialog(self.store, self.course, self.folder)
        self.assertIn("Answer hidden", dialog.answer.toPlainText())
        dialog.reveal()
        self.assertIn("Response", dialog.answer.toPlainText())
        dialog.practice()
        self.assertEqual(self.store.flashcards(self.course)[0]["incorrect"], 1)
        dialog.close()


if __name__ == "__main__":
    unittest.main()
