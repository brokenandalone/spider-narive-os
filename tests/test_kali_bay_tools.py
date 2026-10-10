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

    def test_kali_package_workbench_opens_interactive_shell_without_apt(self):
        result, calls = self.run_action("packages", "")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("konsole --hold -e distrobox enter --name kali-bay -- bash", calls)
        self.assertNotIn("apt-get install", calls)
        self.assertNotIn("podman exec", calls)

    def test_kali_installed_package_inventory_is_readonly(self):
        result, calls = self.run_action("inventory", "")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("podman exec --user 0 --tty=false kali-bay", calls)
        self.assertNotIn("distrobox", calls)
        self.assertNotIn("podman start", calls)

    def test_stopped_inventory_must_not_start_kali(self):
        result, calls = self.run_action("inventory", "", running=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("stopped", result.stderr)
        self.assertNotIn("podman exec", calls)
        self.assertNotIn("distrobox", calls)

    def test_app_ids_reject_shell_fragments_before_container_access(self):
        for bad in ("../wireshark.desktop", "/etc/passwd", "tool;id.desktop",
                    "tool.desktop --help", "tool$(id).desktop", "not_desktop"):
            result, calls = self.run_action("app-open", bad)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Invalid Kali desktop application", result.stderr)
            self.assertEqual(calls, "")

    def test_kali_app_preflight_does_not_start_container(self):
        result, calls = self.run_action(
            "app-check", "wireshark.desktop", running=False
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("stopped", result.stderr)
        self.assertNotIn("podman exec", calls)
        self.assertNotIn("distrobox", calls)

    def test_kali_app_click_launches_fixed_guest_desktop_file(self):
        result, calls = self.run_action("app-open", "wireshark.desktop")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "distrobox enter --name kali-bay -- gio launch "
            "/usr/share/applications/wireshark.desktop", calls
        )
        self.assertNotIn("sudo ", calls)
        self.assertNotIn("apt-get", calls)

    def test_kali_app_catalog_is_read_only(self):
        result, calls = self.run_action("apps-json", "")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("podman exec --user 0 --tty=false --interactive", calls)
        self.assertNotIn("distrobox", calls)
        self.assertNotIn("podman start", calls)

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

    def test_qt_workspace_has_hybrid_desktop_and_security_tabs(self):
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
assert window.security_tabs.count() == 3
assert window.security_tabs.tabText(0) == 'DESKTOP HUB'
assert window.security_tabs.tabText(1) == 'OFFENSIVE'
assert window.security_tabs.tabText(2) == 'PURPLE DEFENSE'
assert window.desktop_list.count() == len(module.DESKTOP_TOOL_MENU)
from PyQt5.QtWidgets import QPushButton
buttons = [b.text() for b in window.findChildren(QPushButton)]
assert 'KALI PACKAGE MANAGER' in buttons
assert 'INSTALLED KALI PACKAGES' in buttons
assert 'LOAD ALL INSTALLED KALI APPS' in buttons
from unittest.mock import patch
from subprocess import CompletedProcess
import json
payload = {"applications": [
    {"id": "real-kali.desktop", "name": "Actual Kali App",
     "category": "X-Kali-Tools", "description": "Installed in Kali"},
    {"id": "../../host.desktop", "name": "Unsafe", "category": "Other"},
]}
with patch.object(module.subprocess, "run", return_value=CompletedProcess(
    [], 0, json.dumps(payload), ""
)) as read, patch.object(module.subprocess, "Popen") as start:
    window.load_installed_desktop_apps()
    assert read.call_args.args[0][-1] == "apps-json"
    assert window.desktop_list.count() == len(module.DESKTOP_TOOL_MENU) + 1
    assert window.desktop_apps_status.text().startswith("1 installed")
    start.assert_not_called()
window.desktop_category.setCurrentText("X-Kali-Tools")
assert window.desktop_list.count() == 1
selected = window.desktop_list.currentItem()
assert selected.data(module.Qt.UserRole) == ("app", "real-kali.desktop")
window.desktop_category.setCurrentText("All categories")
window.desktop_search.setText('Wireshark')
assert window.desktop_list.count() == 1
assert window.desktop_list.item(0).data(module.Qt.UserRole) == 'wireshark'
window.desktop_search.clear()
window.desktop_category.setCurrentText('Detection')
assert window.desktop_list.count() == 2
window.desktop_category.setCurrentText('All categories')
assert window.desktop_list.count() == len(module.DESKTOP_TOOL_MENU) + 1
window.security_tabs.setCurrentIndex(2)
assert window.security_tabs.currentIndex() == 2
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
