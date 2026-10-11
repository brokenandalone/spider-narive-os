"""Native Study progress dialog smoke test without school data."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PyQt5.QtWidgets import QApplication
from study import store as store_module
from study.study_progress_ui import StudyProgressDialog

app = QApplication.instance() or QApplication([])


class StudyProgressQATests(unittest.TestCase):
    def test_grade_and_session_panels_show_saved_local_values(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch.object(store_module, "DATA_DIR", root / "data"), \
                 patch.object(store_module, "DB_PATH", root / "data/study.db"), \
                 patch.object(store_module, "DOCUMENTS_ROOT", root / "Study"):
                store = store_module.StudyStore()
                try:
                    course = store.add_course("PSY-328")
                    store.add_assignment(course, "Milestone", "2026-10-18")
                    assignment = store.assignments(course)[0]["id"]
                    store.set_assignment_score(assignment, 9, 10)
                    store.add_study_session(course, "Personality theories", 35)
                    dialog = StudyProgressDialog(store, course)
                    self.assertIn("90.0%", dialog.grade_summary.text())
                    self.assertIn("35 minutes", dialog.time_summary.text())
                    self.assertEqual(dialog.grades.rowCount(), 1)
                    self.assertEqual(dialog.sessions.rowCount(), 1)
                    dialog.close()
                finally:
                    store.close()


if __name__ == "__main__":
    unittest.main()
