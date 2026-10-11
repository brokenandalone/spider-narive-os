"""Verify the separate proactive-session PR works with current Webbie sleep gate."""
import ast
import importlib.util
import os
from pathlib import Path
import pwd
import subprocess
import tempfile
import unittest
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
AGENT = BASE / "webbie/agent/webbie.py"
tree = ast.parse(AGENT.read_text())
names = {"session_activity", "session_is_active"}
nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef)
         and n.name in names]
assert {n.name for n in nodes} == names, "Webbie session activity check missing"
scope = dict(os=os, pwd=pwd, subprocess=subprocess)
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(AGENT), "exec"), scope)

night = importlib.util.spec_from_file_location(
    "webbie_night_mode_source_test", BASE / "webbie/agent/night_mode.py")
night_module = importlib.util.module_from_spec(night)
night.loader.exec_module(night_module)


class WebbieProactiveSessions(unittest.TestCase):
    def test_multiple_sessions_choose_active_unlocked_kde(self):
        username = pwd.getpwuid(os.getuid()).pw_name
        def output(argv, **kwargs):
            if "list-sessions" in argv:
                return f"2 1000 {username} seat0 tty2\n7 1000 {username} seat0 tty7"
            if "2" in argv:
                return "Active=no\nIdleHint=yes\nLockedHint=no\nRemote=no\nType=tty"
            return "Active=yes\nIdleHint=no\nLockedHint=no\nRemote=no\nType=x11"
        with patch.object(subprocess, "check_output", side_effect=output):
            self.assertTrue(scope["session_is_active"]())
            self.assertEqual(scope["session_activity"]()[1], "active session 7")

    def test_locked_idle_remote_or_non_graphical_is_not_active(self):
        username = pwd.getpwuid(os.getuid()).pw_name
        good = "Active=yes\nIdleHint=no\nLockedHint=no\nRemote=no\nType=wayland"
        for field, replacement in (("LockedHint=no", "LockedHint=yes"),
                                   ("IdleHint=no", "IdleHint=yes"),
                                   ("Remote=no", "Remote=yes"),
                                   ("Type=wayland", "Type=tty")):
            info = good.replace(field, replacement)
            def output(argv, **kwargs):
                if "list-sessions" in argv:
                    return f"7 1000 {username} seat0 tty7"
                return info
            with self.subTest(field=field), patch.object(
                subprocess, "check_output", side_effect=output
            ):
                self.assertFalse(scope["session_is_active"]())

    def test_session_lookup_failure_is_never_activity(self):
        with patch.object(subprocess, "check_output",
                          side_effect=FileNotFoundError):
            activity, reason = scope["session_activity"]()
        self.assertFalse(activity)
        self.assertIn("failed", reason)

    def test_existing_night_mode_is_kept_and_proactive_gated(self):
        with tempfile.TemporaryDirectory() as home:
            flag = Path(home) / "sleep.json"
            flag.write_text('{"asleep":true,"until":null}')
            self.assertTrue(night_module.asleep(flag))
            flag.write_text('{"asleep":false}')
            self.assertFalse(night_module.asleep(flag))
        source = AGENT.read_text()
        self.assertIn("from night_mode import asleep as quiet_asleep", source)
        self.assertIn("and not quiet_asleep()", source)
        self.assertIn("sleeping = quiet_asleep()", source)


if __name__ == "__main__":
    unittest.main()
