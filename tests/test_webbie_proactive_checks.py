"""Pure/local tests for proactive checks. Never call Ollama or systemd here."""
import importlib.util
from datetime import datetime
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "webbie/agent/proactive_checks.py"
spec = importlib.util.spec_from_file_location("webbie_proactive_checks_test", source)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class ProactiveTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "private-status.json"
        self.clock = [120000.0]
        self.delivered = []
        self.responses = {
            "disk": ("ok", "Storage healthy."),
            "ollama": ("warn", "Local Ollama is offline."),
            "microphone": ("ok", "Microphone listener running."),
        }

    def monitor(self, on_alert=None, settings=None):
        settings = {
            "check_in_minutes": 5,
            "alert_cooldown_minutes": 180,
            "quiet_start": "12:00",
            "quiet_end": "12:00",
            **(settings or {}),
        }
        return mod.ProactiveMonitor(
            state_path=self.path, settings=settings,
            clock=lambda: self.clock[0],
            checks=lambda: self.responses.copy(),
            on_alert=on_alert,
        )

    def test_config_clamps_and_rejects_bad_types(self):
        settings = mod.configure({
            "enabled": 1,
            "watch_ai_dj": "true",
            "check_in_minutes": 0,
            "alert_cooldown_minutes": 3000,
            "disk_warning_free_gib": 1000,
            "quiet_start": "41:98",
        })
        self.assertTrue(settings["enabled"])
        self.assertFalse(settings["watch_ai_dj"])
        self.assertEqual(settings["check_in_minutes"], 5)
        self.assertEqual(settings["alert_cooldown_minutes"], 1440)
        self.assertEqual(settings["disk_warning_free_gib"], 100)
        self.assertEqual(settings["quiet_start"], "22:00")

    def test_quiet_hours_cross_midnight_and_equal_off(self):
        today = datetime.now()
        before = today.replace(hour=23, minute=30, second=0).timestamp()
        after = today.replace(hour=7, minute=15, second=0).timestamp()
        noon = today.replace(hour=12, minute=0, second=0).timestamp()
        self.assertTrue(mod.quiet_now(before, "22:00", "08:00"))
        self.assertTrue(mod.quiet_now(after, "22:00", "08:00"))
        self.assertFalse(mod.quiet_now(noon, "22:00", "08:00"))
        self.assertFalse(mod.quiet_now(before, "12:00", "12:00"))

    def test_checks_run_even_during_sleep_but_do_not_alert(self):
        monitor = self.monitor(on_alert=self.delivered.append)
        result = monitor.tick(session_active=True, sleeping=True)
        self.assertEqual(result["checks"]["ollama"]["status"], "warn")
        self.assertEqual(result["pending_count"], 1)
        self.assertEqual(self.delivered, [])
        monitor.tick(session_active=True, sleeping=False)
        self.assertEqual(self.delivered, ["Local Ollama is offline."])
        self.assertEqual(monitor.snapshot()["pending_count"], 0)

    def test_inactive_session_queues_until_active(self):
        monitor = self.monitor(on_alert=self.delivered.append)
        monitor.tick(session_active=False, sleeping=False)
        self.assertEqual(self.delivered, [])
        monitor.tick(session_active=True, sleeping=False)
        self.assertEqual(len(self.delivered), 1)

    def test_quiet_suppresses_alert_without_canceling_check(self):
        monitor = self.monitor(on_alert=self.delivered.append,
                               settings={"quiet_start": "00:00", "quiet_end": "23:59"})
        result = monitor.tick(session_active=True)
        self.assertTrue(result["last_run"] > 0)
        self.assertEqual(self.delivered, [])

    def test_repeated_identical_failure_does_not_spam(self):
        monitor = self.monitor(on_alert=self.delivered.append)
        monitor.tick(session_active=True)
        self.clock[0] += 300
        monitor.tick(session_active=True)
        self.assertEqual(self.delivered, ["Local Ollama is offline."])

    def test_cooldown_renotifies_unresolved_failure(self):
        monitor = self.monitor(on_alert=self.delivered.append,
                               settings={"alert_cooldown_minutes": 30})
        monitor.tick(session_active=True)
        self.clock[0] += 1800
        monitor.tick(session_active=True)
        self.assertEqual(len(self.delivered), 2)

    def test_recovery_only_after_actual_warning_delivery(self):
        monitor = self.monitor(on_alert=self.delivered.append)
        monitor.tick(session_active=True)
        self.responses["ollama"] = ("ok", "Local Ollama has recovered.")
        self.clock[0] += 300
        monitor.tick(session_active=True)
        self.assertEqual(self.delivered, [
            "Local Ollama is offline.", "Local Ollama has recovered."])

    def test_unseen_failure_clears_without_false_recovery_notice(self):
        monitor = self.monitor(on_alert=self.delivered.append)
        monitor.tick(session_active=False)
        self.responses["ollama"] = ("ok", "Local Ollama has recovered.")
        self.clock[0] += 300
        monitor.tick(session_active=True)
        self.assertEqual(self.delivered, [])
        self.assertEqual(monitor.snapshot()["pending_count"], 0)

    def test_restart_loads_saved_alerts_without_new_probe(self):
        monitor = self.monitor()
        monitor.tick(session_active=True)
        self.assertEqual(monitor.snapshot()["pending_count"], 1)
        restarted = self.monitor(on_alert=self.delivered.append)
        restarted.tick(session_active=True)
        self.assertEqual(self.delivered, ["Local Ollama is offline."])

    def test_failed_notification_is_retried_not_lost(self):
        def broken(message):
            raise RuntimeError("desktop notifications unavailable")
        monitor = self.monitor(on_alert=broken)
        monitor.tick(session_active=True)
        self.assertEqual(monitor.snapshot()["pending_count"], 1)
        monitor.on_alert = self.delivered.append
        monitor.tick(session_active=True)
        self.assertEqual(len(self.delivered), 1)

    def test_storage_mode_is_private_and_anchored(self):
        monitor = self.monitor()
        monitor.tick()
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)
        self.assertEqual(mod._read_small_json(self.path)["version"], 1)
        self.assertLess(self.path.stat().st_size, mod.MAX_STATE_BYTES)

    def test_existing_symlink_cannot_be_overwritten(self):
        target = Path(self.directory.name) / "important.txt"
        target.write_text("not Webbie data")
        self.path.symlink_to(target)
        with self.assertRaises(PermissionError):
            self.monitor().tick()
        self.assertEqual(target.read_text(), "not Webbie data")

    def test_corrupt_state_does_not_crash(self):
        self.path.write_text("{bad json")
        result = self.monitor().tick()
        self.assertIn("checks", result)

    def test_unknown_probe_cannot_inject_new_action(self):
        self.responses["shell_exec"] = ("warn", "run arbitrary command")
        result = self.monitor(on_alert=self.delivered.append).tick(session_active=True)
        self.assertNotIn("shell_exec", result["checks"])
        self.assertEqual(len(self.delivered), 1)

    def test_disabled_monitor_does_not_run_probes(self):
        def crash():
            raise AssertionError("must not check")
        monitor = mod.ProactiveMonitor(
            state_path=self.path, settings={"enabled": False}, checks=crash)
        result = monitor.tick(session_active=True)
        self.assertFalse(result["enabled"])
        self.assertEqual(result["checks"], {})

    def test_status_message_read_only(self):
        self.monitor().tick()
        message = mod.status_message(self.path)
        self.assertIn("Storage healthy.", message)
        self.assertIn("Local Ollama is offline.", message)

    def test_microphone_reports_state_not_speaker_identity(self):
        agent_path = Path(self.directory.name) / "webbie.json"
        agent_path.write_text(json.dumps({"voice_listener": False}))
        status, text = mod.probe_microphone(agent_state=agent_path)
        self.assertEqual(status, "warn")
        self.assertIn("listener error", text)
        agent_path.write_text(json.dumps({"voice_listener": True}))
        status, text = mod.probe_microphone(agent_state=agent_path)
        self.assertEqual(status, "ok")
        self.assertIn("not hardware verified", text)

    def test_disk_probe_uses_free_space(self):
        from collections import namedtuple
        Usage = namedtuple("usage", ["total", "used", "free"])
        with patch.object(mod.shutil, "disk_usage",
                          return_value=Usage(100 * 1024**3, 99 * 1024**3, 1024**3)):
            status, text = mod.probe_disk(warning_gib=5)
        self.assertEqual(status, "warn")
        self.assertIn("Storage is low", text)

    def test_dj_probe_only_asks_systemd_read_only(self):
        from types import SimpleNamespace
        calls = []
        def runner(args, **kwargs):
            calls.append((args, kwargs))
            return SimpleNamespace(returncode=0, stdout="active\n")
        status, message = mod.probe_ai_dj(runner=runner)
        self.assertEqual(status, "ok")
        self.assertEqual(calls[0][0], [
            "systemctl", "--user", "is-active", "spider-ai-dj.service"])
        self.assertIn("broadcast not verified", message)

    def test_ollama_uses_fixed_loopback_endpoint_and_bounded_response(self):
        from io import BytesIO
        class Response:
            status = 200
            def __init__(self):
                self.body = BytesIO(b'{"models":[]}')
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self, count):
                self.count = count
                return self.body.read(count)
        seen = []
        def opener(url, timeout=0):
            seen.append((url, timeout))
            return Response()
        status, _ = mod.probe_ollama(opener=opener)
        self.assertEqual(status, "ok")
        self.assertEqual(seen, [("http://127.0.0.1:11434/api/tags", 2)])


if __name__ == "__main__":
    unittest.main()
