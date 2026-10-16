#!/usr/bin/env python3
"""No-PC regression coverage for staging only into a disposable Git checkout."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location("reconcile_stage", TOOLS / "stage_installed_source.py")
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)


class StageInstalledSourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.repo = base / "checkout"
        self.pc = base / "installed"
        self.repo.mkdir()
        self.pc.mkdir()
        subprocess.run(["git", "init", "-q", "-b", stage.BRANCH, str(self.repo)], check=True)
        for field, value in (("user.name", "Regression Test"), ("user.email", "test@example.invalid")):
            subprocess.run(["git", "-C", str(self.repo), "config", field, value], check=True)
        self.put(self.repo, "webbie/agent/webbie.py", "print('git old')\n")
        self.put(self.pc, "webbie/agent/webbie.py", "print('pc current')\n")
        self.put(self.pc, "webbie/agent/webbie_ai_worker.py", "def reply():\n    return 'ok'\n")
        self.put(self.pc, "webbie/vendor/numpy/__init__.py", "vendor")
        subprocess.run(["git", "-C", str(self.repo), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.repo), "commit", "-qm", "base"], check=True)
        self.manifest = {
            "groups": {
                "different": ["webbie/agent/webbie.py"],
                "installed_only": [
                    "webbie/agent/webbie_ai_worker.py",
                    "webbie/vendor/numpy/__init__.py",
                ],
            },
            "installed_sha256": {
                "webbie/agent/webbie.py": {
                    "sha256": stage.sha((self.pc / "webbie/agent/webbie.py").read_bytes())},
                "webbie/agent/webbie_ai_worker.py": {
                    "sha256": stage.sha((self.pc / "webbie/agent/webbie_ai_worker.py").read_bytes())},
            },
            "git_sha256": {
                "webbie/agent/webbie.py": {
                    "sha256": stage.sha((self.repo / "webbie/agent/webbie.py").read_bytes())},
            },
        }

    def put(self, base, name, content):
        path = base / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_select_only_owner_code_and_ignore_vendor(self):
        changed, unique = stage.select_paths(self.manifest)
        self.assertEqual(changed, ["webbie/agent/webbie.py"])
        self.assertEqual(unique, ["webbie/agent/webbie_ai_worker.py"])

    def test_stages_only_git_checkout_and_never_installed(self):
        stage.check_git(self.repo)
        entries = stage.prepare(self.repo, self.pc, self.manifest)
        before = (self.pc / "webbie/agent/webbie.py").read_bytes()
        stage.install_checkout_only(self.repo, entries)
        self.assertEqual((self.repo / "webbie/agent/webbie.py").read_text(),
                         "print('pc current')\n")
        self.assertEqual((self.repo / "webbie/agent/webbie_ai_worker.py").read_text(),
                         "def reply():\n    return 'ok'\n")
        self.assertEqual((self.pc / "webbie/agent/webbie.py").read_bytes(), before)
        self.assertFalse((self.repo / "webbie/vendor/numpy/__init__.py").exists())
        with self.assertRaisesRegex(ValueError, "not clean"):
            stage.check_git(self.repo)

    def test_stale_modified_source_blocks_all_changes(self):
        self.put(self.pc, "webbie/agent/webbie.py", "print('changed since audit')\n")
        with self.assertRaisesRegex(ValueError, "after original audit"):
            stage.prepare(self.repo, self.pc, self.manifest)
        self.assertFalse((self.repo / "webbie/agent/webbie_ai_worker.py").exists())

    def test_git_checkout_change_blocks_all_changes(self):
        self.put(self.repo, "webbie/agent/webbie.py", "print('new branch code')\n")
        with self.assertRaisesRegex(ValueError, "not clean"):
            stage.check_git(self.repo)

    def test_secret_and_malformed_python_refused(self):
        with self.assertRaisesRegex(ValueError, "credential"):
            stage.validate_source("webbie/agent/x.py",
                                  b"password='ThisIsNotAnAppropriateSecretValue'\n")
        with self.assertRaisesRegex(ValueError, "Python syntax"):
            stage.validate_source("webbie/agent/x.py", b"def invalid(\n")

    def test_invalid_path_and_branch_refused(self):
        with self.assertRaises(ValueError):
            stage.checked_rel("../outside.py")
        with self.assertRaises(ValueError):
            stage.checked_rel("/etc/passwd")
        self.manifest["groups"]["different"].append("../outside.py")
        with self.assertRaises(ValueError):
            stage.select_paths(self.manifest)


if __name__ == "__main__":
    unittest.main()
