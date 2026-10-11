"""Offline regression checks for local Study steps, source notes, weekly worklists."""
from datetime import date
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from study import store as store_module
from study.milestones import (
    STARTER_STEPS, valid_step, valid_source, weekly_plan, workload_totals,
)


class StudyMilestoneTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.patchers = [
            patch.object(store_module, "DATA_DIR", root / "state"),
            patch.object(store_module, "DB_PATH", root / "state/study.db"),
            patch.object(store_module, "DOCUMENTS_ROOT", root / "Documents"),
        ]
        for patcher in self.patchers:
            patcher.start()
        self.store = store_module.StudyStore()
        self.psych = self.store.add_course("PSY-328")
        self.soc = self.store.add_course("SOC-112")
        self.store.add_assignment(self.psych, "Personality essay", "2026-10-15")
        self.store.add_assignment(self.soc, "Sociology final", "2026-10-18")
        self.store.add_assignment(self.soc, "Undated work")
        self.store.add_assignment(self.psych, "Old assignment", "2026-10-08")
        self.essay = next(row["id"] for row in self.store.assignments(self.psych)
                          if row["title"] == "Personality essay")
        self.final = next(row["id"] for row in self.store.assignments(self.soc)
                          if row["title"] == "Sociology final")
        self.store.save_notes(self.psych, "Keep my existing real class notes.")

    def tearDown(self):
        self.store.close()
        for patcher in reversed(self.patchers):
            patcher.stop()
        self.tmp.cleanup()

    def test_checklist_duplicate_protection_and_status(self):
        count = self.store.add_assignment_steps(
            self.essay, [(name, "") for name in STARTER_STEPS])
        self.assertEqual(count, len(STARTER_STEPS))
        self.assertEqual(self.store.add_assignment_steps(
            self.essay, [(name, "") for name in STARTER_STEPS]), 0)
        steps = self.store.assignment_steps(self.essay)
        self.assertEqual(len(steps), 7)
        step = steps[0]["id"]
        self.assertTrue(self.store.set_step_completed(self.essay, step, True))
        self.assertFalse(self.store.set_step_completed(self.final, step, False))
        self.assertEqual(sum(x["completed"] for x in self.store.assignment_steps(self.essay)), 1)
        self.assertTrue(self.store.set_step_completed(self.essay, step, False))
        self.store.delete_assignment_step(self.final, step)  # Must not cross courses.
        self.assertEqual(len(self.store.assignment_steps(self.essay)), 7)

    def test_invalid_step_batch_does_not_add_partial_rows(self):
        with self.assertRaises(ValueError):
            self.store.add_assignment_steps(
                self.essay, [("Valid", ""), ("Invalid", "2026-02-31")])
        self.assertEqual(self.store.assignment_steps(self.essay), [])
        for text, due in [("", "2026-10-14"), ("Good", "next Thursday"),
                          ("Good", "2026-13-20"), ("x" * 241, "")]:
            with self.assertRaises(ValueError):
                valid_step(text, due)

    def test_source_notes_are_owner_supplied_and_assignment_scoped(self):
        citation = "Author, A. (2023). Journal article."
        self.assertTrue(self.store.add_assignment_source(
            self.essay, citation, "https://example.org", "Verify actual metadata."))
        self.assertFalse(self.store.add_assignment_source(self.essay, citation))
        rows = self.store.assignment_sources(self.essay)
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(self.store.assignment_sources(self.final)), 0)
        self.assertIsNone(self.store.assignment_source(self.final, rows[0]["id"]))
        self.assertEqual(rows[0]["notes"], "Verify actual metadata.")
        self.store.delete_assignment_source(self.final, rows[0]["id"])
        self.assertEqual(len(self.store.assignment_sources(self.essay)), 1)
        self.store.delete_assignment_source(self.essay, rows[0]["id"])
        self.assertEqual(len(self.store.assignment_sources(self.essay)), 0)

    def test_bad_source_cannot_change_saved_records(self):
        original = "Book title. (2021). Publisher."
        self.store.add_assignment_source(self.essay, original)
        for ref, url, notes in [("", "", ""), ("A\nB", "", ""),
                                (original, "x" * 501, ""),
                                (original, "", "\x00")]:
            with self.subTest(ref=ref[:20]), self.assertRaises(ValueError):
                valid_source(ref, url, notes)
        self.assertEqual(len(self.store.assignment_sources(self.essay)), 1)

    def test_weekly_plan_uses_owner_dates_and_subtask_progress(self):
        self.store.add_assignment_step(self.essay, "Outline", "2026-10-12")
        self.store.add_assignment_step(self.essay, "Finish draft", "2026-10-13")
        first = self.store.assignment_steps(self.essay)[0]
        self.store.set_step_completed(self.essay, first["id"], True)
        self.store.add_assignment_step(self.final, "Review source notes")
        items = weekly_plan(self.store.planner_rows(),
                            today=date(2026, 10, 11), days=7)
        self.assertEqual([row["title"] for row in items],
                         ["Old assignment", "Personality essay",
                          "Sociology final", "Undated work"])
        self.assertEqual(items[0]["urgency"], "Overdue")
        self.assertEqual(items[1]["progress"], "1/2")
        self.assertEqual(items[1]["next_action"], "Finish draft")
        self.assertEqual(items[-1]["urgency"], "No valid date")
        totals = workload_totals(items)
        self.assertEqual(totals["steps_left"], 2)
        self.assertEqual(totals["undated"], 1)
        self.assertEqual(totals["overdue"], 1)

    def test_completed_not_in_default_weekly_plan_and_no_guessed_due(self):
        self.store.set_assignment_status(self.essay, "Complete")
        open_items = weekly_plan(self.store.planner_rows(), today=date(2026, 10, 11))
        self.assertNotIn("Personality essay", [item["title"] for item in open_items])
        full = weekly_plan(self.store.planner_rows(), today=date(2026, 10, 11),
                           include_completed=True)
        self.assertIn("Personality essay", [item["title"] for item in full])
        with self.assertRaises(ValueError):
            weekly_plan([], days=10)

    def test_restart_preserves_courses_workspaces_checklist_and_sources(self):
        self.store.add_assignment_step(self.essay, "Read chapter", "2026-10-12")
        self.store.add_assignment_source(self.essay, "Example reference.")
        self.store.close()
        self.store = store_module.StudyStore()
        self.assertEqual(self.store.get_notes(self.psych), "Keep my existing real class notes.")
        self.assertEqual(len(self.store.assignment_steps(self.essay)), 1)
        self.assertEqual(len(self.store.assignment_sources(self.essay)), 1)

    def test_delete_parent_cascades_only_associated_steps_and_sources(self):
        self.store.add_assignment_step(self.essay, "Draft essay")
        self.store.add_assignment_step(self.final, "Prepare sociology final")
        self.store.add_assignment_source(self.essay, "User article.")
        self.store.delete_assignment(self.essay)
        self.assertEqual(len(self.store.assignment_steps(self.essay)), 0)
        self.assertEqual(len(self.store.assignment_sources(self.essay)), 0)
        self.assertEqual(len(self.store.assignment_steps(self.final)), 1)
        self.assertEqual(self.store.get_notes(self.psych), "Keep my existing real class notes.")


if __name__ == "__main__":
    unittest.main()
