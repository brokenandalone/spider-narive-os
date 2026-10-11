"""Native Qt smoke: select a reading without automatically sending it to Webbie."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PyQt5.QtWidgets import QApplication, QMessageBox, QDialog
from study import store as store_module
from study.reading_library import import_course_reading
from study.reading_library_ui import ReadingLibraryDialog
from study.study_coach_ui import CoachWorker, StudyCoachDialog
from study.homework_ui import HomeworkDialog
from study.assignment_workspace_ui import AssignmentWorkspaceDialog

app = QApplication.instance() or QApplication([])


class ReadingQtTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.patchers = [
            patch.object(store_module, "DATA_DIR", root / "data"),
            patch.object(store_module, "DB_PATH", root / "data/study.db"),
            patch.object(store_module, "DOCUMENTS_ROOT", root / "docs"),
        ]
        for p in self.patchers:
            p.start()
        self.store = store_module.StudyStore()
        self.course = self.store.add_course("PSY-328")
        self.store.add_assignment(self.course, "Essay", "2026-10-18")
        self.assignment = self.store.assignments(self.course)[0]["id"]
        self.source = root / "excerpt.txt"
        self.source.write_text("Ethics, culture, and psychological differences.",
                               encoding="utf-8")
        import_course_reading(self.store, self.course, self.source)

    def tearDown(self):
        self.store.close()
        for p in reversed(self.patchers):
            p.stop()
        self.tmp.cleanup()

    def test_owner_controls_excerpt_transfer(self):
        picker = ReadingLibraryDialog(self.store, self.course, pick=True)
        self.assertEqual(picker.table.rowCount(), 1)
        picker.table.selectRow(0)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.No):
            picker.use_selected()
        self.assertIsNone(picker.selected_excerpt)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
            picker.use_selected()
        self.assertIn("OWNER-SELECTED LOCAL COURSE READING", picker.selected_excerpt)

    def test_study_coach_has_picker_but_does_not_ask_ai(self):
        dialog = StudyCoachDialog(
            course="PSY-328", topic="Cultural differences",
            store=self.store, course_id=self.course)
        with patch.object(CoachWorker, "start") as start, \
             patch.object(ReadingLibraryDialog, "exec_", return_value=QDialog.Rejected):
            dialog.import_reading()
            start.assert_not_called()
            self.assertFalse(dialog.materials.toPlainText().strip())
        dialog.close()

    def test_homework_picker_works_with_no_existing_materials(self):
        dialog = HomeworkDialog(
            course="PSY-328", assignment="Essay",
            folder=self.store.course_folder(self.course),
            store=self.store, course_id=self.course)
        def select(picker):
            picker.selected_excerpt = "Chosen course excerpt from owner reading"
            return QDialog.Accepted
        with patch.object(ReadingLibraryDialog, "exec_", select):
            dialog.import_course_reading()
        self.assertIn("Chosen course excerpt", dialog.materials.toPlainText())
        self.assertIsNone(dialog.worker)
        dialog.close()

    def test_assignment_workspace_hands_course_context_to_homework(self):
        from study import homework_ui
        work = AssignmentWorkspaceDialog(
            self.store, self.assignment,
            self.store.course_folder(self.course))
        work.editors["instructions"].setPlainText("Review psychological theory")
        result = {}
        def inspect(dlg):
            result["course_id"] = dlg.course_id
            result["store"] = dlg.store
            return QDialog.Rejected
        with patch.object(homework_ui.HomeworkDialog, "exec_", inspect):
            work.use_webbie()
        self.assertEqual(result["course_id"], self.course)
        self.assertIs(result["store"], self.store)
        work.close()


if __name__ == "__main__":
    unittest.main()
