"""Tests for non-destructive, course-isolated Study homework drafts."""
import tempfile
import unittest
from pathlib import Path

from study.draft_storage import drafts_folder, label_part, save_snapshot, read_snapshot


class DraftSnapshotsTests(unittest.TestCase):
    def test_new_version_never_overwrites_previous(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root) / "PSY-328"
            first = save_snapshot(folder, "Week 4 / Reflection", "My first attempt.")
            second = save_snapshot(folder, "Week 4 / Reflection", "My revision.")
            self.assertNotEqual(first, second)
            self.assertEqual(read_snapshot(first, folder), "My first attempt.")
            self.assertEqual(read_snapshot(second, folder), "My revision.")
            self.assertEqual(first.stat().st_mode & 0o077, 0)
            self.assertIn("Week-4-Reflection", first.name)

    def test_blank_and_oversized_drafts_fail(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                save_snapshot(root, "Essay", "   ")
            with self.assertRaises(ValueError):
                save_snapshot(root, "Essay", "x" * 500001)
            self.assertEqual(list(Path(root).rglob("*.txt")), [])

    def test_other_courses_cannot_restore_drafts(self):
        with tempfile.TemporaryDirectory() as root:
            first_course = Path(root) / "PSY"
            second_course = Path(root) / "SOC"
            snapshot = save_snapshot(first_course, "Assignment", "Private draft.")
            with self.assertRaisesRegex(ValueError, "outside this course"):
                read_snapshot(snapshot, second_course)

    def test_existing_draft_symlink_not_read(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root) / "Course"
            existing = save_snapshot(folder, "Essay", "Owner writing.")
            linked = drafts_folder(folder) / "alias.txt"
            linked.symlink_to(existing)
            with self.assertRaises(ValueError):
                read_snapshot(linked, folder)

    def test_safe_assignment_label(self):
        self.assertEqual(label_part("../hello <course>?"), "hello-course")


if __name__ == "__main__":
    unittest.main()
