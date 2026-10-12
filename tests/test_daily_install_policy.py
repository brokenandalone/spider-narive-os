"""Disposable once-per-day installer test: no privileged access."""
from datetime import datetime
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "spider_daily_install_policy_test", ROOT / "system/daily_install_policy.py"
)
policy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(policy)
CLOCK = lambda: datetime(2026, 10, 11, 16, 0, tzinfo=ZoneInfo("America/Indiana/Indianapolis"))


class OneSystemInstallPerDayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "backups"

    def test_first_install_slot_is_available_before_backup_receipt(self):
        self.assertEqual(policy.existing_batch_receipts(self.root,
                         policy.local_day(CLOCK)), [])
        with policy.daily_install_guard(self.root, CLOCK):
            self.assertTrue(self.root.is_dir())
            lock = self.root / ".spider-daily-install.lock"
            self.assertEqual(lock.stat().st_mode & 0o777, 0o600)
        self.assertEqual(policy.existing_batch_receipts(self.root,
                         policy.local_day(CLOCK)), [])

    def test_second_normal_install_same_day_is_denied(self):
        with policy.daily_install_guard(self.root, CLOCK):
            receipt = self.root / "spider-batch-20261011-160000-123456"
            receipt.mkdir(mode=0o700)
            (receipt / "manifest.json").write_text('{"version":1,"files":[]}\n')
        with self.assertRaisesRegex(RuntimeError, "One Spider OS system installation"):
            with policy.daily_install_guard(self.root, CLOCK):
                self.fail("A second batch must not run")

    def test_backups_on_earlier_date_do_not_use_next_day_slot(self):
        old = self.root / "spider-batch-20261010-151000-000000"
        old.mkdir(parents=True)
        receipt = old / "manifest.json"
        receipt.write_text('{"version":1,"files":[]}')
        when = datetime(2026, 10, 10, 15, 10,
                        tzinfo=ZoneInfo("America/Indiana/Indianapolis"))
        os.utime(receipt, (when.timestamp(), when.timestamp()))
        with policy.daily_install_guard(self.root, CLOCK):
            pass

    def test_uncertain_or_incomplete_same_day_receipt_is_fail_closed(self):
        receipt = self.root / "spider-batch-20261011-160000-000000"
        receipt.mkdir(parents=True)
        (receipt / "manifest.json").write_text('{"version":1,"files":[]}')
        with self.assertRaisesRegex(RuntimeError, "receipt already exists"):
            with policy.daily_install_guard(self.root, CLOCK):
                pass

    def test_crashed_batch_without_manifest_still_uses_daily_slot(self):
        crash = self.root / "spider-batch-20261011-160000-500000"
        crash.mkdir(parents=True)
        (crash / "original-0000").write_text("backup copy before receipt")
        self.assertFalse((crash / "manifest.json").exists())
        found = policy.existing_batch_receipts(self.root, policy.local_day(CLOCK))
        self.assertEqual(found, [crash])
        with self.assertRaisesRegex(RuntimeError, "receipt already exists"):
            with policy.daily_install_guard(self.root, CLOCK):
                self.fail("Never retry a partially staged same-day batch")

    def test_symlink_backups_and_receipts_are_rejected(self):
        outside = Path(self.tmp.name) / "outside"
        outside.mkdir()
        self.root.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(RuntimeError, "symlink"):
            with policy.daily_install_guard(self.root, CLOCK):
                pass
        self.root.unlink()
        self.root.mkdir()
        link = self.root / "spider-batch-20261011-160000-000000"
        link.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(RuntimeError, "receipt link"):
            with policy.daily_install_guard(self.root, CLOCK):
                pass

    def test_timezone_is_american_indianapolis_not_utc(self):
        # UTC Oct 12 can still be Oct 11 in Indianapolis.
        from datetime import timezone
        utc = datetime(2026, 10, 12, 2, 0, tzinfo=timezone.utc)
        self.assertEqual(policy.local_day(lambda: utc).isoformat(), "2026-10-11")
        with self.assertRaises(ValueError):
            policy.local_day(lambda: datetime(2026, 10, 11, 12))


if __name__ == "__main__":
    unittest.main()
