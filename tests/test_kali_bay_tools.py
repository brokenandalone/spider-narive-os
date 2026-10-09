"""Safe Kali Bay tool discovery and launcher regressions.

These tests use fake Podman/Distrobox; they never install Kali or run tools.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
KALI = ROOT / "kali-bay/bin/kali-bay"
UI = ROOT / "kali-bay/ui/kali_bay.py"


class KaliToolLauncherTests(unittest.TestCase):
    def run_action(self, action, tool, running=True, installed=True):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            mock = work / "bin"
            mock.mkdir()
            calls = work / "calls"
            podman = mock / "podman"
            podman.write_text("""#!/bin/sh
printf 'podman %s\\n' "$*" >> "$MOCK_CALLS"
case "$1 $2" in
  "container exists") exit 0;;
  "inspect --format") if [ "$MOCK_RUNNING" = "1" ]; then echo true; else echo false; fi; exit 0;;
  "exec --user") if [ "$MOCK_INSTALLED" = "1" ]; then exit 0; else exit 3; fi;;
  *) exit 71;;
esac
""")
            podman.chmod(0o755)
            for name in ("distrobox", "konsole"):
                stub = mock / name
                stub.write_text(
                    "#!/bin/sh\nprintf '" + name +
                    " %s\\n' \"$*\" >> \"$MOCK_CALLS\"\nexit 0\n"
                )
                stub.chmod(0o755)
            env = dict(
                os.environ,
                HOME=tmp,
                PATH=str(mock) + os.pathsep + os.environ.get("PATH", ""),
                MOCK_CALLS=str(calls),
                MOCK_RUNNING="1" if running else "0",
                MOCK_INSTALLED="1" if installed else "0",
            )
            result = subprocess.run(
                ["bash", str(KALI), action, tool],
                env=env, capture_output=True, text=True, timeout=10,
            )
            return result, calls.read_text() if calls.exists() else ""

    def test_allowlisted_gui_detected_without_distrobox(self):
        result, calls = self.run_action("tool-check", "wireshark")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "ready")
        self.assertIn("podman exec", calls)
        self.assertNotIn("distrobox", calls)
        self.assertNotIn("konsole", calls)

    def test_unknown_tool_rejected_before_container_contact(self):
        for bad in ("bash", "/bin/sh", "wireshark;id", "../evil"):
            result, calls = self.run_action("tool", bad)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Unknown tool", result.stderr)
            self.assertEqual(calls, "")

    def test_stopped_container_does_not_start_or_initialize(self):
        result, calls = self.run_action("tool-check", "wireshark", running=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("stopped", result.stderr)
        self.assertNotIn("distrobox", calls)
        self.assertNotIn("podman start", calls)
        self.assertNotIn("podman exec", calls)

    def test_missing_tool_does_not_launch(self):
        result, calls = self.run_action("tool", "zaproxy", installed=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not installed", result.stderr)
        self.assertNotIn("distrobox", calls)
        self.assertNotIn("konsole", calls)

    def test_gui_launch_has_no_arbitrary_arguments(self):
        result, calls = self.run_action("tool", "wireshark")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("distrobox enter --name kali-bay -- wireshark", calls)
        self.assertNotIn("sudo ", calls)
        self.assertNotIn("apt-get", calls)

    def test_cli_button_opens_workbench_without_running_scan(self):
        result, calls = self.run_action("tool", "nmap")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("konsole --hold -e distrobox enter", calls)
        self.assertNotIn("distrobox enter --name kali-bay -- nmap", calls)
        self.assertNotIn("sudo ", calls)

    def test_both_security_tabs_and_tool_actions_in_desktop_source(self):
        source = UI.read_text()
        self.assertIn("OFFENSIVE_CATEGORIES", source)
        self.assertIn("PURPLE_CATEGORIES", source)
        self.assertIn("PURPLE DEFENSE", source)
        self.assertIn("def open_tool(self, tool_id)", source)
        self.assertIn('"tool-check", tool_id', source)
        self.assertIn('"tool", tool_id', source)

    def test_qt_workspace_has_both_security_tabs(self):
        # An isolated child process keeps Qt's global singleton out of
        # unrelated source-check tests and needs no real Kali installation.
        import sys
        script = """
import importlib.util
from pathlib import Path
from PyQt5.QtWidgets import QApplication
source = Path(__import__('sys').argv[1])
spec = importlib.util.spec_from_file_location('kali_bay_under_test', source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
app = QApplication([])
window = module.KaliBayWindow()
assert window.security_tabs.count() == 2
assert window.security_tabs.tabText(0) == 'OFFENSIVE'
assert window.security_tabs.tabText(1) == 'PURPLE DEFENSE'
assert 'DIRECT SECURITY TOOL LAUNCHERS' in [
    widget.text()
    for widget in window.findChildren(module.QLabel)
]
window.close()
"""
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
        result = subprocess.run(
            [sys.executable, "-c", script, str(UI)],
            cwd=ROOT, env=env, capture_output=True,
            text=True, timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
