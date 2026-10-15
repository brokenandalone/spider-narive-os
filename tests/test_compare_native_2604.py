"""Tests for privacy-respecting structural comparison of the installed native bays."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "spider_compare_native_2604", ROOT / "tools/compare-native-2604.py"
)
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class LocalReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.src = self.base / "candidate"
        self.host = self.base / "installed"
        self.src.mkdir()
        self.host.mkdir()
        (self.src / "system").mkdir()
        (self.src / "system/release_batch.py").write_text(
            "APP_FILES = ('the-web/shell/main.py', 'webbie/agent/webbie.py')\n"
        )

    def write(self, root, name, data):
        file = root / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(data)
        return file

    def test_summarizes_symbols_without_returning_private_source(self):
        local = "def existing():\n    return 'PRIVATE-OWNER-CODE'\ndef local_only():\n    pass\n"
        candidate = "def existing():\n    return 2\ndef new_only():\n    pass\n"
        summary = tool.summarize_python(local, candidate)
        self.assertEqual(summary["local_only"], ["local_only"])
        self.assertEqual(summary["candidate_only"], ["new_only"])
        self.assertEqual(summary["changed_common"], 1)
        self.assertNotIn("PRIVATE-OWNER-CODE", str(summary))

    def test_reports_customization_and_new_module(self):
        self.write(self.src, "the-web/shell/main.py", "def common(): return 2\n")
        self.write(self.host, "the-web/shell/main.py", "def common(): return 1\n")
        self.write(self.src, "webbie/agent/webbie.py", "def newly_added(): pass\n")
        summary = tool.inspect(self.src, self.host)
        self.assertEqual(summary["changed"], ["the-web/shell/main.py"])
        self.assertEqual(summary["missing"], ["webbie/agent/webbie.py"])

    def test_does_not_follow_symlink_to_unrelated_file(self):
        self.write(self.src, "the-web/shell/main.py", "def common(): return 2\n")
        private = self.base / "private.py"
        private.write_text("def password(): return 'SECRET'\n")
        target = self.host / "the-web/shell/main.py"
        target.parent.mkdir(parents=True)
        target.symlink_to(private)
        self.write(self.src, "webbie/agent/webbie.py", "def safe(): pass\n")
        summary = tool.inspect(self.src, self.host)
        self.assertEqual(summary["skipped"], [
            ("the-web/shell/main.py", "installed symlink")
        ])
        self.assertEqual(summary["missing"], ["webbie/agent/webbie.py"])


if __name__ == "__main__":
    unittest.main()
