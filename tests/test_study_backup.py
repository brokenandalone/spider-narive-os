"""Study private backup regression tests using disposable schoolwork only."""
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from study import store as store_module
from study.study_backup import create_study_backup, verify_study_backup


class StudyBackupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.data = self.root / "settings"
        self.docs = self.root / "Documents" / "Study"
        self.patchers = [
            patch.object(store_module, "DATA_DIR", self.data),
            patch.object(store_module, "DB_PATH", self.data / "study.db"),
            patch.object(store_module, "DOCUMENTS_ROOT", self.docs),
        ]
        for patcher in self.patchers:
            patcher.start()
        self.store = store_module.StudyStore()
        self.course = self.store.add_course("PSY-328")
        self.store.add_assignment(self.course, "Essay", "2026-10-18")
        self.store.save_notes(self.course, "My draft should not disappear.")
        self.material = self.store.course_folder(self.course) / "Research" / "reading.md"
        self.material.write_text("My research notes.", encoding="utf-8")

    def tearDown(self):
        self.store.close()
        for patcher in reversed(self.patchers):
            patcher.stop()
        self.tmp.cleanup()

    def backup(self, target=None):
        target = target or self.root / "study-test.zip"
        return create_study_backup(self.data / "study.db", self.docs, target)

    def test_consistent_database_and_files_can_be_verified(self):
        result = self.backup()
        path = self.root / "study-test.zip"
        self.assertTrue(path.is_file())
        self.assertGreaterEqual(result["files"], 1)
        self.assertEqual(verify_study_backup(path)["verified"], True)
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            self.assertIn("StudyData/study.db", names)
            self.assertTrue(any(n.endswith("reading.md") for n in names))
            manifest = json.loads(archive.read("manifest.json"))
            self.assertEqual(manifest["format"], "spider-study-backup-v1")
            # An actual consistent SQLite snapshot, not a copy of live WAL bytes.
            dbdata = archive.read("StudyData/study.db")
        snapshot = self.root / "restored-test-copy.sqlite"
        snapshot.write_bytes(dbdata)
        with sqlite3.connect(snapshot) as copied:
            note = copied.execute("SELECT content FROM notes").fetchone()[0]
        self.assertEqual(note, "My draft should not disappear.")

    def test_archive_never_overwrites_existing_zip(self):
        target = self.root / "study-test.zip"
        target.write_text("Owner's original data", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            self.backup(target)
        self.assertEqual(target.read_text(), "Owner's original data")

    def test_destination_inside_documents_blocked(self):
        with self.assertRaises(ValueError):
            self.backup(self.docs / "accidental-recursive.zip")

    def test_changed_archive_member_fails_checksum_validation(self):
        self.backup()
        original = self.root / "study-test.zip"
        altered = self.root / "altered.zip"
        with zipfile.ZipFile(original) as source, zipfile.ZipFile(
                altered, "w", compression=zipfile.ZIP_DEFLATED) as sink:
            for name in source.namelist():
                value = source.read(name)
                if name.endswith("reading.md"):
                    value = b"Altered private notes"
                sink.writestr(name, value)
        with self.assertRaisesRegex(ValueError, "checksum|wrong size"):
            verify_study_backup(altered)

    def test_archive_path_traversal_rejected_before_trusting_manifest(self):
        unsafe = self.root / "unsafe.zip"
        with zipfile.ZipFile(unsafe, "w") as archive:
            archive.writestr("../outside.txt", "Oops")
            archive.writestr("manifest.json", "{}")
        with self.assertRaises(ValueError):
            verify_study_backup(unsafe)

    def test_symlink_files_not_included_in_backup(self):
        secret = self.root / "secret.txt"
        secret.write_text("Not part of coursework", encoding="utf-8")
        link = self.docs / "linked-secret.txt"
        link.symlink_to(secret)
        self.backup()
        with zipfile.ZipFile(self.root / "study-test.zip") as archive:
            self.assertNotIn("CourseFiles/linked-secret.txt", archive.namelist())
        self.assertEqual(secret.read_text(), "Not part of coursework")


if __name__ == "__main__":
    unittest.main()
