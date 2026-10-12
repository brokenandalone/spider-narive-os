"""Offline repeatability tests for immutable Spider OS known-good PC snapshots."""
import importlib.util
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("spider_baseline_test", ROOT / "tools/known_good_baseline.py")
baseline = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(baseline)


class KnownGoodTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        home = Path(self.temp.name)
        self.source, self.installed, self.snapshots = (home / "source", home / "live", home / "baseline")
        self.source.mkdir()
        self.installed.mkdir()
        self.snapshots.mkdir(mode=0o700)
        self.paths = ["webbie/agent/webbie.py", "webbie/brain/brain.py", "study/study.py"]
        for root in (self.source, self.installed):
            for rel in self.paths:
                file = root / rel
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text("baseline stable feature\n")
        config = self.installed / "webbie/config/default.json"
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(json.dumps({"ollama": {"model": "qwen3:4b"}}))
        batch = self.source / "system/release_batch.py"
        batch.parent.mkdir()
        batch.write_text("APP_FILES = " + repr(tuple(self.paths)) + "\n")
        self.config = config
        self.batch = batch

    def record(self):
        # GitHub CI runs as non-root, but test isolation also works in root sandboxes.
        with patch.object(baseline.os, "geteuid", return_value=1000):
            return baseline.capture(repo=self.source, installed=self.installed,
                                    folder=self.snapshots, confirmed=True,
                                    clock=lambda: datetime(2026,10,11,18,0,tzinfo=timezone.utc))

    def review(self):
        return baseline.verify(repo=self.source, installed=self.installed, folder=self.snapshots)

    def test_explicit_working_confirmation_required(self):
        with self.assertRaisesRegex(ValueError, "Owner must confirm"):
            baseline.capture(repo=self.source, installed=self.installed, folder=self.snapshots)
        self.assertEqual(list(self.snapshots.iterdir()), [])

    def test_model_and_source_baseline_snapshot_is_private(self):
        output = self.record()
        self.assertEqual(output["status"], "CAPTURED_AFTER_MANUAL_CONFIRMATION")
        path = self.snapshots / output["snapshot"]
        self.assertEqual(path.stat().st_mode & 0o077, 0)
        raw = path.read_text()
        self.assertIn("qwen3:4b", raw)
        self.assertNotIn("baseline stable feature", raw)
        self.assertEqual(self.review()["status"], "REVIEW_REQUIRED")
        self.assertTrue(self.review()["model_preserved"])
        self.assertEqual(self.review()["candidate_changes"], [])

    def test_in_place_drift_is_blocked_before_overwrite(self):
        self.record()
        (self.installed / "webbie/brain/brain.py").write_text("owner newer fix\n")
        result = self.review()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("webbie/brain/brain.py" in s for s in result["blockers"]))

    def test_missing_module_is_not_ignored(self):
        self.record()
        (self.installed / "study/study.py").unlink()
        self.assertEqual(self.review()["status"], "BLOCKED")

    def test_old_source_cannot_drop_working_module_silently(self):
        self.record()
        self.batch.write_text("APP_FILES = " + repr(tuple(self.paths[:2])) + "\n")
        result = self.review()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("omitted working module" in s for s in result["blockers"]))

    def test_model_selection_change_is_blocked(self):
        self.record()
        self.config.write_text(json.dumps({"ollama": {"model": "qwen3:1.7b"}}))
        result = self.review()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["model_preserved"])

    def test_new_candidate_code_is_reported_not_silently_approved(self):
        self.record()
        (self.source / "webbie/brain/brain.py").write_text("new candidate implementation\n")
        report = self.review()
        self.assertEqual(report["status"], "REVIEW_REQUIRED")
        self.assertIn("webbie/brain/brain.py", report["candidate_changes"])

    def test_new_safe_addition_is_included_but_review_required(self):
        self.record()
        self.paths.append("author/new_view.py")
        (self.source / "author").mkdir(exist_ok=True)
        (self.source / "author/new_view.py").write_text("new module\n")
        self.batch.write_text("APP_FILES = " + repr(tuple(self.paths)) + "\n")
        report = self.review()
        self.assertEqual(report["status"], "REVIEW_REQUIRED")
        self.assertIn("author/new_view.py", report["candidate_changes"])

    def test_new_untracked_live_code_blocks(self):
        self.record()
        self.paths.append("author/new_view.py")
        for root in (self.source, self.installed):
            (root / "author").mkdir(exist_ok=True)
            (root / "author/new_view.py").write_text("module installed by someone else\n")
        self.batch.write_text("APP_FILES = " + repr(tuple(self.paths)) + "\n")
        self.assertEqual(self.review()["status"], "BLOCKED")

    def test_missing_or_world_readable_golden_record_blocks(self):
        self.assertEqual(self.review()["status"], "BLOCKED")
        result = self.record()
        (self.snapshots / result["snapshot"]).chmod(0o644)
        self.assertEqual(self.review()["status"], "BLOCKED")

    def test_symlinked_live_code_is_not_trusted(self):
        self.record()
        file = self.installed / "study/study.py"
        file.unlink()
        file.symlink_to(self.source / "study/study.py")
        self.assertEqual(self.review()["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
