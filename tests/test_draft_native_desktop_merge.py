"""Private desktop preservation overlay: retain local Webbie methods, block install."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
spec = importlib.util.spec_from_file_location(
    "spider_noninstallable_desktop_draft",
    ROOT / "tools/draft_native_desktop_merge.py")
tool = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = tool
spec.loader.exec_module(tool)


class DesktopDraftTests(unittest.TestCase):
    def test_preserves_two_owner_only_webbie_methods_but_marks_shared_unresolved(self):
        local = b'''from webbie_local_workflow import open_original
class WebbieCognitiveDialog:
    def __init__(self, parent):
        self.parent = parent
    def open_workflow(self):
        return "OWNER APPROVED FLOW"
    def offer_workflow(self, text):
        return open_original(text)
    def open_workflows(self):
        return self.offer_workflow("approved")
'''
        candidate = b'''from nova_controls import assisted
class WebbieCognitiveDialog:
    def __init__(self, parent, callback=None):
        self.callback = callback
    def open_workflow(self):
        return assisted(self.callback)
    def inspect_readiness(self):
        return "read only"
'''
        draft, result = tool.preservation_overlay(local, candidate)
        s = draft.decode()
        self.assertIn("from webbie_local_workflow import open_original", s)
        self.assertIn("def offer_workflow(", s)
        self.assertIn("def open_workflows(", s)
        self.assertIn("def inspect_readiness(", s)
        self.assertIn("return assisted(self.callback)", s)
        self.assertEqual(result["owner_only_members_added"], [
            "WebbieCognitiveDialog.offer_workflow",
            "WebbieCognitiveDialog.open_workflows"])
        self.assertIn("WebbieCognitiveDialog.__init__", result["unresolved_shared"])
        self.assertIn("WebbieCognitiveDialog.open_workflow", result["unresolved_shared"])
        self.assertEqual(result["owner_only_imports_added"], 1)
        self.assertFalse(result["install_allowed"])
        self.assertNotIn("OWNER APPROVED FLOW", str(result))
        self.assertNotIn("OWNER APPROVED FLOW", json.dumps(result))

    def test_decorators_and_owner_top_level_function_restored(self):
        old = b'''from webbie_local import allow
class Old:
    @staticmethod
    def only_here(flag):
        return allow(flag)

def original_old():
    return 13
'''
        new = b'''class Old:
    def new_thing(self):
        return 25
'''
        result, info = tool.preservation_overlay(old, new)
        content = result.decode()
        self.assertIn("@staticmethod\n    def only_here(", content)
        self.assertIn("def original_old():", content)
        self.assertIn("def new_thing(", content)
        self.assertEqual(info["owner_only_imports_added"], 1)
        self.assertFalse(info["install_allowed"])

    def test_private_overlay_refuses_symlink_and_original_remains_unchanged(self):
        with tempfile.TemporaryDirectory() as base:
            home = Path(base)
            stage = home / "private-original-pairs"
            stage.mkdir(mode=0o700)
            installed = b"class Webbie:\n    def existing(self):\n        return 'MY HOST'\n"
            candidate = b"class Webbie:\n    def existing(self):\n        return 'YOUR DRAFT'\n"
            entries = []
            for name in tool.DESKTOP:
                for scope, content in (("installed", installed), ("candidate", candidate)):
                    source = stage / scope / name
                    source.parent.mkdir(parents=True, exist_ok=True)
                    source.write_bytes(content)
                    source.chmod(0o600)
                entries.append({
                    "component": name,
                    "installed_sha256": hashlib.sha256(installed).hexdigest(),
                    "candidate_sha256": hashlib.sha256(candidate).hexdigest(),
                })
            manifest = stage / "manifest.json"
            manifest.write_text(json.dumps({
                "format": "spider-native-private-merge-stage-v1",
                "focus": "desktop",
                "release_installable": False,
                "files": entries,
            }), encoding="utf-8")
            manifest.chmod(0o600)
            output = home / "private-review-output"
            report = tool.draft(stage, output, home=home)
            self.assertEqual(len(report["files"]), 5)
            self.assertFalse(report["release_installable"])
            self.assertFalse(report["safe_to_overwrite"])
            self.assertEqual(output.stat().st_mode & 0o777, 0o700)
            for name in tool.DESKTOP:
                path = output / "draft" / name
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                self.assertEqual((stage / "installed" / name).read_bytes(), installed)
                self.assertEqual((stage / "candidate" / name).read_bytes(), candidate)
                self.assertEqual(report["files"][0]["unresolved_shared"], ["Webbie.existing"])
            with self.assertRaises(ValueError):
                tool.draft(stage, output, home=home)
            target = stage / "installed" / tool.DESKTOP[0]
            target.unlink()
            secret = home / "secret.py"
            secret.write_text("not staged", encoding="utf-8")
            target.symlink_to(secret)
            with self.assertRaises(ValueError):
                tool.draft(stage, home / "new-stage", home=home)
            self.assertFalse((home / "new-stage").exists())

    def test_no_install_services_or_network(self):
        source = (ROOT / "tools/draft_native_desktop_merge.py").read_text()
        for forbidden in ("os.system(", "sudo ", "subprocess.Popen",
                          "requests.", "urlopen(", "git push",
                          "systemctl ", "apply(items", "apt install"):
            self.assertNotIn(forbidden, source)
        self.assertIn("STRICT INSTALL GATE REMAINS BLOCKED.", source)


if __name__ == "__main__":
    unittest.main()
