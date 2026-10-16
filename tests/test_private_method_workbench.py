"""Private native-method HTML review remains offline, owner-only and read-only."""
import hashlib
import html
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
spec = importlib.util.spec_from_file_location(
    "spider_private_method_workbench", ROOT / "tools/private_method_workbench.py")
tool = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = tool
spec.loader.exec_module(tool)


class PrivateWorkbenchTests(unittest.TestCase):
    def test_decorated_methods_are_extractable_without_imports(self):
        src = b"""import missing_private_module
class WebbiePanel:
    @staticmethod
    def stop_sensitive_actions():
        return '<strong>OWNER SECRET</strong>'
"""
        result = tool.definition_text(src, "WebbiePanel.stop_sensitive_actions")
        self.assertIn("@staticmethod", result)
        self.assertIn("def stop_sensitive_actions()", result)
        self.assertNotIn("import missing_private_module", result)

    def test_private_html_has_csp_and_escapes_markup(self):
        source = "def run(self):\n    return '<script>alert(1)</script>'\n"
        html_text = tool.build_html([
            ("the-web/shell/main.py", "TheWeb.open_workspace",
             source, source.replace("alert(1)", "alert(2)"), "Review navigation")])
        self.assertIn("Content-Security-Policy", html_text)
        self.assertIn("connect-src 'none'", html_text)
        self.assertIn("script-src 'none'", html_text)
        self.assertNotIn("<script>alert(1)</script>", html_text)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html_text)
        self.assertIn("DO NOT INSTALL OR UPLOAD", html_text)

    def test_rejects_unstaged_or_changed_conflicts(self):
        with tempfile.TemporaryDirectory() as root:
            home = Path(root)
            staged = home / "Stage"
            staged.mkdir(mode=0o700)
            owner = b"""class TheWeb:
    def __init__(self): pass
    def open_workspace(self): return 'private original'
"""
            candidate = b"""class TheWeb:
    def __init__(self): return 1
    def open_workspace(self): return 'new'
"""
            entries = []
            for file in tool.DESKTOP:
                for label, text in (("installed", owner), ("candidate", candidate)):
                    item = staged / label / file
                    item.parent.mkdir(parents=True, exist_ok=True)
                    item.write_bytes(text)
                    item.chmod(0o600)
                entries.append({
                    "component": file,
                    "installed_sha256": hashlib.sha256(owner).hexdigest(),
                    "candidate_sha256": hashlib.sha256(candidate).hexdigest(),
                })
            m = staged / "manifest.json"
            m.write_text(json.dumps({
                "format": "spider-native-private-merge-stage-v1",
                "focus": "desktop", "release_installable": False, "files": entries,
            }))
            m.chmod(0o600)
            out = home / "PrivateWorkbench"
            with self.assertRaises(ValueError):
                tool.prepare(staged, out, home=home)
            self.assertFalse(out.exists())
            (staged / "installed" / tool.DESKTOP[0]).write_text("tampered")
            with self.assertRaises(ValueError):
                tool.prepare(staged, out, home=home)
            self.assertFalse(out.exists())

    def test_does_not_run_or_write_to_os(self):
        code = (ROOT / "tools/private_method_workbench.py").read_text()
        for phrase in ("subprocess", "sudo ", "systemctl ",
                       "requests.", "urlopen(", "os.system(", "git push",
                       "apt install", "os.replace(", "shutil.copytree("):
            self.assertNotIn(phrase, code)
        self.assertIn("NOT INSTALLABLE.", code)


if __name__ == "__main__":
    unittest.main()
