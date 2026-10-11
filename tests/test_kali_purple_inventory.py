"""Kali Purple binary inventory: mocked real guest shell, no service startup."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MANAGER = ROOT / "kali-bay/bin/kali-bay"
UI = ROOT / "kali-bay/ui/kali_bay.py"


class PurpleCliTests(unittest.TestCase):
    def run_inventory(self, state="running", exists=True):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            stubs = root / "mock"
            stubs.mkdir()
            calls = root / "calls"
            exe = stubs / "podman"
            exe.write_text("""#!/bin/sh
printf '%s\\n' "$1 $2" >> "$MOCK_CALLS"
case "$1 $2" in
 "container exists") [ "$MOCK_EXISTS" = yes ]; exit $?;;
 "inspect --format")
   if [ "$MOCK_STATE" = running ]; then echo true; exit 0; fi
   if [ "$MOCK_STATE" = stopped ]; then echo false; exit 0; fi
   exit 7;;
 "exec --user")
   while [ "$1" != sh ]; do shift; done
   exec "$@" ;;
esac
exit 65
""", encoding="utf-8")
            exe.chmod(0o755)
            distro = stubs / "distrobox"
            distro.write_text(
                "#!/bin/sh\nprintf 'UNEXPECTED distrobox\\n' >> \"$MOCK_CALLS\"\nexit 71\n"
            )
            distro.chmod(0o755)
            env = dict(
                os.environ, HOME=folder,
                PATH=str(stubs) + os.pathsep + os.environ["PATH"],
                MOCK_STATE=state, MOCK_EXISTS="yes" if exists else "no",
                MOCK_CALLS=str(calls),
            )
            result = subprocess.run(
                ["bash", str(MANAGER), "purple-json"],
                capture_output=True, text=True, env=env, timeout=12,
            )
            data = json.loads(result.stdout) if result.returncode == 0 else {}
            directories_created = (root / ".local").exists()
            return result, data, calls.read_text() if calls.exists() else "", directories_created

    def test_running_inventory_executes_fixed_readonly_guest_script(self):
        result, data, calls, writes = self.run_inventory()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(data["state"], "running")
        self.assertEqual(
            set(data["tools"]),
            {"suricata", "zeek", "yara", "lynis", "clamscan",
             "wireshark", "tcpdump", "tshark", "auditctl"},
        )
        self.assertTrue(all(type(v) is bool for v in data["tools"].values()))
        self.assertIn("exec --user", calls)
        self.assertNotIn("start", calls)
        self.assertFalse(writes)

    def test_missing_and_stopped_do_not_execute_or_create(self):
        for state, exists, expected in (
            ("running", False, "missing"),
            ("stopped", True, "stopped"),
            ("unknown", True, "unknown"),
        ):
            with self.subTest(expected=expected):
                result, data, calls, writes = self.run_inventory(state, exists)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(data["state"], expected)
                self.assertEqual(data["tools"], {})
                self.assertNotIn("exec --user", calls)
                self.assertNotIn("start", calls)
                self.assertFalse(writes)

    def test_no_repair_or_background_sensor_start_in_cli(self):
        source = MANAGER.read_text()
        body = source.split("purple_status_json() {", 1)[1].split("\n\ninfo() {", 1)[0]
        self.assertNotIn("apt-get", body)
        self.assertNotIn("distrobox enter", body)
        self.assertNotIn("systemctl start", body)
        self.assertNotIn("podman start", body)


class PurpleQtAndWebbieTests(unittest.TestCase):
    def test_gui_has_readonly_purple_summary(self):
        script = r"""
import importlib.util, json
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch
from PyQt5.QtWidgets import QApplication, QPushButton
root = Path(__import__("sys").argv[1])
spec = importlib.util.spec_from_file_location("purple_ui", root/"kali-bay/ui/kali_bay.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
a = QApplication([])
with patch.object(mod.subprocess, "run", return_value=CompletedProcess([], 0, "missing", "")):
    win = mod.KaliBayWindow()
    assert win.purple_status.objectName() == "kaliPurpleInventory"
    assert win.findChild(QPushButton, "kaliPurpleCheck")
    data = {"state":"running","tools":{"suricata":True, "yara":True, "zeek":False}}
    with patch.object(mod.subprocess, "run",
                      return_value=CompletedProcess([], 0, json.dumps(data), "")):
        win.check_purple_defense_tools()
    summary = win.purple_status.text()
    assert "suricata" in summary and "yara" in summary
    assert "NOT started" in summary
    win.close()
"""
        result = subprocess.run(
            [sys.executable, "-c", script, str(ROOT)],
            cwd=ROOT, env=dict(os.environ, QT_QPA_PLATFORM="offscreen"),
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_webbie_readonly_purple_intent(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "purple_assistant", ROOT / "webbie/agent/kali_assistant.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertEqual(
            mod.parse_request("check Kali Purple tools"), ("purple_tools", None)
        )
        self.assertIsNone(mod.parse_request("check Kali Purple tools; start suricata"))
        data = {
            "state": "running",
            "tools": {"suricata": True, "yara": True, "zeek": False},
        }
        with tempfile.TemporaryDirectory() as folder:
            manager = Path(folder) / "kali-bay"
            manager.write_text("#!/bin/sh\n", encoding="utf-8")
            manager.chmod(0o700)
            with patch.object(
                mod.subprocess, "run",
                return_value=subprocess.CompletedProcess(
                    [], 0, json.dumps(data), ""
                ),
            ) as runner, patch.object(mod.subprocess, "Popen") as spawn:
                reply = mod.handle_kali_request(
                    "check Kali Purple tools", manager=manager,
                )
                self.assertIn("suricata", reply)
                self.assertIn("2 of 9", reply)
                self.assertIn("doesn't mean", reply)
                runner.assert_called_once()
                self.assertEqual(
                    runner.call_args.args[0], [str(manager), "purple-json"]
                )
                spawn.assert_not_called()


if __name__ == "__main__":
    unittest.main()
