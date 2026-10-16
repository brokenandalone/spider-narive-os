#!/usr/bin/env python3
"""Tests for source-versus-backup report classification, with no PC access."""
import importlib.util
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import sys
import tempfile
import unittest

TOOL = Path(__file__).resolve().parents[1] / "tools" / "installed_truth_triage.py"
spec = importlib.util.spec_from_file_location("installed_triage", TOOL)
triage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(triage)


class TriageTests(unittest.TestCase):
    def test_recovery_directories_and_normal_source(self):
        self.assertEqual(triage.category(
            "upgrade-backups/old/webbie/agent/webbie.py", "installed_only"
        ), "recovery_likely")
        self.assertEqual(triage.category(
            "webbie.backup-20261003-040101/agent/webbie.py", "installed_only"
        ), "recovery_likely")
        self.assertEqual(triage.category(
            "webbie/agent/webbie.py", "installed_only"
        ), "review_source")
        self.assertEqual(triage.category(
            "webbie/brain/brain.py", "installed_only"
        ), "review_source")

    def test_runtime_receipts_and_source_build_files(self):
        self.assertEqual(triage.category(
            "the-web/install-receipt.json", "installed_only"
        ), "runtime_or_sensitive_review")
        self.assertEqual(triage.category(
            "tests/test_webbie.py", "repo_only"
        ), "development_only")
        self.assertEqual(triage.category(
            ".github/workflows/source-checks.yml", "repo_only"
        ), "development_only")
        self.assertEqual(triage.category(
            "studio/main.py", "different"
        ), "review_source")

    def test_path_traversal_is_not_promoted_to_source(self):
        for path in ("../secrets.py", "/absolute/path.py", "foo/../secrets.py"):
            self.assertEqual(triage.category(path, "installed_only"), "unsafe_name")

    def test_end_to_end_existing_manifest_only(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "manifest.json"
            p.write_text(json.dumps({
                "repo_commit": "fixture",
                "groups": {
                    "identical": ["webbie/voice/output.py"],
                    "different": ["webbie/agent/webbie.py"],
                    "installed_only": [
                        "upgrade-backups/old/studio/main.py",
                        "webbie/agent/webbie_ai_worker.py",
                    ],
                    "repo_only": ["tests/test_foo.py"],
                },
            }))
            old_argv = sys.argv[:]
            sys.argv = ["triage", "--manifest", str(p), "--limit", "3"]
            try:
                output = io.StringIO()
                with redirect_stdout(output):
                    status = triage.main()
            finally:
                sys.argv = old_argv
            self.assertEqual(status, 0)
            self.assertIn("different: 1 paths", output.getvalue())
            self.assertIn("recovery_likely=1", output.getvalue())
            self.assertIn("webbie/agent/webbie_ai_worker.py", output.getvalue())


if __name__ == "__main__":
    unittest.main()
