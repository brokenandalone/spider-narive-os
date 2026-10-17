"""Legacy developer shortcut audit cannot modify existing .desktop apps."""
import importlib.util
import sys
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "spider_shortcut_audit", ROOT / "tools/audit_legacy_shortcuts.py")
tool = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = tool
spec.loader.exec_module(tool)


class RedundantLauncherAuditTests(unittest.TestCase):
    def test_finds_three_developer_shortcuts_but_leaves_all_other_apps(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            candidates = {
                "spider-os-universal.desktop": "Spider OS Universal Control Center v3 (Private)",
                "spider-os-workspace-max.desktop": "Spider OS Workspace MAX Control Center v4 (Private)",
                "spider-webbie-intelligence.desktop": "Webbie Intelligence Center (Private)",
                "ardour.desktop": "Ardour",
                "blender.desktop": "Blender",
            }
            for file, name in candidates.items():
                (directory / file).write_text(
                    "[Desktop Entry]\nType=Application\nName=" + name +
                    "\nExec=existing-program\n", encoding="utf-8")
            original = {file: (directory / file).read_bytes()
                        for file in candidates}
            items = tool.inspect_entries(directory)
            self.assertEqual(len(items), 3)
            self.assertEqual({item["filename"] for item in items},
                             set(tool.KNOWN))
            self.assertEqual({file: (directory / file).read_bytes()
                              for file in candidates}, original)

    def test_symlinked_shortcut_is_not_followed(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            private = directory / "private-secret.txt"
            private.write_text("NOT A DESKTOP ENTRY")
            link = directory / "spider-os-universal.desktop"
            link.symlink_to(private)
            self.assertEqual(tool.inspect_entries(directory), [])

    def test_distinguishes_desktop_icons_from_system_menu(self):
        self.assertEqual(len(tool.KNOWN), 3)
        source = (ROOT / "tools/audit_legacy_shortcuts.py").read_text()
        for forbidden in ("unlink(", "rmtree(", "os.remove(",
                          "subprocess", "os.system(", "apt purge", "chmod("):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
