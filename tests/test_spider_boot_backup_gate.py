"""Regression checks for backup-first, no-installer-media SpiderOS release prep."""
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKUP = ROOT / "distro/backup-spider-boot-independent.sh"

class BootBackupGateTests(unittest.TestCase):
    def test_shell_parses(self):
        subprocess.run(["bash", "-n", str(BACKUP)], check=True)

    def test_rejects_backups_on_same_internal_disk(self):
        text = BACKUP.read_text()
        self.assertIn('mount_target" == "/"', text)
        self.assertIn("ancestors=", text)
        self.assertIn("same physical /dev/sda disk", text)
        self.assertIn("independent mounted backup volume required", text)

    def test_data_backed_up_and_verified_without_writing_source(self):
        text = BACKUP.read_text()
        self.assertIn("dd if=/dev/sda1 of=", text)
        self.assertIn("dd if=/dev/sda2 of=", text)
        self.assertIn("sha256sum -c SHA256SUMS", text)
        self.assertIn("stat -c %s", text)
        self.assertIn("webbie-brain.tar", text)
        self.assertIn("sda-partitions.txt", text)
        self.assertNotIn("grub-install", text)
        self.assertNotIn("update-grub", text)
        self.assertNotIn("do-release-upgrade", text)
        self.assertNotIn("mkfs.", text)
        self.assertNotIn("of=/dev/sda", text)

if __name__ == "__main__":
    unittest.main()
