"""JARVIS readiness checks use synthetic PC files. No owner data or installs."""
import ast
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import Mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from jarvis_install_preflight import assess,render,speaker_gate_status,main


class DummyBatch:
    def __init__(self,state="CURRENT",file_count=2):
        self.state=state
        self.file_count=file_count

    def prepare_items(self,*,root,install,units,home,uid,gid):
        return [types.SimpleNamespace(
            source=Path(root)/f"module{i}.py",
            target=Path(install)/f"module{i}.py",
            reference=f"webbie/module{i}.py",
        ) for i in range(self.file_count)]

    def inspect(self,items,**kwargs):
        return [(item,self.state,"owner-secret-value-DO-NOT-EXPORT")
                for item in items]


class DummyAudit:
    def __init__(self,errors=None):
        self.errors=errors or []

    def audit(self,source,installed):
        return (self.errors,["PC source mismatch but never export content"])


class JarvisPcPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.checkout=self.root/"source"
        (self.checkout/"system").mkdir(parents=True)
        (self.checkout/"system/release_batch.py").write_text(
            "APP_FILES=('module0.py','module1.py')\n")
        self.installed=self.root/"installed"
        self.installed.mkdir()
        self.home=self.root/"owner"
        self.home.mkdir()
        self.voice_dir=self.installed/"webbie"/"voice"
        self.voice_dir.mkdir(parents=True)
        self.config=self.installed/"webbie"/"config"/"default.json"
        self.config.parent.mkdir()
        self.provider=self.voice_dir/"speaker_voice_provider.py"

    def run_assess(self,**overrides):
        opts={
            "home":self.home,
            "env":{"XDG_SESSION_TYPE":"x11"},
            "available_bytes":6*1024**3,
            "release":DummyBatch(),
            "audit":DummyAudit(),
            "config":self.config,
            "provider":self.provider,
        }
        opts.update(overrides)
        return assess(self.checkout,self.installed,**opts)

    def add_pinned_voice(self):
        content=b"def verify_audio_segment(path):\n    return None\n"
        self.provider.write_bytes(content)
        self.config.write_text(json.dumps({
            "speaker_verification":{
                "enabled":True,
                "provider_sha256":hashlib.sha256(content).hexdigest(),
            }
        }))

    def test_no_provider_blocks_one_combined_install(self):
        report=self.run_assess()
        self.assertEqual(report["status"],"BLOCKED")
        self.assertFalse(report["install_authorized"])
        self.assertFalse(report["install_executed"])
        self.assertEqual(report["summary"]["CURRENT"],2)
        self.assertTrue(any("speaker" in entry.lower()
                            for entry in report["blockers"]))
        self.assertNotIn("owner-secret-value",render(report))
        self.assertNotIn(str(self.home),render(report))
        self.assertEqual(list(self.installed.glob("module*.py")),[])

    def test_pinned_provider_still_requires_live_owner_voice_testing(self):
        self.add_pinned_voice()
        report=self.run_assess()
        self.assertEqual(report["status"],"MANUAL_ACCEPTANCE_HOLD")
        self.assertEqual(report["voice"]["status"],
                         "live_verification_required")
        self.assertTrue(report["voice"]["provider_source_verified"])
        self.assertFalse(report["install_authorized"])
        self.assertTrue(any("live enroll" in item.lower()
                            for item in report["reviews"]))

    def test_mismatched_owner_file_blocks_everything_and_redacts(self):
        self.add_pinned_voice()
        report=self.run_assess(
            release=DummyBatch(state="BLOCKED"))
        self.assertEqual(report["status"],"BLOCKED")
        self.assertEqual(len(report["drift"]),2)
        self.assertTrue(any("entire batch" in x.lower()
                            for x in report["blockers"]))
        self.assertNotIn("owner-secret-value",json.dumps(report))
        self.assertEqual(report["drift"][0]["component"],
                         "webbie/module0.py")

    def test_source_manifest_issue_blocks_a_safe_PC(self):
        self.add_pinned_voice()
        report=self.run_assess(
            audit=DummyAudit(["NOT IN BATCH INSTALLER: tool.py"]))
        self.assertEqual(report["status"],"BLOCKED")
        self.assertEqual(len(report["source_audit"]),1)

    def test_missing_space_blocks_and_privacy_report_contains_no_paths(self):
        self.add_pinned_voice()
        report=self.run_assess(available_bytes=150)
        self.assertEqual(report["backups"]["space_check"],"insufficient")
        self.assertEqual(report["status"],"BLOCKED")
        self.assertNotIn(str(self.installed),render(report))

    def test_fake_wayland_session_needs_real_desktop_review(self):
        self.add_pinned_voice()
        report=self.run_assess(env={"XDG_SESSION_TYPE":"wayland"})
        self.assertEqual(report["desktop"]["session"],"wayland")
        self.assertTrue(any("KDE X11" in x for x in report["reviews"]))

    def test_symlink_or_corrupt_voice_providers_never_pass(self):
        self.add_pinned_voice()
        self.provider.unlink()
        outside=self.root/"nonlocal.py"
        outside.write_text("pass\n")
        self.provider.symlink_to(outside)
        self.assertEqual(speaker_gate_status(
            self.installed,config=self.config,provider=self.provider
        )["status"],"blocked")
        self.provider.unlink()
        self.provider.write_text("wrong file contents")
        self.assertEqual(speaker_gate_status(
            self.installed,config=self.config,provider=self.provider
        )["status"],"blocked")

    def test_same_source_and_installed_directory_refused(self):
        report=assess(self.checkout,self.checkout)
        self.assertEqual(report["status"],"BLOCKED")
        self.assertIn("different",report["blockers"][0])

    def test_preflight_has_no_apply_or_force_option(self):
        source=(ROOT/"tools/jarvis_install_preflight.py").read_text()
        tree=ast.parse(source)
        args=[
            node.args[0].value for node in ast.walk(tree)
            if isinstance(node,ast.Call)
            and isinstance(node.func,ast.Attribute)
            and node.func.attr=="add_argument"
            and node.args and isinstance(node.args[0],ast.Constant)
        ]
        self.assertNotIn("--apply",args)
        self.assertNotIn("--force",args)
        self.assertIn("--json",args)


