"""Check that a failed verifier and broken logging cannot strand the VM."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BootResultTests(unittest.TestCase):
    def run_report(self, result, marker, broken_output=False):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            called = path / 'shutdown'
            for name, body in {
                'journalctl': 'echo test-journal',
                'systemctl': f'printf "%s\\n" "$*" > "{called}"',
            }.items():
                command = path / name
                command.write_text('#!/bin/sh\n' + body + '\n')
                command.chmod(0o755)
            passed = path / 'passed'
            if marker:
                passed.touch()
            env = dict(os.environ, PATH=f'{path}:{os.environ["PATH"]}', SERVICE_RESULT=result)
            with open('/dev/full' if broken_output else '/dev/null', 'w') as sink:
                run = subprocess.run(
                    ['bash', str(ROOT / 'tests/report-boot-result.sh'), str(passed)],
                    env=env, stdout=sink if broken_output else subprocess.PIPE,
                    stderr=subprocess.PIPE, text=True, timeout=5)
            self.assertEqual(called.read_text().strip(), '--no-block poweroff')
            return run

    def test_success_requires_completed_checks_and_successful_service(self):
        self.assertIn('SPIDER_DISK_BOOT_PASSED', self.run_report('success', True).stdout)
        for result, marker in [('success', False), ('timeout', True), ('exit-code', False)]:
            run = self.run_report(result, marker)
            self.assertIn('SPIDER_DISK_BOOT_FAILED', run.stdout)
            self.assertNotIn('SPIDER_DISK_BOOT_PASSED', run.stdout)

    def test_broken_output_cannot_prevent_shutdown(self):
        self.assertEqual(self.run_report('exit-code', False, broken_output=True).returncode, 0)


if __name__ == '__main__':
    unittest.main()
