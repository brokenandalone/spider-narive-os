"""Local course reading index, explicit import and search regression tests."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from study import store as store_module
from study.reading_library import (
    import_course_reading, find_course_excerpts, selected_reading_excerpt,
    safe_reading_name,
)


class ReadingLibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.root = root
        self.config = root / "config"
        self.docs = root / "Documents"
        self.patchers = [
            patch.object(store_module, "DATA_DIR", self.config),
            patch.object(store_module, "DB_PATH", self.config / "study.db"),
            patch.object(store_module, "DOCUMENTS_ROOT", self.docs),
        ]
        for p in self.patchers:
            p.start()
        self.store = store_module.StudyStore()
        self.psych = self.store.add_course("PSY-328")
        self.soc = self.store.add_course("SOC-112")
        self.source = root / "example-reading.txt"
        self.source.write_text(
            "Emotional intelligence has interpersonal and self-regulation "
            "dimensions. This is an owner supplied course note.",
            encoding="utf-8")
        self.store.save_notes(self.psych, "My existing notes remain.")

    def tearDown(self):
        self.store.close()
        for p in reversed(self.patchers):
            p.stop()
        self.temp.cleanup()

    def test_import_copies_without_changing_user_original_and_persists(self):
        text = self.source.read_text(encoding="utf-8")
        result = import_course_reading(self.store, self.psych, self.source)
        self.assertTrue(result["created"])
        saved = self.store.course_readings(self.psych)
        self.assertEqual(len(saved), 1)
        self.assertIn("Emotional intelligence", saved[0]["excerpt"])
        self.assertEqual(self.source.read_text(encoding="utf-8"), text)
        copy = self.store.course_folder(self.psych) / saved[0]["relative_path"]
        self.assertEqual(copy.read_text(encoding="utf-8"), text)
        self.store.close()
        self.store = store_module.StudyStore()
        self.assertEqual(len(self.store.course_readings(self.psych)), 1)
        self.assertEqual(self.store.get_notes(self.psych), "My existing notes remain.")

    def test_identical_import_skips_and_duplicate_name_never_clobbers(self):
        self.assertTrue(import_course_reading(self.store, self.psych, self.source)["created"])
        second = import_course_reading(self.store, self.psych, self.source)
        self.assertFalse(second["created"])
        self.assertEqual(len(self.store.course_readings(self.psych)), 1)
        changed = self.root / "other" / "example-reading.txt"
        changed.parent.mkdir()
        changed.write_text("Second source, unique content.", encoding="utf-8")
        result = import_course_reading(self.store, self.psych, changed)
        self.assertTrue(result["created"])
        self.assertEqual(len(self.store.course_readings(self.psych)), 2)
        names = sorted(x.name for x in (
            self.store.course_folder(self.psych) / "Readings").iterdir())
        self.assertEqual(names, ["example-reading-2.txt", "example-reading.txt"])
        self.assertIn("Emotional intelligence",
                      (self.store.course_folder(self.psych) /
                       "Readings/example-reading.txt").read_text())

    def test_course_isolation_and_owner_search(self):
        import_course_reading(self.store, self.psych, self.source)
        self.assertEqual(self.store.course_readings(self.soc), [])
        matching = find_course_excerpts(self.store.course_readings(self.psych), "self-regulation")
        self.assertEqual(len(matching), 1)
        self.assertIn("self-regulation", matching[0]["snippet"])
        self.assertEqual(find_course_excerpts(
            self.store.course_readings(self.soc), "self-regulation"), [])
        report = selected_reading_excerpt(self.store.course_readings(self.psych)[0])
        self.assertIn("NOT a verified reference", report)
        self.assertIn("emotional intelligence", report.lower())

    def test_disallow_symlink_and_invalid_files(self):
        symlink = self.root / "shortcut.txt"
        symlink.symlink_to(self.source)
        with self.assertRaises(ValueError):
            import_course_reading(self.store, self.psych, symlink)
        unsupported = self.root / "file.exe"
        unsupported.write_text("Bad", encoding="utf-8")
        with self.assertRaises(ValueError):
            import_course_reading(self.store, self.psych, unsupported)
        for name in (".hidden.pdf", "..", "bad:name.docx", "a" * 183 + ".txt"):
            with self.assertRaises(ValueError):
                safe_reading_name(name)
        with self.assertRaises(ValueError):
            find_course_excerpts([], "?" * 200)

    def test_copy_failure_leaves_no_false_index(self):
        with patch.object(self.store, "add_course_reading", side_effect=ValueError("bad DB")):
            with self.assertRaisesRegex(ValueError, "bad DB"):
                import_course_reading(self.store, self.psych, self.source)
        root = self.store.course_folder(self.psych) / "Readings"
        self.assertEqual(list(root.iterdir()), [])
        self.assertEqual(len(self.store.course_readings(self.psych)), 0)

    def test_indexed_reading_kept_when_other_course_is_removed(self):
        import_course_reading(self.store, self.psych, self.source)
        self.store.remove_course(self.soc)
        self.assertEqual(len(self.store.course_readings(self.psych)), 1)


if __name__ == "__main__":
    unittest.main()
