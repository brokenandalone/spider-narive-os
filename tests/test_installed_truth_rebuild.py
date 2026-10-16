#!/usr/bin/env python3
"""Regression tests for the read-only installed-source reconciliation."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

TOOL = Path(__file__).resolve().parents[1] / "tools" / "spider_installed_truth.py"
spec = importlib.util.spec_from_file_location("installed_truth", TOOL)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class InstalledTruthTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.installed = self.root / "installed"
        self.report = self.root / "report"
        self.repo.mkdir()
        self.installed.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "config", "user.email",
                        "testing@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "config", "user.name",
                        "Spider Test"], check=True)

    def _add(self, base, name, content):
        p = base / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return p

    def _git_add(self):
        subprocess.run(["git", "-C", str(self.repo), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.repo), "commit", "-qm", "fixture"],
                       check=True)

    def test_classifies_matching_modified_and_both_directions(self):
        self._add(self.repo, "webbie/agent/webbie.py", "working")
        self._add(self.repo, "studio/engine.py", "upstream")
        self._add(self.repo, "art_lab/main.py", "only-in-repo")
        self._add(self.installed, "webbie/agent/webbie.py", "working")
        self._add(self.installed, "studio/engine.py", "owner-custom")
        self._add(self.installed, "kali-bay/tools.py", "only-installed")
        self._git_add()
        outcome = audit.make_report(self.installed, self.repo, self.report)
        self.assertEqual(outcome["counts"], {
            "identical": 1, "different": 1, "installed_only": 1, "repo_only": 1
        })
        manifest = json.loads((self.report / "manifest.json").read_text())
        self.assertIn("webbie/agent/webbie.py", manifest["groups"]["identical"])
        self.assertIn("studio/engine.py", manifest["groups"]["different"])
        self.assertIn("kali-bay/tools.py", manifest["groups"]["installed_only"])
        self.assertIn("art_lab/main.py", manifest["groups"]["repo_only"])
        self.assertNotIn("owner-custom", (self.report / "SUMMARY.md").read_text())

    def test_does_not_follow_symlinks_or_include_secret_tree(self):
        self._add(self.repo, "webbie/brain.py", "basic")
        self._add(self.installed, "webbie/brain.py", "basic")
        outside = self._add(self.root, "outside.py", "sensitive token string")
        (self.installed / "unsafe.py").symlink_to(outside)
        self._add(self.installed, "private/keys.py", "PRIVATE_KEY")
        self._add(self.installed, "recordings/huge.py", "recorded data")
        self._git_add()
        audit.make_report(self.installed, self.repo, self.report)
        manifest = json.loads((self.report / "manifest.json").read_text())
        self.assertNotIn("unsafe.py", manifest["installed_sha256"])
        self.assertNotIn("private/keys.py", manifest["installed_sha256"])
        self.assertNotIn("recordings/huge.py", manifest["installed_sha256"])
        self.assertIn("unsafe.py", manifest["skipped"])
        self.assertNotIn("PRIVATE_KEY", (self.report / "manifest.json").read_text())
        self.assertNotIn("sensitive token string",
                         (self.report / "manifest.json").read_text())

    def test_rejects_reports_inside_git_checkout(self):
        self._add(self.repo, "studio/audio.py", "original")
        self._add(self.installed, "studio/audio.py", "original")
        self._git_add()
        with self.assertRaisesRegex(RuntimeError, "inside the Git checkout"):
            audit.make_report(self.installed, self.repo, self.repo / "PC-REPORT")
        self.assertFalse((self.repo / "PC-REPORT").exists())

    def test_ignores_untracked_git_file_and_never_modifies_installed(self):
        p = self._add(self.repo, "studio/audio.py", "version one")
        q = self._add(self.installed, "studio/audio.py", "version one")
        self._git_add()
        self._add(self.repo, "studio/untracked.py", "not committed")
        before = q.read_bytes()
        audit.make_report(self.installed, self.repo, self.report)
        self.assertEqual(before, q.read_bytes())
        self.assertNotIn("studio/untracked.py",
                         json.loads((self.report / "manifest.json").read_text())["git_sha256"])


if __name__ == "__main__":
    unittest.main()
