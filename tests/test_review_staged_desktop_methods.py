"""Private AST desktop review only emits identifiers, never project code."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "spider_review_staged_methods",
    ROOT / "tools/review_staged_desktop_methods.py")
tool = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = tool
spec.loader.exec_module(tool)


class MethodReviewTests(unittest.TestCase):
    def test_detects_changed_methods_with_same_top_level_class(self):
        local = b"""import os
DEFAULT = 'PRIVATE-OWNER-SECRET'
class TheWeb:
    def restore_state(self):
        return 'LOCAL ONLY, PRESERVE ME'
    def open_workspace(self, name):
        return 'LOCAL WORKSPACE PATH'
"""
        candidate = b"""import os
from home_dashboard import SpiderHomeDashboard
DEFAULT = 'Candidate setting'
class TheWeb:
    def restore_state(self):
        return 'CANDIDATE STATE'
    def open_workspace(self, name):
        return 'CANDIDATE WORKSPACE'
    def new_toolbar(self):
        return True
"""
        result = tool.structural_diff(local, candidate, "the-web/shell/main.py")
        self.assertEqual(result["local_only_definitions"], [])
        self.assertEqual(result["candidate_only_definitions"], ["TheWeb.new_toolbar"])
        self.assertEqual(result["changed_shared_definitions"],
                         ["TheWeb.open_workspace", "TheWeb.restore_state"])
        self.assertEqual(result["module_binding_changes"], 1)
        self.assertEqual(result["candidate_only_import_count"], 1)
        self.assertFalse(result["safe_to_overwrite"])
        self.assertNotIn("PRIVATE-OWNER-SECRET", str(result))
        self.assertNotIn("LOCAL ONLY, PRESERVE ME", str(result))

    def test_separates_method_arguments_from_body_changes(self):
        first = b"class Webbie:\n    def listen(self, name):\n        return 1\n"
        second = b"class Webbie:\n    def listen(self, name, verified=False):\n        return 2\n"
        result = tool.structural_diff(first, second, "webbie.py")
        self.assertIn("Webbie.listen", result["signature_or_decorator_changes"])
        self.assertIn("Webbie.listen", result["changed_shared_definitions"])

    def test_private_manifest_hash_rejection_and_stage_permission(self):
        with tempfile.TemporaryDirectory() as folder:
            stage = Path(folder) / "desktop-private"
            stage.mkdir(mode=0o700)
            original = b"def safe():\n    return 'LOCAL HIDDEN CODE'\n"
            candidate = b"def safe():\n    return 'NEW CODE'\n"
            entries = []
            for relative in tool.DESKTOP:
                for kind, payload in (("installed", original),
                                      ("candidate", candidate)):
                    path = stage / kind / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(payload)
                    path.chmod(0o600)
                entries.append({
                    "component": relative,
                    "installed_sha256": hashlib.sha256(original).hexdigest(),
                    "candidate_sha256": hashlib.sha256(candidate).hexdigest(),
                })
            manifest = stage / "manifest.json"
            manifest.write_text(json.dumps({
                "format": tool.FORMAT, "focus": "desktop",
                "release_installable": False, "files": entries,
            }))
            manifest.chmod(0o600)
            outcome = tool.inspect_stage(stage)
            self.assertEqual(len(outcome), 5)
            self.assertNotIn("LOCAL HIDDEN CODE", str(outcome))
            target = stage / "installed" / tool.DESKTOP[0]
            target.write_bytes(b"tampered")
            with self.assertRaises(ValueError):
                tool.inspect_stage(stage)
            target.write_bytes(original)
            stage.chmod(0o755)
            with self.assertRaises(ValueError):
                tool.inspect_stage(stage)

    def test_no_execution_merging_writing_or_network(self):
        source = (ROOT / "tools/review_staged_desktop_methods.py").read_text()
        for forbidden in ("subprocess", "requests.", "urlopen(",
                          "open(\"w", "write_bytes(", "write_text(",
                          "os.replace(", "os.system(", "pip install",
                          "apply(", "git push", "sudo "):
            self.assertNotIn(forbidden, source)
        self.assertIn("Nothing installed, copied, committed, executed or modified.",
                      source)


if __name__ == "__main__":
    unittest.main()
