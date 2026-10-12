"""Only the reviewed owner Webbie session function changes; no live PC writes."""
import ast
import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
spec=importlib.util.spec_from_file_location(
    "spider_session_patch", ROOT/"tools/patch_owner_session_detection.py"
)
helper=importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class WebbieSessionPatchTests(unittest.TestCase):
    def sample(self):
        source=b'''import os
import subprocess

def keep_browser_commands():
    return "firefox stays"

def session_is_active():
    # Simulate the original's incorrect early False for first session.
    return False

def keep_audio_hearing():
    return "owner's microphone"
'''
        node=helper.function_node(source)
        fhash=hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest()
        return source, fhash

    def test_only_target_function_changes(self):
        source,fhash=self.sample()
        amended=helper.patch_source(
            source,
            expected_source_sha=hashlib.sha256(source).hexdigest(),
            expected_func_sha=fhash,
        )
        text=amended.decode()
        self.assertIn('return "firefox stays"',text)
        self.assertIn('return "owner\'s microphone"',text)
        self.assertIn("LockedHint",text)
        self.assertIn("for line in sessions.splitlines():",text)
        self.assertIn("def session_is_active():",text)
        self.assertEqual(sum(1 for n in ast.parse(text).body
                             if isinstance(n,ast.FunctionDef) and
                             n.name=="session_is_active"),1)
        self.assertNotEqual(source,amended)

    def test_wrong_fingerprint_blocks(self):
        src,func=self.sample()
        with self.assertRaisesRegex(ValueError,"changed"):
            helper.patch_source(src,expected_source_sha="0"*64,expected_func_sha=func)
        with self.assertRaisesRegex(ValueError,"does not match"):
            helper.patch_source(src,expected_source_sha=hashlib.sha256(src).hexdigest(),
                                expected_func_sha="0"*64)

    def controlled(self, status):
        namespace={"os":os,"subprocess":subprocess}
        exec(helper.REPLACEMENT,namespace)
        identity=__import__("pwd").getpwuid(os.getuid()).pw_name
        def fake(cmd,**_kw):
            if cmd[1]=="list-sessions":
                return f"1 100 {identity} seat0 tty2\n2 100 {identity} seat0 tty3\n"
            if cmd[2]=="1":
                return ("Active=no\nIdleHint=yes\nLockedHint=no\n"
                        "Remote=no\nType=tty\n")
            if cmd[2]=="2":
                return ("Active="+status.get("active","yes")+
                        "\nIdleHint="+status.get("idle","no")+
                        "\nLockedHint="+status.get("locked","no")+
                        "\nRemote="+status.get("remote","no")+
                        "\nType="+status.get("type","x11")+"\n")
            raise AssertionError(cmd)
        with patch.object(subprocess,"check_output",side_effect=fake):
            return namespace["session_is_active"]()

    def test_second_active_session_is_recognized(self):
        self.assertTrue(self.controlled({}))

    def test_locked_idle_remote_or_tty_is_not_counted(self):
        for state in (
            {"locked":"yes"},{"idle":"yes"},
            {"remote":"yes"},{"active":"no"},{"type":"tty"}
        ):
            with self.subTest(state=state):
                self.assertFalse(self.controlled(state))

    def test_login_session_failure_is_fail_closed(self):
        namespace={"os":os,"subprocess":subprocess}
        exec(helper.REPLACEMENT,namespace)
        with patch.object(subprocess,"check_output",side_effect=subprocess.TimeoutExpired("loginctl",4)):
            self.assertFalse(namespace["session_is_active"]())

    def test_no_run_of_installed_agent_at_import(self):
        self.assertIn("OWNER_SHA256",helper.__dict__)
        self.assertNotIn("main",str(helper.REPLACEMENT))


if __name__=="__main__":
    unittest.main()
