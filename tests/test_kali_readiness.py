"""Read-only Kali Bay readiness and readable native menu regression tests."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
MANAGER = ROOT / "kali-bay" / "bin" / "kali-bay"
UI = ROOT / "kali-bay" / "ui" / "kali_bay.py"


class KaliReadinessTests(unittest.TestCase):
    def run_report(self, state="running", exists=True, installed=True, gui=True):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            mock_dir = tmp / "bin"
            mock_dir.mkdir()
            calls = tmp / "podman-calls"
            podman = mock_dir / "podman"
            podman.write_text("""#!/bin/sh
printf 'podman %s\\n' "$*" >> "$MOCK_CALLS"
case "$1 $2" in
  "container exists") [ "$MOCK_EXISTS" = "1" ]; exit $? ;;
  "inspect --format")
    if [ "$MOCK_STATE" = "running" ]; then echo true; exit 0; fi
    if [ "$MOCK_STATE" = "stopped" ]; then echo false; exit 0; fi
    exit 15 ;;
  "exec --user") [ "$MOCK_INSTALLED" = "1" ]; exit $? ;;
  *) exit 65 ;;
esac
""", encoding="utf-8")
            podman.chmod(0o755)
            distrobox = mock_dir / "distrobox"
            distrobox.write_text(
                '#!/bin/sh\nprintf "unexpected distrobox\\n" >> "$MOCK_CALLS"\nexit 67\n',
                encoding="utf-8",
            )
            distrobox.chmod(0o755)
            env = os.environ.copy()
            env.update(
                HOME=str(tmp),
                PATH=str(mock_dir) + os.pathsep + env.get("PATH", ""),
                MOCK_CALLS=str(calls),
                MOCK_EXISTS="1" if exists else "0",
                MOCK_STATE=state,
                MOCK_INSTALLED="1" if installed else "0",
            )
            env.pop("WAYLAND_DISPLAY", None)
            if gui:
                env["DISPLAY"] = ":2"
            else:
                env.pop("DISPLAY", None)
            run = subprocess.run(
                ["bash", str(MANAGER), "readiness-json"],
                capture_output=True, text=True, env=env, timeout=10,
            )
            touched_state_dir = (tmp / ".local/state/spider-os/kali-bay").exists()
            touched_data_dir = (tmp / ".local/share/spider-os/kali-bay").exists()
            return (
                run,
                calls.read_text() if calls.exists() else "",
                touched_state_dir or touched_data_dir,
            )

    def test_running_full_kali_and_gui_reports_ready(self):
        result, calls, wrote_dirs = self.run_report()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["container_exists"])
        self.assertTrue(report["container_running"])
        self.assertTrue(report["toolkit_ready"])
        self.assertTrue(report["gui_session"])
        self.assertEqual(report["container_state"], "running")
        self.assertIn("podman exec", calls)
        self.assertFalse(wrote_dirs)
        self.assertNotIn("distrobox", calls)
        self.assertNotIn("podman start", calls)
        self.assertNotIn("apt", calls)

    def test_stopped_kali_never_autostarts_or_inspects_packages(self):
        result, calls, wrote_dirs = self.run_report(state="stopped")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["container_state"], "stopped")
        self.assertFalse(report["toolkit_ready"])
        self.assertIn("START EXISTING KALI", report["next_step"])
        self.assertNotIn("podman exec", calls)
        self.assertNotIn("podman start", calls)
        self.assertFalse(wrote_dirs)

    def test_missing_container_does_not_create_it(self):
        result, calls, wrote_dirs = self.run_report(exists=False, gui=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["container_state"], "missing")
        self.assertFalse(report["container_exists"])
        self.assertFalse(report["gui_session"])
        self.assertNotIn("podman exec", calls)
        self.assertNotIn("podman create", calls)
        self.assertNotIn("distrobox", calls)
        self.assertFalse(wrote_dirs)

    def test_unknown_and_unverified_remain_explicit(self):
        unknown, _, _ = self.run_report(state="unknown")
        self.assertEqual(json.loads(unknown.stdout)["container_state"], "unknown")
        unverified, _, _ = self.run_report(installed=False)
        report = json.loads(unverified.stdout)
        self.assertTrue(report["container_running"])
        self.assertFalse(report["toolkit_ready"])
        self.assertIn("HEALTH CHECK", report["next_step"])


class KaliReadabilityTests(unittest.TestCase):
    def test_menu_contrast_and_selection_are_explicit(self):
        source = UI.read_text(encoding="utf-8")
        for token in (
            "QComboBox QAbstractItemView",
            "selection-background-color: #6b21a8",
            "QPushButton:focus",
            "QToolTip",
            "min-width: 115px",
            "kaliReadinessSummary",
            "READINESS REPORT",
            '"readiness-json"',
            "def show_readiness_report(self):",
        ):
            self.assertIn(token, source)

    def test_readiness_cli_has_no_package_mutation_or_container_start(self):
        source = MANAGER.read_text(encoding="utf-8")
        function = source.split("readiness_json() {", 1)[1].split("\ninfo() {", 1)[0]
        for unsafe in ("podman start", "distrobox enter", "apt-get ", "distrobox create"):
            # Comments are allowed to describe forbidden side effects.
            live_lines = [
                line.strip() for line in function.splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            ]
            self.assertFalse(any(unsafe in line for line in live_lines))


if __name__ == "__main__":
    unittest.main()
