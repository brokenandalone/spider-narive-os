"""Kali Bay status must not trigger Distrobox installation or mutate the host."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
KALI = ROOT / 'kali-bay/bin/kali-bay'


class KaliBayCliTests(unittest.TestCase):
    def run_kali(self, action, running=True):
        with tempfile.TemporaryDirectory() as tmp:
            mock_bin = Path(tmp, 'bin')
            mock_bin.mkdir()
            calls = Path(tmp, 'calls')
            podman = mock_bin / 'podman'
            podman.write_text("""#!/bin/sh
printf 'podman %s\\n' "$*" >> "$MOCK_CALLS"
case "$1 $2" in
  "container exists") exit 0 ;;
  "inspect --format") if [ "$MOCK_RUNNING" = "1" ]; then echo true; else echo false; fi; exit 0 ;;
  "exec --user") exit 0 ;;
  *) exit 71 ;;
esac
""")
            podman.chmod(0o755)
            distrobox = mock_bin / 'distrobox'
            distrobox.write_text("""#!/bin/sh
printf 'distrobox %s\\n' "$*" >> "$MOCK_CALLS"
exit 72
""")
            distrobox.chmod(0o755)
            env = dict(os.environ, HOME=tmp, PATH=str(mock_bin)+os.pathsep+os.environ.get('PATH', ''),
                       MOCK_CALLS=str(calls), MOCK_RUNNING='1' if running else '0')
            result = subprocess.run(['bash', str(KALI), action], env=env,
                                    text=True, capture_output=True, timeout=10)
            return result, calls.read_text() if calls.exists() else ''

    def test_ready_status_uses_only_podman(self):
        result, calls = self.run_kali('status')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'ready')
        self.assertNotIn('distrobox', calls)
        self.assertIn('podman exec', calls)

    def test_stopped_container_status_does_not_start_it(self):
        result, calls = self.run_kali('status', running=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'container')
        self.assertNotIn('distrobox', calls)
        self.assertNotIn('podman exec', calls)
        self.assertNotIn('podman start', calls)

    def test_update_no_unconditional_autoremove(self):
        self.assertNotIn('apt-get autoremove', KALI.read_text())


if __name__ == '__main__':
    unittest.main()
