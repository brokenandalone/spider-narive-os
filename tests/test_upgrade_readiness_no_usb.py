"""Checks for the USB-free in-place upgrade readiness report."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "distro" / "report-inplace-26-10.sh"


class InPlace2610ReadinessTests(unittest.TestCase):
    def test_shell_syntax(self):
        subprocess.run(["bash", "-n", str(SCRIPT)], check=True)

    def test_has_no_upgrade_or_privileged_actions(self):
        source = SCRIPT.read_text()
        self.assertNotIn("sudo ", source)
        self.assertNotIn("apt-get install", source)
        self.assertNotIn("apt-get update", source)
        self.assertNotIn("do-release-upgrade -d", source)
        self.assertNotIn("update-initramfs", source)
        self.assertNotIn("grub-install", source)
        self.assertIn("apt-get -s full-upgrade", source)
        self.assertIn("26.04 only, NOT the 26.10 plan", source)

    def test_custom_unmounted_efi_boot_is_an_explicit_stop_gate(self):
        source = SCRIPT.read_text()
        self.assertIn('stub="/boot/efi/EFI/SpiderOS/grub.cfg"', source)
        self.assertIn('findmnt -rn -S "UUID=$stub_uuid"', source)
        self.assertIn('mark BLOCK "Separate unmounted SpiderOS boot filesystem"', source)
        self.assertIn("kernel and initramfs may be loaded from it", source)

    def test_report_on_wrong_host_blocks_without_changing_it(self):
        # The Ubuntu 24.04 GitHub runner intentionally is NOT an eligible host.
        with tempfile.TemporaryDirectory(prefix="spider-readiness-") as home:
            env = dict(os.environ, HOME=home)
            cp = subprocess.run(
                ["bash", str(SCRIPT)],
                text=True, capture_output=True, env=env, timeout=45,
            )
            self.assertEqual(cp.returncode, 2, cp.stdout[-3000:] + cp.stderr[-3000:])
            self.assertIn("Unexpected version", cp.stdout)
            self.assertIn("NO CHANGES", cp.stdout)
            reports = list(Path(home).glob("SpiderOS-26.10-Readiness-*/SUMMARY.txt"))
            self.assertEqual(len(reports), 1)
            self.assertIn("do-release-upgrade", reports[0].read_text())


if __name__ == "__main__":
    unittest.main()
