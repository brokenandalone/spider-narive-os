"""Study native dashboard and store agree on expected due-date counters."""
from datetime import date
from pathlib import Path
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("study_overview_continuity", ROOT / "study/dashboard.py")
dashboard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dashboard)

class StudyDashboardContinuity(unittest.TestCase):
    def test_day_and_week_counts_without_double_counting(self):
        today = date(2026, 10, 11)
        records = [
            {"title": "Yesterday", "due": "2026-10-10", "status": "Open"},
            {"title": "Today", "due": "2026-10-11", "status": "Open"},
            {"title": "Tomorrow", "due": "2026-10-12", "status": "Open"},
            {"title": "Day seven", "due": "2026-10-18", "status": "Open"},
            {"title": "Day eight", "due": "2026-10-19", "status": "Open"},
            {"title": "Undated", "due": "", "status": "Open"},
            {"title": "Completed", "due": "2026-10-11", "status": "Complete"},
        ]
        result = dashboard.overview(records, today=today)
        self.assertEqual(
            [result[key] for key in ("open", "complete", "overdue", "today", "next_7_days", "undated")],
            [6, 1, 1, 1, 2, 1],
        )
        self.assertEqual([row["title"] for row in result["upcoming"]][:2],
                         ["Yesterday", "Today"])

    def test_empty_dashboard_still_has_all_native_ui_fields(self):
        result = dashboard.overview([], today=date(2026, 10, 11))
        for name in ("open", "complete", "overdue", "today", "next_7_days", "undated", "upcoming"):
            self.assertIn(name, result)

if __name__ == "__main__":
    unittest.main()
