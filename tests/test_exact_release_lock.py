"""Regression tests for exact release SHA and local source immutability."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("spider_installer_pinned_test", ROOT/"system/release_batch.py")
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


class ExactReleaseLockTests(unittest.TestCase):
    def setUp(self):
        self.good = "a"*40
        self.root = Path("/fixture/not-written")
        self.calls = []

    def mock_runner(self, outputs):
        def runner(argv, **kwargs):
            self.calls.append(tuple(argv))
            return outputs.pop(0)
        return runner

    def result(self, text, code=0):
        return subprocess.CompletedProcess([], code, stdout=text, stderr="")

    def test_exact_clean_sha_passes(self):
        runner = self.mock_runner([self.result(self.good+"\n"), self.result("")])
        self.assertTrue(module.require_exact_candidate_commit(self.root, self.good, runner))
        self.assertEqual(len(self.calls), 2)

    def test_green_ci_from_previous_commit_must_not_authorize(self):
        runner = self.mock_runner([self.result("b"*40+"\n"), self.result("")])
        with self.assertRaisesRegex(RuntimeError, "SHA differs"):
            module.require_exact_candidate_commit(self.root, self.good, runner)

    def test_locally_modified_source_cannot_be_installed(self):
        runner = self.mock_runner([self.result(self.good+"\n"), self.result(" M webbie/brain/brain.py\n")])
        with self.assertRaisesRegex(RuntimeError, "modified tracked files"):
            module.require_exact_candidate_commit(self.root, self.good, runner)

    def test_unknown_sha_cannot_be_installed(self):
        with self.assertRaisesRegex(RuntimeError, "Missing or invalid"):
            module.require_exact_candidate_commit(self.root, "", self.mock_runner([]))

    def test_unavailable_git_check_blocks(self):
        runner = self.mock_runner([self.result("",code=128), self.result("")])
        with self.assertRaisesRegex(RuntimeError, "SHA differs"):
            module.require_exact_candidate_commit(self.root, self.good, runner)

    def test_installer_actually_calls_both_permanent_gates(self):
        src = (ROOT/"system/release_batch.py").read_text()
        self.assertIn("require_exact_candidate_commit(source_root, plan.get('candidate_commit'))", src)
        self.assertIn("require_known_good_pc(source_root)", src)
        self.assertIn("daily_install_guard(backup_root)", src)


if __name__ == "__main__":
    unittest.main()
