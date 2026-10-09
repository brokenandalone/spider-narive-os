"""Kali Bay-only packaging stays separate from Kali provisioning or host upgrades."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / 'kali-bay/package/install-kali-bay.sh'


class KaliOnlyInstallerTests(unittest.TestCase):
    def test_shell_syntax(self):
        subprocess.run(['bash', '-n', str(INSTALLER)], check=True)

    def test_read_only_check_does_not_invoke_container_runtime(self):
        with tempfile.TemporaryDirectory() as folder:
            tmp = Path(folder)
            log = tmp / 'invoked'
            for name in ('podman', 'distrobox'):
                executable = tmp / name
                executable.write_text('#!/bin/sh\nprintf "%s\\n" "' + name + '" >> "$MOCK_CALLS"\nexit 90\n')
                executable.chmod(0o755)
            env = dict(os.environ, PATH=str(tmp) + ':' + os.environ.get('PATH', ''),
                       MOCK_CALLS=str(log))
            result = subprocess.run(['bash', str(INSTALLER), '--check'], env=env,
                                    text=True, capture_output=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Read-only check complete', result.stdout)
            self.assertFalse(log.exists(), 'check unexpectedly launched the container runtime')

    def test_install_scope_is_host_ui_only_with_rollback(self):
        content = INSTALLER.read_text()
        for prohibited in ('distrobox enter', 'distrobox create', 'podman run',
                           'podman exec', 'apt-get', 'update-grub', 'autoremove',
                           'systemctl stop', 'rm -rf'):
            self.assertNotIn(prohibited, content)
        self.assertIn('kali-bay/ui/kali_bay.py', content)
        self.assertIn('kali-bay/bin/kali-bay', content)
        self.assertIn('spider-kali-bay.desktop', content)
        self.assertIn('rollback.sh', content)
        self.assertIn('Kali container and its installed tools were not modified.', content)

    def test_bad_arguments_never_apply(self):
        result = subprocess.run(['bash', str(INSTALLER), '--invalid'],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 2)
        self.assertIn('Usage:', result.stdout)


if __name__ == '__main__':
    unittest.main()
