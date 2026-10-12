"""Test exact-owner preservation with no in-place Spider OS writes."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("spider_owner_stage", ROOT / "tools/build_owner_preserving_stage.py")
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def git(repo, *parts):
    result = subprocess.run(["git", "-C", str(repo), *parts], capture_output=True,
                            check=True, text=True, timeout=10)
    return result.stdout.strip()


class OwnerFirstStageTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        home = Path(temp.name)
        self.candidate = home / "checkout"
        self.live = home / "installed"
        self.archive = home / "owner.zip"
        self.out = home / "staged"
        self.candidate.mkdir()
        self.live.mkdir()
        self.owner = {}
        for name in module.OWNER_FILES:
            path = self.candidate / name
            path.parent.mkdir(parents=True, exist_ok=True)
            original = self.live / name
            original.parent.mkdir(parents=True, exist_ok=True)
            if name.endswith(".py"):
                owner = b"def owner_unique():\n    return 'working pc'\n"
                candidate = b"def candidate_unique():\n    return 'new feature'\n"
            else:
                owner = b"#!/bin/bash\ntrue\n"
                candidate = b"#!/bin/bash\necho candidate\n"
            original.write_bytes(owner)
            path.write_bytes(candidate)
            self.owner[name] = owner
        with zipfile.ZipFile(self.archive, "w") as bundle:
            for name, data in self.owner.items():
                bundle.writestr("installed/" + name, data)
        git(self.candidate, "init", "-q")
        git(self.candidate, "-c", "user.name=Tester", "-c",
            "user.email=ci@example.test", "add", "--all")
        git(self.candidate, "-c", "user.name=Tester", "-c",
            "user.email=ci@example.test", "commit", "-qm", "synthetic candidate")
        self.sha = git(self.candidate, "rev-parse", "HEAD")

    def review(self):
        return module.stage(self.candidate, self.archive, self.out, self.sha,
                            installed=self.live)

    def test_copy_preserves_owner_files_but_leaves_candidate_checkout_alone(self):
        result = self.review()
        self.assertEqual(result["status"], "REVIEW_ONLY_NOT_INSTALLABLE")
        self.assertEqual(result["preserved_owner_files"], 31)
        self.assertEqual(len(result["files"]), 31)
        for name in module.OWNER_FILES:
            self.assertEqual((self.out/"staged-source"/name).read_bytes(), self.owner[name])
            self.assertNotEqual((self.candidate/name).read_bytes(), self.owner[name])
            self.assertEqual((self.live/name).read_bytes(), self.owner[name])
        self.assertTrue((self.out/"reconciliation.json").is_file())
        self.assertEqual(json.loads((self.out/"reconciliation.json").read_text())["status"],
                         "REVIEW_ONLY_NOT_INSTALLABLE")

    def test_pending_functions_are_not_silently_claimed(self):
        result = self.review()
        entry = next(x for x in result["files"] if x["path"] == "webbie/agent/webbie.py")
        self.assertIn("owner_unique", entry["owner_symbols_absent_in_candidate"])
        self.assertIn("candidate_unique", entry["candidate_symbols_absent_in_owner"])
        self.assertTrue(entry["requires_semantic_review"])

    def test_zip_missing_entry_blocks_before_output_exists(self):
        with zipfile.ZipFile(self.archive, "w") as bundle:
            bundle.writestr("installed/webbie/agent/webbie.py", b"def example(): pass\n")
        with self.assertRaisesRegex(ValueError, "exactly"):
            self.review()
        self.assertFalse(self.out.exists())

    def test_installed_drift_blocks_before_output_exists(self):
        (self.live/"webbie/agent/webbie.py").write_text("def changed(): pass\n")
        with self.assertRaisesRegex(ValueError, "changed since"):
            self.review()
        self.assertFalse(self.out.exists())

    def test_commit_drift_blocks_before_output_exists(self):
        with self.assertRaisesRegex(ValueError, "tested SHA"):
            module.stage(self.candidate, self.archive, self.out, "a"*40,
                         installed=self.live)
        self.assertFalse(self.out.exists())

    def test_local_tracked_source_change_blocks(self):
        (self.candidate/"webbie/agent/webbie.py").write_text("def unreviewed(): pass\n")
        with self.assertRaisesRegex(ValueError, "modified tracked"):
            self.review()

    def test_existing_output_never_overwritten(self):
        self.out.mkdir()
        (self.out/"owner-file").write_text("preserve me")
        with self.assertRaisesRegex(ValueError, "existing review"):
            self.review()
        self.assertEqual((self.out/"owner-file").read_text(), "preserve me")

    def test_invalid_python_blocks(self):
        (self.live/"webbie/agent/webbie.py").write_bytes(b"def broken(:\n")
        self.owner["webbie/agent/webbie.py"] = b"def broken(:\n"
        with zipfile.ZipFile(self.archive, "w") as bundle:
            for name, data in self.owner.items():
                bundle.writestr("installed/" + name, data)
        with self.assertRaises(SyntaxError):
            self.review()

    def test_stage_inside_checkout_or_live_is_forbidden(self):
        with self.assertRaisesRegex(ValueError, "outside both"):
            module.stage(self.candidate, self.archive, self.live/"stage", self.sha,
                         installed=self.live)
        with self.assertRaisesRegex(ValueError, "outside both"):
            module.stage(self.candidate, self.archive, self.candidate/"stage", self.sha,
                         installed=self.live)


if __name__ == "__main__":
    unittest.main()
