"""Offline tests for Study assignment importing and private calendar export."""
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from study.assignment_planner import parse_assignment_csv, calendar_text, write_calendar


class AssignmentPlannerTests(unittest.TestCase):
    def test_csv_skips_duplicates_and_completed_and_accepts_utf8_bom(self):
        with tempfile.TemporaryDirectory() as folder:
            csv_file = Path(folder) / "assignments.csv"
            csv_file.write_text("\ufeffTitle,Due,Status\nEssay,2026-10-18,Open\n"
                                "Essay,2026-10-18,Open\nOld,2026-10-12,Complete\n"
                                "Discussion,,Open\n", encoding="utf-8")
            parsed = parse_assignment_csv(csv_file, [{"title": "Essay", "due": "2026-10-18"}])
            self.assertEqual(parsed, {"rows": [("Discussion", "")], "skipped": 2, "completed": 1})

    def test_bad_dates_and_malformed_csv_are_rejected_without_writes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "work.csv"
            for raw in ("Title,Due\nQuiz,10/20/2026\n",
                        "Title,Due\nQuiz,2026-02-30\n",
                        "Title,Due\nQuiz,2026-10-20,EXTRA\n"):
                path.write_text(raw, encoding="utf-8")
                with self.assertRaises(ValueError):
                    parse_assignment_csv(path)

    def test_calendar_excludes_completed_and_unknown_deadlines(self):
        items = [
            {"id": 1, "course": "PSY-328", "title": "Final, part; two", "due": "2026-10-18", "status": "Open"},
            {"id": 2, "course": "SOC-112", "title": "Done", "due": "2026-10-12", "status": "Complete"},
            {"id": 3, "course": "SOC-112", "title": "Unknown", "due": "Sunday", "status": "Open"}
        ]
        value, count = calendar_text(items, now=datetime(2026, 10, 11, tzinfo=timezone.utc))
        self.assertEqual(count, 1)
        self.assertIn("DTSTART;VALUE=DATE:20261018", value)
        self.assertIn("DTEND;VALUE=DATE:20261019", value)
        self.assertIn("SUMMARY:PSY-328: Final\\, part\\; two", value)
        self.assertNotIn("Unknown", value)
        self.assertEqual(value.count("BEGIN:VEVENT"), 1)
        self.assertIn("\r\n", value)

    def test_calendar_export_never_clobbers_unapproved_existing_file(self):
        assignments = [{"id": 1, "course": "PSY", "title": "Paper", "due": "2026-10-18", "status": "Open"}]
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "school.ics"
            target.write_text("KEEP", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                write_calendar(target, assignments)
            self.assertEqual(target.read_text(), "KEEP")
            self.assertEqual(write_calendar(target, assignments, overwrite=True), 1)
            self.assertIn("BEGIN:VCALENDAR", target.read_text())
            self.assertEqual(list(Path(folder).glob(".study-cal-*")), [])

    def test_unicode_folding_keeps_lines_within_75_octets(self):
        assignments = [{"id": 3, "course": "SOC", "title": "É" * 130, "due": "2026-10-20", "status": "Open"}]
        data, count = calendar_text(assignments)
        self.assertEqual(count, 1)
        self.assertTrue(all(len(line.encode("utf-8")) <= 75 for line in data.split("\r\n")))


if __name__ == "__main__":
    unittest.main()
