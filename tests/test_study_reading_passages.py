"""Long-text reading passages, provenance and additive Study migration regressions."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from study import store as store_module
from study.course_materials import read_course_document
from study.reading_library import import_course_reading, reindex_course_reading, file_digest
from study.reading_passages import (
    split_reading_passages, search_reading_passages, selected_passage_text,
)


class ReadingPassageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.root = root
        self.patchers = [
            patch.object(store_module, "DATA_DIR", root / "settings"),
            patch.object(store_module, "DB_PATH", root / "settings/study.db"),
            patch.object(store_module, "DOCUMENTS_ROOT", root / "course-files"),
        ]
        for p in self.patchers:
            p.start()
        self.store = store_module.StudyStore()
        self.course = self.store.add_course("PSY-328")
        self.other = self.store.add_course("SOC-112")
        self.store.add_assignment(self.course, "Essay", "2026-10-20")
        self.store.save_notes(self.course, "Preserve my existing class notes.")
        self.source = root / "long-source.txt"
        # Substantial useful material appears AFTER the old 12K truncation.
        self.source.write_text(
            ("Personality and identity examples. " * 1300) +
            "\nSOURCE END: Cognitive dissonance and self-perception.",
            encoding="utf-8")

    def tearDown(self):
        self.store.close()
        for p in reversed(self.patchers):
            p.stop()
        self.temp.cleanup()

    def test_import_searches_beyond_old_first_12k_limit(self):
        original = self.source.read_bytes()
        self.assertTrue(import_course_reading(self.store, self.course, self.source)["created"])
        records = self.store.course_readings(self.course)
        self.assertEqual(len(records), 1)
        self.assertLessEqual(len(records[0]["excerpt"]), 12000)
        chunks = self.store.reading_passages(self.course, records[0]["id"])
        self.assertGreater(len(chunks), 4)
        results = search_reading_passages(
            self.store.reading_passage_candidates(self.course), "cognitive dissonance")
        self.assertTrue(results)
        self.assertIn("cognitive dissonance", results[0]["snippet"].lower())
        self.assertGreater(results[0]["start_char"], 12000)
        passage = self.store.reading_passage(
            self.course, results[0]["id"], results[0]["passage_index"])
        text = selected_passage_text(records[0], passage)
        self.assertIn("extracted character range", text.lower())
        self.assertIn("NOT book or PDF page numbers", text)
        self.assertEqual(self.source.read_bytes(), original)
        self.assertEqual(self.store.get_notes(self.course),
                         "Preserve my existing class notes.")

    def test_course_isolation_across_passage_lookup_and_search(self):
        import_course_reading(self.store, self.course, self.source)
        record = self.store.course_readings(self.course)[0]
        self.assertEqual(self.store.reading_passages(self.other, record["id"]), [])
        self.assertIsNone(self.store.reading_passage(self.other, record["id"], 1))
        self.assertEqual(self.store.reading_passage_candidates(self.other), [])
        self.assertEqual(search_reading_passages([], "personality"), [])
        with self.assertRaises(ValueError):
            selected_passage_text(
                record, {"reading_id": record["id"] + 1, "body": "Mismatch"})

    def test_legacy_import_reindex_requires_owner_copied_file_and_checksum(self):
        folder = self.store.course_folder(self.course) / "Readings"
        folder.mkdir(parents=True, exist_ok=True)
        copied = folder / "old-reading.txt"
        copied.write_bytes(self.source.read_bytes())
        checksum = file_digest(copied)
        self.assertTrue(self.store.add_course_reading(
            self.course, copied.name, "Readings/old-reading.txt",
            checksum, self.source.read_text(encoding="utf-8")[:12000]))
        record = self.store.course_readings(self.course)[0]
        self.assertEqual(self.store.reading_passages(self.course, record["id"]), [])
        outcome = reindex_course_reading(self.store, self.course, record["id"])
        self.assertTrue(outcome["updated"])
        self.assertGreater(outcome["passages"], 4)
        self.assertFalse(reindex_course_reading(
            self.store, self.course, record["id"])["updated"])
        self.assertEqual(self.store.get_notes(self.course),
                         "Preserve my existing class notes.")

    def test_modified_legacy_file_refused_without_changing_index(self):
        folder = self.store.course_folder(self.course) / "Readings"
        folder.mkdir(parents=True, exist_ok=True)
        copied = folder / "older.txt"
        copied.write_bytes(self.source.read_bytes())
        self.store.add_course_reading(
            self.course, "older.txt", "Readings/older.txt",
            file_digest(copied), "Prior saved snippet")
        record = self.store.course_readings(self.course)[0]
        copied.write_text("Changed source content", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "changed"):
            reindex_course_reading(self.store, self.course, record["id"])
        self.assertEqual(self.store.reading_passages(self.course, record["id"]), [])
        self.assertEqual(self.store.course_reading(
            self.course, record["id"])["excerpt"], "Prior saved snippet")

    def test_passage_validation_is_atomic(self):
        with self.assertRaises(ValueError):
            self.store.add_course_reading(
                self.course, "broken.txt", "Readings/broken.txt",
                "a" * 64, "excerpt",
                passages=[(1, 0, 4, "valid"), (2, 4, 0, "broken")])
        self.assertEqual(self.store.course_readings(self.course), [])

    def test_bounds_and_default_reader_remain_stable(self):
        self.assertEqual(len(read_course_document(self.source)), 12000)
        self.assertGreater(len(read_course_document(
            self.source, max_chars=240000)), 12000)
        with self.assertRaises(ValueError):
            read_course_document(self.source, max_chars=240001)
        with self.assertRaises(ValueError):
            split_reading_passages("x" * 240001)
        with self.assertRaises(ValueError):
            search_reading_passages([], "?")
        self.assertTrue(split_reading_passages("meaningful passage"))

    def test_after_restart_index_and_course_assignments_survive(self):
        import_course_reading(self.store, self.course, self.source)
        original_count = len(self.store.reading_passage_candidates(self.course))
        self.store.close()
        self.store = store_module.StudyStore()
        self.assertEqual(
            len(self.store.reading_passage_candidates(self.course)), original_count)
        self.assertEqual(self.store.get_notes(self.course),
                         "Preserve my existing class notes.")
        self.assertEqual(
            self.store.assignments(self.course)[0]["title"], "Essay")


if __name__ == "__main__":
    unittest.main()
