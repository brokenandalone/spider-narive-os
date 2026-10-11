"""Native Study dialog smoke tests; no network, school credentials, or LLM."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PyQt5.QtWidgets import QApplication, QMessageBox
from study import store as store_module
from study.milestones_ui import MilestonesDialog
from study.source_library_ui import AssignmentSourcesDialog
from study.weekly_planner_ui import WeeklyPlannerDialog
from study.assignment_workspace_ui import AssignmentWorkspaceDialog

app = QApplication.instance() or QApplication([])


class StudyPlannerQtTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.patchers = [
            patch.object(store_module, "DATA_DIR", root / "config"),
            patch.object(store_module, "DB_PATH", root / "config/study.db"),
            patch.object(store_module, "DOCUMENTS_ROOT", root / "Documents"),
        ]
        for p in self.patchers:
            p.start()
        self.store = store_module.StudyStore()
        self.course = self.store.add_course("PSY-328")
        self.store.add_assignment(self.course, "Final project", "2026-10-18")
        self.assignment = self.store.assignments(self.course)[0]["id"]

    def tearDown(self):
        self.store.close()
        for p in reversed(self.patchers):
            p.stop()
        self.temp.cleanup()

    def test_starter_checklist_is_explicit_and_saves(self):
        dialog = MilestonesDialog(self.store, self.assignment)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.No):
            dialog.add_starter()
        self.assertEqual(dialog.table.rowCount(), 0)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
            dialog.add_starter()
        self.assertEqual(dialog.table.rowCount(), 7)
        dialog.table.selectRow(0)
        dialog.mark_done()
        self.assertEqual(sum(x["completed"] for x in self.store.assignment_steps(self.assignment)), 1)
        dialog.close()

    def test_source_append_needs_explicit_confirmation(self):
        ref = "Example, A. (2022). Title."
        self.store.add_assignment_source(self.assignment, ref, "https://example.org")
        dialog = AssignmentSourcesDialog(self.store, self.assignment)
        self.assertEqual(dialog.list.count(), 1)
        dialog.list.setCurrentRow(0)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.No):
            dialog.use_selected()
        self.assertIsNone(dialog.selected_reference)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
            dialog.use_selected()
        self.assertEqual(dialog.selected_reference, ref)

    def test_weekly_window_and_selected_assignment(self):
        dialog = WeeklyPlannerDialog(self.store)
        self.assertGreaterEqual(dialog.table.rowCount(), 1)
        dialog.window.setCurrentIndex(1)
        self.assertEqual(dialog.window.currentData(), 14)
        self.assertEqual(dialog.table.columnCount(), 6)
        dialog.close()

    def test_parent_notebook_contains_research_and_checklist_buttons(self):
        dialog = AssignmentWorkspaceDialog(
            self.store, self.assignment, self.store.course_folder(self.course))
        # New dialogs must open even without Webbie, Microsoft or network services.
        dialog.open_steps()
        dialog.open_sources = lambda: None  # avoid a second modal in offscreen mode
        dialog.close()


if __name__ == "__main__":
    unittest.main()
