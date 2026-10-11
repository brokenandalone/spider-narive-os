"""Manual grade and session tracker regression tests. No school integration."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from study import store as store_module
from study.study_progress import (valid_score, grade_summary,
                                  valid_study_session, session_summary)


class ProgressTrackerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.patchers = [
            patch.object(store_module, "DATA_DIR", root / "settings"),
            patch.object(store_module, "DB_PATH", root / "settings/study.db"),
            patch.object(store_module, "DOCUMENTS_ROOT", root / "Documents"),
        ]
        for p in self.patchers:
            p.start()
        self.store = store_module.StudyStore()
        self.course = self.store.add_course("SOC-112")
        self.other_course = self.store.add_course("PSY-328")
        self.store.save_notes(self.course, "Original course notes must survive.")
        self.store.add_assignment(self.course, "Journal", "2026-10-18")
        self.store.add_assignment(self.course, "Discussion", "2026-10-20")
        self.store.add_assignment(self.other_course, "Other assignment")
        self.assignment = self.store.assignments(self.course)[0]["id"]

    def tearDown(self):
        self.store.close()
        for p in reversed(self.patchers):
            p.stop()
        self.temp.cleanup()

    def test_manual_percent_is_not_a_gpa_and_ungraded_excluded(self):
        self.store.set_assignment_score(self.assignment, 18, 20)
        records = self.store.assignment_scores(self.course)
        totals = grade_summary(records)
        self.assertEqual(totals["graded"], 1)
        self.assertEqual(totals["percentage"], "90.0")
        self.assertEqual(totals["earned"], "18.00")
        self.assertEqual(totals["possible"], "20.00")
        self.assertEqual(grade_summary(self.store.assignment_scores(self.other_course))["percentage"], None)

    def test_bad_or_zero_possible_scores_do_not_overwrite(self):
        self.store.set_assignment_score(self.assignment, 8, 10)
        for earned, possible in [(-1, 10), (8, 0), ("bogus", 10),
                                 (100, 1), ("NaN", 100), ("0.001", "0.001")]:
            with self.subTest(score=(earned, possible)), self.assertRaises(ValueError):
                self.store.set_assignment_score(self.assignment, earned, possible)
        saved = self.store.assignment_scores(self.course)
        scored = next(r for r in saved if r["id"] == self.assignment)
        self.assertEqual((scored["earned"], scored["possible"]), ("8.00", "10.00"))

    def test_manual_grade_clear_and_existing_course_notes_preserved(self):
        self.store.set_assignment_score(self.assignment, 8, 10)
        self.store.clear_assignment_score(self.assignment)
        self.assertEqual(grade_summary(self.store.assignment_scores(self.course))["graded"], 0)
        self.assertEqual(self.store.get_notes(self.course), "Original course notes must survive.")

    def test_session_journal_separates_courses(self):
        first = self.store.add_study_session(self.course, "Chapter 7", 45)
        self.store.add_study_session(self.course, "Exam practice", 30)
        self.store.add_study_session(self.other_course, "Psychology quiz", 60)
        sessions = self.store.study_sessions(self.course)
        self.assertEqual(session_summary(sessions)["minutes"], 75)
        self.assertEqual(len(self.store.study_sessions(self.other_course)), 1)
        self.store.delete_study_session(self.course, first)
        self.assertEqual(session_summary(self.store.study_sessions(self.course))["minutes"], 30)
        self.assertEqual(self.store.get_notes(self.course), "Original course notes must survive.")

    def test_reject_unrealistic_or_fake_sessions(self):
        for topic, minutes in [("", 20), ("Valid", -2), ("Valid", 650),
                               ("Bad", True), ("Too big" * 50, 5)]:
            with self.subTest(topic=topic, minutes=minutes), self.assertRaises(ValueError):
                valid_study_session(topic, minutes)
        self.assertEqual(valid_study_session("Read an article", 25), ("Read an article", 25))

    def test_local_grade_and_study_time_survive_restart(self):
        self.store.set_assignment_score(self.assignment, "45.25", "50")
        self.store.add_study_session(self.course, "Fieldwork reading", 50)
        self.store.close()
        self.store = store_module.StudyStore()
        rows = self.store.assignment_scores(self.course)
        self.assertEqual(grade_summary(rows)["percentage"], "90.5")
        self.assertEqual(session_summary(self.store.study_sessions(self.course))["minutes"], 50)


if __name__ == "__main__":
    unittest.main()