class VoiceStopPersistenceTests(unittest.TestCase):
    def test_real_listener_interrupt_persists_owner_pause_without_gui(self):
        """Extract actual nested interrupt handler, not a mock rewrite."""
        tree=ast.parse((ROOT/"webbie/agent/webbie.py").read_text())
        listener=next(
            node for node in tree.body
            if isinstance(node,ast.FunctionDef)
            and node.name=="voice_listener")
        handler=next(
            node for node in ast.walk(listener)
            if isinstance(node,ast.FunctionDef)
            and node.name=="on_interrupt")
        calls=[]
        auth=Mock(return_value={"authorized":True})
        saver=Mock(side_effect=lambda *a,**kw: calls.append(("pause",a)))
        scope={
            "is_direct_stop":lambda phrase: phrase=="stop",
            "VOICE_INTAKE":types.SimpleNamespace(count=Mock()),
            "next_window":lambda old,action,now:12,
            "awaiting_command_until":0,
            "coordinator":types.SimpleNamespace(cancel=Mock()),
            "speech_playback":types.SimpleNamespace(stop=Mock()),
            "read_policy":auth,
            "update_policy":saver,
            "request_stop":Mock(),
            "write_state":Mock(),
            "time":time,
        }
        module=ast.fix_missing_locations(ast.Module(body=[handler],
                                                    type_ignores=[]))
        exec(compile(module,"webbie.py","exec"),scope)
        scope["on_interrupt"]("stop")
        saver.assert_called_once_with("pause")
        scope["request_stop"].assert_called_once()
        scope["on_interrupt"]("ignore random instruction")
        saver.assert_called_once()


if __name__=="__main__":
    unittest.main()
