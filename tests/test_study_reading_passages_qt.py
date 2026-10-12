"""Study passage browsing and explicit model handoff, no real AI calls."""
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
from study.study_coach_ui import StudyCoachDialog, CoachWorker

app = QApplication.instance() or QApplication([])


class StudyPassageQt(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.patchers = [
            patch.object(store_module, "DATA_DIR", root / "settings"),
            patch.object(store_module, "DB_PATH", root / "settings/study.db"),
            patch.object(store_module, "DOCUMENTS_ROOT", root / "files"),
        ]
        for p in self.patchers:
            p.start()
        self.store = store_module.StudyStore()
        self.course = self.store.add_course("SOC-112")
        doc = root / "reading.txt"
        doc.write_text(
            "Social movements can contribute to social change. " * 400 +
            "Later reading passage: education and stratification.",
            encoding="utf-8")
        import_course_reading(self.store, self.course, doc)

    def tearDown(self):
        self.store.close()
        for p in reversed(self.patchers):
            p.stop()
        self.temp.cleanup()

    def test_search_selects_specific_passage_not_whole_document(self):
        picker = ReadingLibraryDialog(self.store, self.course, pick=True)
        picker.search.setText("education stratification")
        picker.search_readings()
        self.assertGreater(picker.table.rowCount(), 0)
        picker.table.selectRow(0)
        self.assertIsNotNone(picker.selected_passage())
        with patch.object(QMessageBox, "question", return_value=QMessageBox.No):
            picker.use_selected()
        self.assertIsNone(picker.selected_excerpt)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
            picker.use_selected()
        self.assertIn("LOCAL COURSE READING PASSAGE",
                      picker.selected_excerpt)
        self.assertIn("stratification", picker.selected_excerpt.lower())

    def test_browse_explicit_passage_count(self):
        picker = ReadingLibraryDialog(self.store, self.course)
        picker.table.selectRow(0)
        picker.browse_passages()
        self.assertGreater(picker.table.rowCount(), 2)
        picker.table.selectRow(2)
        self.assertIn("passage: 3", picker.preview.toPlainText().lower())
        picker.close()

    def test_passage_reaches_editable_coach_only_after_selection(self):
        dialog = StudyCoachDialog(
            course="SOC-112", topic="Social movement",
            store=self.store, course_id=self.course)
        def fake_picker(picker):
            picker.selected_excerpt = "OWNER-SELECTED COURSE READING PASSAGE\nSelected text"
            return QDialog.Accepted
        with patch.object(ReadingLibraryDialog, "exec_", fake_picker), \
             patch.object(CoachWorker, "start") as start:
            dialog.import_reading()
            start.assert_not_called()
            self.assertIn("Selected text", dialog.materials.toPlainText())
        dialog.close()


if __name__ == "__main__":
    unittest.main()
