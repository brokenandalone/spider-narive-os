"""Verify that the original native applications received the MAX tools directly."""
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CASES = {
    "studio/main.py": ("NativeWorkspaceTools('studio', self)", "self.tool_tabs.addTab(self.native_max_tools"),
    "author/main.py": ("NativeWorkspaceTools('author', self)", "tabs.addTab(self.native_max_tools"),
    "study/study.py": ("NativeWorkspaceTools('study', self)", "self.tabs.addTab(self.native_max_tools"),
    "kali-bay/ui/kali_bay.py": ("NativeWorkspaceTools('kali-bay', self)", "self.security_tabs.addTab(self.native_max_tools"),
}


class ActualNativeApplicationIntegration(unittest.TestCase):
    def test_native_windows_compile(self):
        for name in CASES:
            with self.subTest(name=name):
                text = (ROOT / name).read_text("utf-8")
                compile(text, name, "exec")

    def test_each_native_app_hosts_its_tools(self):
        for name, anchors in CASES.items():
            with self.subTest(name=name):
                text = (ROOT / name).read_text("utf-8")
                self.assertIn("from workspace_max_native import NativeWorkspaceTools", text)
                for anchor in anchors:
                    self.assertIn(anchor, text)

    def test_existing_functions_still_present(self):
        source = {
            name: (ROOT / name).read_text("utf-8") for name in CASES
        }
        self.assertIn("def launch_music(", source["studio/main.py"])
        self.assertIn("def autosave(", source["author/main.py"])
        self.assertIn("def load_courses(", source["study/study.py"])
        self.assertIn("def build_webbie_dock(", source["kali-bay/ui/kali_bay.py"])

    def test_no_launcher_commands_added(self):
        for name in CASES:
            text = (ROOT / name).read_text("utf-8")
            self.assertNotIn("exec spider-os-workspace-max", text)


if __name__ == "__main__":
    unittest.main()
