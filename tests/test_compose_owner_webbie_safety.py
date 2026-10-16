"""Owner-private Webbie safety composition tests, no devices or service access."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
spec=importlib.util.spec_from_file_location(
    "spider_safety_webbie_compose",ROOT/"tools/compose_owner_webbie_safety.py")
mod=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=mod
spec.loader.exec_module(mod)


def sample(path):
    return (ROOT/path).read_bytes()


class PrivateWebbieSafetyTests(unittest.TestCase):
    def test_global_stop_is_verified_not_unconditional(self):
        info=mod._stop_gate(sample("the-web/shell/webbie_panel.py"))
        self.assertTrue(info["saved_authorization_rechecked"])
        self.assertTrue(info["resident_and_standalone_mission_stop_supported"])
        candidate=sample("the-web/shell/webbie_panel.py")
        weakened=candidate.replace(b"complete revocation was NOT verified",
                                   b"all controls have been revoked")
        self.assertNotEqual(weakened,candidate)
        with self.assertRaisesRegex(ValueError,"unverified revocation"):
            mod._stop_gate(weakened)

    def test_current_webbie_constructor_retains_all_attributes(self):
        code=sample("the-web/shell/webbie_panel.py")
        verified=mod._critical_constructor(code,code,"WebbiePanel")
        self.assertTrue(verified["owner_state_fields_preserved"])
        local=code.replace(b"self.jarvis_core = JarvisCore()",
                           b"self.owner_controller = JarvisCore()")
        self.assertNotEqual(local,code)
        with self.assertRaisesRegex(ValueError,"drops owner state"):
            mod._critical_constructor(local,code,"WebbiePanel")

    def test_owner_message_and_camera_methods_never_replaced(self):
        candidate=sample("the-web/shell/webbie_panel.py")
        local=candidate.replace(b"    def send(self):",
                                b"    def send(self):\n        self.owner_custom_route = True")
        self.assertNotEqual(local,candidate)
        merged,report=mod.combine_pair("the-web/shell/webbie_panel.py",
                                       local,candidate)
        own=mod._definitions(local)
        made=mod._definitions(merged)
        self.assertEqual(ast.dump(own["WebbiePanel.send"],
                                 include_attributes=False),
                         ast.dump(made["WebbiePanel.send"],
                                 include_attributes=False))
        self.assertIn("WebbiePanel.send",
                      report["preserved_original_sensitive_methods"])
        self.assertFalse(report["install_allowed"])
        self.assertNotIn("owner_custom_route",str(report))

    def test_cognitive_native_callback_and_owner_fallback_both_present(self):
        candidate=sample("the-web/shell/webbie_cognitive_center.py")
        first=b"    def open_workflow(self):"
        legacy=(b"    def offer_workflow(self, args):\n"
                b"        return 'private owner workflow'\n"
                b"    def open_workflows(self):\n"
                b"        return self.offer_workflow(None)\n")
        self.assertIn(first,candidate)
        local=candidate.replace(first,legacy+first)
        merged,record=mod.combine_pair(
            "the-web/shell/webbie_cognitive_center.py",local,candidate)
        tree=mod._definitions(merged)
        self.assertIn("WebbieCognitiveDialog.offer_workflow",tree)
        self.assertIn("WebbieCognitiveDialog.open_workflows",tree)
        flow=tree["WebbieCognitiveDialog.open_workflow"]
        calls={n.attr for n in ast.walk(flow) if isinstance(n,ast.Attribute)}
        self.assertTrue({"workflow_callback","offer_workflow"} <= calls)
        self.assertIn(b"private owner workflow",merged)
        self.assertFalse(record["install_allowed"])
        compile(merged,"webbie_cognitive_center.py","exec")

    def test_cognitive_workflow_callback_precedes_owner_fallback(self):
        public = sample("the-web/shell/webbie_cognitive_center.py")
        original = public.replace(
            b"    def open_workflow(self):",
            b"    def offer_workflow(self, key):\\n"
            b"        return 'legacy fallback'\\n"
            b"    def open_workflows(self):\\n"
            b"        return self.offer_workflow(None)\\n"
            b"    def open_workflow(self):")
        merged, _ = mod.combine_pair(
            "the-web/shell/webbie_cognitive_center.py", original, public)
        node = mod._definitions(merged)["WebbieCognitiveDialog.open_workflow"]
        module = ast.fix_missing_locations(
            ast.Module(body=[node], type_ignores=[]))
        namespace = {}
        exec(compile(module, "<isolated-workflow>", "exec"), namespace)
        open_workflow = namespace["open_workflow"]

        class FakeReport:
            message = None
            def setPlainText(self, message):
                self.message = message

        class FakeDialog:
            workflow_callback = None
            report = FakeReport()
            calls = []
            def offer_workflow(self, key):
                self.calls.append(("legacy", key))
                return "legacy"

        obj = FakeDialog()
        obj.workflow_callback = lambda: obj.calls.append(("native", None)) or "native"
        self.assertEqual(open_workflow(obj), "native")
        self.assertEqual(obj.calls, [("native", None)])

        obj.calls.clear()
        obj.workflow_callback = None
        self.assertEqual(open_workflow(obj), "legacy")
        self.assertEqual(obj.calls, [("legacy", None)])

        obj.offer_workflow = None
        open_workflow(obj)
        self.assertIn("resident Webbie panel", obj.report.message)

    def test_full_private_stage_compiles_both_without_touching_installed(self):
        with tempfile.TemporaryDirectory() as home_dir:
            home=Path(home_dir)
            stage=home/"PrivateLivePairs"
            stage.mkdir(mode=0o700)
            entries=[]
            for name in mod.DESKTOP:
                current=sample(name)
                old=current
                if name.endswith("webbie_cognitive_center.py"):
                    old=current.replace(
                        b"    def open_workflow(self):",
                        b"    def offer_workflow(self, args):\n"
                        b"        return 'private user workflow'\n"
                        b"    def open_workflows(self):\n"
                        b"        return self.offer_workflow(None)\n"
                        b"    def open_workflow(self):")
                for scope,data in (("installed",old),
                                   ("candidate",current)):
                    p=stage/scope/name
                    p.parent.mkdir(parents=True,exist_ok=True)
                    p.write_bytes(data)
                    p.chmod(0o600)
                entries.append({
                    "component":name,
                    "installed_sha256":hashlib.sha256(old).hexdigest(),
                    "candidate_sha256":hashlib.sha256(current).hexdigest()})
            manifest=stage/"manifest.json"
            manifest.write_text(json.dumps({
                "format":"spider-native-private-merge-stage-v1",
                "focus":"desktop","release_installable":False,
                "files":entries,
            }))
            manifest.chmod(0o600)
            output=home/"WebbiePrivateMerge"
            report=mod.compose(stage,output,home=home)
            self.assertEqual(len(report["files"]),2)
            self.assertFalse(report["release_installable"])
            self.assertFalse(report["safe_to_overwrite"])
            self.assertTrue(report["source_snapshot_verified"])
            self.assertEqual(output.stat().st_mode & 0o777,0o700)
            for name in mod.WEBBIE_FILES:
                written=output/"candidate"/name
                self.assertEqual(written.stat().st_mode & 0o777,0o600)
                compile(written.read_bytes(),name,"exec")
            with self.assertRaises(ValueError):
                mod.compose(stage,output,home=home)
            for name in mod.WEBBIE_FILES:
                self.assertEqual((stage/"candidate"/name).read_bytes(),
                                 sample(name))
            self.assertNotIn("private user workflow",
                             (output/"summary.json").read_text())

    def test_refuses_unverified_old_webbie_stage(self):
        # All five candidate files must exist and be individually well-formed
        # to exercise the STALE-stage check, rather than missing-source error.
        with tempfile.TemporaryDirectory() as root:
            here=Path(root)
            source=here/"src"
            source.mkdir()
            stage=here/"private"
            stage.mkdir()
            for rel in mod.DESKTOP:
                current=sample(rel)
                live=source/rel
                live.parent.mkdir(parents=True,exist_ok=True)
                live.write_bytes(current)
                saved=stage/"candidate"/rel
                saved.parent.mkdir(parents=True,exist_ok=True)
                saved.write_bytes(current+(b"\n# stale\n" if rel==mod.DESKTOP[0] else b""))
            with self.assertRaisesRegex(ValueError,"OLD STAGE"):
                mod._check_live_candidate_snapshot(stage,source)

    def test_no_install_commands_in_webbie_composer(self):
        source=sample("tools/compose_owner_webbie_safety.py").decode()
        for unsafe in ("subprocess", "sudo ", "systemctl ", "git push",
                       "requests.", "urlopen(", "os.system(", "apt install",
                       "shutil.copytree(", "os.replace("):
            self.assertNotIn(unsafe,source)


if __name__=="__main__":
    unittest.main()
