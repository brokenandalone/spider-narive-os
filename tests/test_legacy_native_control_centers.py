"""Legacy launcher consolidation must preserve programs and independent bays."""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "spider_legacy_centers", ROOT / "the-web/shell/legacy_control_centers.py")
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class LegacyCenterIntegrationTests(unittest.TestCase):
    def test_only_three_development_control_centers_redirect(self):
        expected = {
            "spider-os-universal.desktop": ("default", "Advanced tools & tasks"),
            "spider-os-workspace-max.desktop": ("default", "Advanced tools & tasks"),
            "spider-webbie-intelligence.desktop": ("webbie", "Webbie controls"),
        }
        self.assertEqual(set(expected), set(mod.LEGACY_DESTINATIONS))
        for name, (bay, tab) in expected.items():
            item = mod.destination(name)
            self.assertEqual((item.workspace, item.tab_title), (bay, tab))
            self.assertTrue(item.message)

    def test_original_ubuntu_studio_app_entries_are_never_redirected(self):
        for name in ("ardour.desktop", "audacity.desktop", "carla.desktop",
                     "org.kde.konsole.desktop", "libreoffice-writer.desktop",
                     "spider-media-player.desktop", "studio.desktop",
                     "webbie.desktop", "kali-bay.desktop", "firefox_firefox.desktop"):
            self.assertIsNone(mod.destination(name), name)

    def test_all_legacy_operations_still_reachable_through_native_tabs(self):
        shell = (ROOT / "the-web/shell/main.py").read_text()
        max_bridge = (ROOT / "the-web/shell/workspace_max_native.py").read_text()
        webbie = (ROOT / "the-web/shell/webbie_native_operations.py").read_text()
        self.assertIn("legacy = legacy_destination(ident)", shell)
        self.assertIn("workspace_tabs.addTab(advanced, 'Advanced tools & tasks')", shell)
        self.assertIn("workspace_tabs.addTab(operations, 'Webbie controls')", shell)
        self.assertIn("catalog.run(self.workspace, self.action, self.folder, self.query)", max_bridge)
        for name in ("WebbieCognitiveDialog", "JarvisMissionCenter",
                     "WebbieUnifiedWorkflowDialog"):
            self.assertIn(name, webbie)

    def test_no_desktop_entry_deletions_or_shell_execution_in_bridge(self):
        body = (ROOT / "the-web/shell/legacy_control_centers.py").read_text()
        for prohibited in ("unlink(", "rmtree(", "subprocess", "os.system",
                           "apt remove", "launch_command"):
            self.assertNotIn(prohibited, body)


if __name__ == "__main__":
    unittest.main()
