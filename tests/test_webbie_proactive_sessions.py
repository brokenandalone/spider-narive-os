"""Regression checks for Webbie proactive gating; never imports the running agent."""
import ast
import json
import os
import pwd
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

AGENT = Path(__file__).resolve().parents[1] / "webbie/agent/webbie.py"
tree = ast.parse(AGENT.read_text(encoding="utf-8"))
names = {"session_activity", "session_is_active", "quiet_asleep"}
nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
assert {node.name for node in nodes} == names, "Proactive session helpers missing"
scope = dict(json=json, os=os, pwd=pwd, subprocess=subprocess, Path=Path, time=time)
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(AGENT), "exec"), scope)


class ProactiveSessionTests(unittest.TestCase):
    def test_checks_second_session_after_inactive_first_session(self):
        username = pwd.getpwuid(os.getuid()).pw_name
        def output(cmd, **kwargs):
            if "list-sessions" in cmd:
                return f"2 1000 {username} seat0 tty2\\n7 1000 {username} seat0 tty7"
            if "2" in cmd:
                return "Active=no\\nIdleHint=yes\\nLockedHint=no\\nRemote=no\\nType=tty"
            return "Active=yes\\nIdleHint=no\\nLockedHint=no\\nRemote=no\\nType=x11"
        with patch.object(subprocess, "check_output", side_effect=output):
            self.assertTrue(scope["session_is_active"]())
            self.assertEqual(scope["session_activity"]()[1], "active session 7")

    def test_locked_or_idle_session_is_rejected(self):
        username = pwd.getpwuid(os.getuid()).pw_name
        for field in ("LockedHint", "IdleHint"):
            info = "Active=yes\\nIdleHint=no\\nLockedHint=no\\nRemote=no\\nType=wayland"
            info = info.replace(field + "=no", field + "=yes")
            def output(cmd, **kwargs):
                return (f"7 1000 {username} seat0 tty7" if "list-sessions" in cmd else info)
            with self.subTest(field=field), patch.object(subprocess, "check_output", side_effect=output):
                self.assertFalse(scope["session_is_active"]())

    def test_lookup_errors_are_not_mistaken_for_activity(self):
        with patch.object(subprocess, "check_output", side_effect=FileNotFoundError):
            active, reason = scope["session_activity"]()
            self.assertFalse(active)
            self.assertIn("failed", reason)

    def test_sleep_flag_prevents_spontaneous_checkin(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p = root / ".config/spider-os/webbie-face.json"
            p.parent.mkdir(parents=True)
            p.write_text('{"asleep":true,"until":null}')
            with patch.object(Path, "home", return_value=root):
                self.assertTrue(scope["quiet_asleep"]())
                p.write_text('{"asleep":false}')
                self.assertFalse(scope["quiet_asleep"]())


if __name__ == "__main__":
    unittest.main()
