"""Local reminder tests: no speech, desktop, calendar or network access."""
from datetime import datetime, timedelta
import importlib.util
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "webbie/agent"))
from local_reminders import (
    ReminderScheduler, add_reminder, delete_reminder, list_reminders,
    _occurrence,
)

class ReminderTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "reminders.json"
        self.now = datetime(2026, 10, 11, 14, 0)
        self.clock = [self.now.timestamp()]
        self.notices = []

    def create(self, title="Attend a meeting", minutes=10, repeat="once"):
        due = (self.now + timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M")
        return add_reminder(title, due, repeat, path=self.path, now=self.now)

    def scheduler(self, callback=None):
        return ReminderScheduler(
            path=self.path, clock=lambda: self.clock[0],
            on_alert=callback)

    def test_one_time_not_before_due(self):
        self.create()
        self.assertEqual(self.scheduler(self.notices.append).tick(
            session_active=True, quiet_start="12:00", quiet_end="12:00")["delivered"], 0)
        self.assertEqual(self.notices, [])

    def test_once_delivered_exactly_one_time(self):
        self.create()
        scheduler = self.scheduler(self.notices.append)
        self.clock[0] += 11 * 60
        first = scheduler.tick(session_active=True, quiet_start="12:00", quiet_end="12:00")
        second = scheduler.tick(session_active=True, quiet_start="12:00", quiet_end="12:00")
        self.assertEqual(first["delivered"], 1)
        self.assertEqual(second["delivered"], 0)
        self.assertEqual(self.notices, ["Reminder: Attend a meeting"])

    def test_reminder_is_saved_privately(self):
        self.create()
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)
        self.assertEqual(len(list_reminders(self.path)), 1)

    def test_sleep_queues_due_reminder_until_wake(self):
        self.create()
        self.clock[0] += 11 * 60
        scheduler = self.scheduler(self.notices.append)
        result = scheduler.tick(session_active=True, sleeping=True,
                                quiet_start="12:00", quiet_end="12:00")
        self.assertEqual(result["due"], 1)
        self.assertEqual(self.notices, [])
        scheduler.tick(session_active=True, sleeping=False,
                       quiet_start="12:00", quiet_end="12:00")
        self.assertEqual(len(self.notices), 1)

    def test_inactive_desktop_does_not_notify(self):
        self.create()
        self.clock[0] += 11 * 60
        scheduler = self.scheduler(self.notices.append)
        scheduler.tick(session_active=False, quiet_start="12:00", quiet_end="12:00")
        self.assertFalse(self.notices)
        scheduler.tick(session_active=True, quiet_start="12:00", quiet_end="12:00")
        self.assertEqual(len(self.notices), 1)

    def test_notification_error_does_not_acknowledge(self):
        self.create()
        self.clock[0] += 11 * 60
        def broken(message):
            raise OSError("notification unavailable")
        scheduler = self.scheduler(broken)
        self.assertEqual(scheduler.tick(session_active=True, quiet_start="12:00",
                                        quiet_end="12:00")["due"], 1)
        scheduler.on_alert = self.notices.append
        scheduler.tick(session_active=True, quiet_start="12:00",
                       quiet_end="12:00")
        self.assertEqual(len(self.notices), 1)

    def test_repeat_daily_once_per_local_calendar_date(self):
        self.create(repeat="daily")
        scheduler = self.scheduler(self.notices.append)
        self.clock[0] += 11 * 60
        scheduler.tick(session_active=True, quiet_start="12:00", quiet_end="12:00")
        self.clock[0] += 86400
        scheduler.tick(session_active=True, quiet_start="12:00", quiet_end="12:00")
        self.assertEqual(len(self.notices), 2)

    def test_weekly_only_matches_start_weekday(self):
        self.create(repeat="weekly")
        scheduler = self.scheduler(self.notices.append)
        self.clock[0] += 11 * 60
        scheduler.tick(session_active=True, quiet_start="12:00", quiet_end="12:00")
        self.clock[0] += 86400
        scheduler.tick(session_active=True, quiet_start="12:00", quiet_end="12:00")
        self.assertEqual(len(self.notices), 1)
        self.clock[0] += 6 * 86400
        scheduler.tick(session_active=True, quiet_start="12:00", quiet_end="12:00")
        self.assertEqual(len(self.notices), 2)

    def test_older_once_is_not_surprise_delivered_days_later(self):
        self.create(repeat="once")
        self.clock[0] += 4 * 86400
        scheduler = self.scheduler(self.notices.append)
        self.assertEqual(scheduler.tick(session_active=True,
                         quiet_start="12:00", quiet_end="12:00")["delivered"], 0)

    def test_delete_clears_future_reminder(self):
        identifier = self.create()
        self.assertTrue(delete_reminder(identifier, path=self.path))
        self.assertFalse(delete_reminder(identifier, path=self.path))
        self.clock[0] += 1000
        self.scheduler(self.notices.append).tick(
            session_active=True, quiet_start="12:00", quiet_end="12:00")
        self.assertFalse(self.notices)

    def test_invalid_time_or_recurrence_is_rejected(self):
        for due in ["tomorrow", "2026-10-11T99:00", "2026-10-11T14:00Z"]:
            with self.subTest(due=due), self.assertRaises(ValueError):
                add_reminder("hello", due, path=self.path, now=self.now)
        with self.assertRaises(ValueError):
            self.create(repeat="hourly")
        with self.assertRaises(ValueError):
            self.create(title=" ")

    def test_cannot_add_past_event(self):
        with self.assertRaises(ValueError):
            self.create(minutes=-500)

    def test_maximum_reminder_count(self):
        for number in range(50):
            self.create(title=f"Reminder {number}")
        with self.assertRaises(ValueError):
            self.create(title="Too many")
        self.assertEqual(len(list_reminders(self.path)), 50)

    def test_symlink_cannot_redirect_reminders(self):
        target = Path(self.directory.name) / "important.txt"
        target.write_text("protected")
        self.path.symlink_to(target)
        with self.assertRaises(PermissionError):
            self.create()
        self.assertEqual(target.read_text(), "protected")

    def test_restart_does_not_repeat_sent_reminder(self):
        self.create()
        self.clock[0] += 11 * 60
        self.scheduler(self.notices.append).tick(session_active=True,
                  quiet_start="12:00", quiet_end="12:00")
        self.scheduler(self.notices.append).tick(session_active=True,
                  quiet_start="12:00", quiet_end="12:00")
        self.assertEqual(len(self.notices), 1)

    def test_due_notifications_bounded_per_tick(self):
        for number in range(9):
            self.create(title=f"Reminder {number}")
        self.clock[0] += 11 * 60
        scheduler = self.scheduler(self.notices.append)
        first = scheduler.tick(session_active=True,
                  quiet_start="12:00", quiet_end="12:00")
        self.assertEqual(first["delivered"], 5)
        self.assertEqual(first["due"], 4)
        second = scheduler.tick(session_active=True,
                  quiet_start="12:00", quiet_end="12:00")
        self.assertEqual(second["delivered"], 4)
        self.assertEqual(len(self.notices), 9)

    def test_no_notification_sink_does_not_mark_sent(self):
        self.create()
        self.clock[0] += 11 * 60
        scheduler = self.scheduler()
        self.assertEqual(scheduler.tick(session_active=True,
                  quiet_start="12:00", quiet_end="12:00")["due"], 1)
        self.assertFalse(scheduler.state_path.exists())


if __name__ == "__main__":
    unittest.main()
