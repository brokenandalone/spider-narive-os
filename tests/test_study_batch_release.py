"""Offline native Study + Studio coverage for the one-shot Spider OS batch release."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from system import release_batch as batch

ROOT = Path(__file__).resolve().parents[1]


class StudyBatchReleaseTests(unittest.TestCase):
    def test_study_and_studio_sources_share_one_batch_manifest(self):
        items = batch.prepare_items(root=ROOT, install=Path("/tmp/spider-release-inspection"),
                                    units=Path("/tmp/spider-release-units"),
                                    home=Path("/tmp/spider-release-owner"))
        references = [item.reference for item in items]
        for required in (
            "study/study.py", "study/store.py", "study/homework.py",
            "study/homework_ui.py", "study/assignment_review.py",
            "study/school_onedrive.py", "study/school_upload.py",
            "study/course_materials.py", "study/bin/webbie-homework",
            "studio/main.py", "studio/ai_panel.py", "studio/music_backend.py",
            "webbie/agent/webbie.py",
        ):
            self.assertIn(required, references)
        self.assertEqual(len(items), len({str(item.target) for item in items}))
        for item in items:
            self.assertTrue(item.source.is_file(), str(item.source))
        forbidden = ("assignments.db", "writing-style.txt", "rclone.conf", "oauth")
        self.assertFalse(any(term in reference for term in forbidden
                             for reference in references))

    def test_git_blob_fingerprint_matches_known_git_object(self):
        with tempfile.TemporaryDirectory() as folder:
            document = Path(folder) / "test.txt"
            document.write_bytes(b"hello\n")
            self.assertEqual(batch.git_blob_sha(document),
                             "ce013625030ba8dba906f756967f9e9ca394464a")

    def test_recognized_older_study_source_is_versioned_and_rollbackable(self):
        with tempfile.TemporaryDirectory() as folder:
            temporary = Path(folder)
            source = ROOT / "study/store.py"
            target = temporary / "install/study/store.py"
            target.parent.mkdir(parents=True)
            old = "# recognized old study store\npass\n"
            target.write_text(old)
            item = batch.Item(source, target, reference="study/store.py")
            known = {batch.git_blob_sha(target)}
            with patch.dict(batch.KNOWN_STUDY_BLOBS, {"study/store.py": known}):
                planned = batch.inspect([item], project_root=ROOT,
                                        refs=(), known_checker=lambda *args: False)
                self.assertEqual(planned[0][1], "UPGRADE")
                backup = batch.apply(
                    [item], temporary / "backup", project_root=ROOT, refs=(),
                    known_checker=lambda *args: False)
                self.assertEqual(target.read_text(), source.read_text())
                batch.rollback([item], backup, temporary / "backup", dry_run=True)
                batch.rollback([item], backup, temporary / "backup", dry_run=False)
                self.assertEqual(target.read_text(), old)

    def test_custom_study_store_blocks_entire_batch_before_writes(self):
        with tempfile.TemporaryDirectory() as folder:
            temporary = Path(folder)
            first = batch.Item(ROOT / "study/homework.py",
                               temporary / "install/study/homework.py",
                               reference="study/homework.py")
            custom = temporary / "install/study/store.py"
            custom.parent.mkdir(parents=True)
            custom.write_text("# owner PC edits\npass\n")
            second = batch.Item(ROOT / "study/store.py", custom,
                                reference="study/store.py")
            result = batch.inspect([first, second], refs=(),
                                   known_checker=lambda *args: False)
            self.assertEqual([status for _, status, _ in result], ["ADD", "BLOCKED"])
            with self.assertRaises(RuntimeError):
                batch.apply([first, second], temporary / "backup", refs=(),
                            known_checker=lambda *args: False)
            self.assertFalse(first.target.exists())
            self.assertEqual(custom.read_text(), "# owner PC edits\npass\n")


if __name__ == "__main__":
    unittest.main()
