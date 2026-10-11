"""Offline regression tests for Study assignment notebooks and flashcards."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from study import store as store_module
from study.assignment_workflow import (WORK_FIELDS, normalized_fields,
                                       readiness_report, webbie_directions,
                                       webbie_materials)
from study.flashcards import parse_flashcards_csv, next_card


def empty_workspace():
    return {field: "" for field in WORK_FIELDS}


class StudyWorkspaceTests(unittest.TestCase):
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
        self.root = root
        self.store = store_module.StudyStore()
        self.course = self.store.add_course("PSY-328")
        self.store.add_assignment(self.course, "Final paper", "2026-10-18")
        self.assignment = self.store.assignments(self.course)[0]["id"]
        self.store.save_notes(self.course, "Important existing course notes.")

    def tearDown(self):
        self.store.close()
        for patcher in reversed(self.patches):
            patcher.stop()
        self.temp.cleanup()

    def test_persists_notebook_and_preserves_notes(self):
        values = empty_workspace()
        values.update(instructions="Explain personality theory.",
                      rubric="Compare theories.",
                      draft="My first editable draft.",
                      references="Example only.")
        self.store.save_assignment_workspace(self.assignment, values)
        self.store.close()
        self.store = store_module.StudyStore()
        self.assertEqual(self.store.get_assignment_workspace(self.assignment), values)
        self.assertEqual(self.store.get_notes(self.course), "Important existing course notes.")
        self.assertEqual(self.store.assignments(self.course)[0]["title"], "Final paper")

    def test_invalid_fields_do_not_partially_overwrite(self):
        original = empty_workspace()
        original["draft"] = "KEEP THIS TEXT"
        self.store.save_assignment_workspace(self.assignment, original)
        with self.assertRaises(ValueError):
            self.store.save_assignment_workspace(
                self.assignment, dict(original, rubric="x" * 120001))
        self.assertEqual(self.store.get_assignment_workspace(self.assignment)["draft"],
                         "KEEP THIS TEXT")

    def test_deletion_cascades_new_record_but_keeps_course_notes(self):
        values = empty_workspace()
        values["draft"] = "Existing content"
        self.store.save_assignment_workspace(self.assignment, values)
        self.store.delete_assignment(self.assignment)
        self.assertEqual(self.store.get_notes(self.course), "Important existing course notes.")
        self.assertIsNone(self.store.assignment_record(self.assignment))
        self.assertEqual(self.store.db.execute(
            "SELECT COUNT(*) FROM assignment_workspaces").fetchone()[0], 0)

    def test_flashcard_review_and_duplicates(self):
        self.assertEqual(self.store.add_flashcards(self.course, [
            ("Theorist?", "Erikson"), ("Trait?", "Personality traits"),
            ("Theorist?", "Erikson")]), 2)
        cards = self.store.flashcards(self.course)
        self.assertEqual(len(cards), 2)
        self.assertTrue(self.store.record_flashcard_review(cards[0]["id"], False))
        cards = self.store.flashcards(self.course)
        self.assertEqual(cards[0]["incorrect"], 1)
        self.assertEqual(next_card(cards)[0]["id"], cards[0]["id"])
        self.assertTrue(self.store.record_flashcard_review(cards[1]["id"], True))
        self.store.delete_flashcard(self.course, cards[1]["id"])
        self.assertEqual(len(self.store.flashcards(self.course)), 1)

    def test_bom_csv_import_and_repeat_skip(self):
        path = self.root / "cards.csv"
        path.write_text("\ufeffQuestion,Answer\nEI?,Emotional intelligence\n"
                        "EI?,Emotional intelligence\nABC,XYZ\n", encoding="utf-8")
        result = parse_flashcards_csv(path)
        self.assertEqual(result, {"cards": [("EI?", "Emotional intelligence"),
                                            ("ABC", "XYZ")], "skipped":1})
        self.store.add_flashcards(self.course, result["cards"])
        retry = parse_flashcards_csv(path, self.store.flashcards(self.course))
        self.assertEqual(retry["cards"], [])
        self.assertEqual(retry["skipped"], 3)


class StudyWorkbookHelpersTests(unittest.TestCase):
    def test_no_fabricated_sources_or_grades(self):
        d = empty_workspace()
        d["instructions"] = "Evaluate a concept"
        d["draft"] = "Claim [SOURCE NEEDED]"
        report = readiness_report(d)
        self.assertIn("Draft contains [SOURCE NEEDED] placeholders", report["missing"])
        self.assertFalse(report["ready_for_review"])

    def test_webbie_handoff_explicit_and_unverified(self):
        d = empty_workspace()
        d.update(instructions="Write a paper.", rubric="APA references",
                 research="Unverified owner note", references="Owner reference")
        self.assertIn("ASSIGNMENT RUBRIC", webbie_directions(d))
        self.assertIn("UNVERIFIED", webbie_materials(d))
        self.assertIn("VERIFY BEFORE CITING", webbie_materials(d))
        with self.assertRaises(ValueError):
            webbie_directions(empty_workspace())

    def test_reject_incomplete_or_unreadable_fields(self):
        with self.assertRaises(ValueError):
            normalized_fields({"draft": "Missing required fields"})
        d = empty_workspace()
        d["research"] = "\x00"
        with self.assertRaises(ValueError):
            normalized_fields(d)


if __name__ == "__main__":
    unittest.main()
