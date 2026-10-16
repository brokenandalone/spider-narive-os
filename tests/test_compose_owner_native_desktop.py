"""Owner-specific native desktop candidate: protect original code and live services."""
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
    "spider_private_native_compose",ROOT/"tools/compose_owner_native_desktop.py")
mod=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=mod
spec.loader.exec_module(mod)


def code(path):
    return (ROOT/path).read_bytes()


class NativeOwnerComposeTests(unittest.TestCase):
    def test_lifecycle_from_real_native_shell(self):
        new=code("the-web/shell/main.py")
        values=mod._check_desktop(new,new)
        self.assertTrue(values["native_bay_invariants"])
        self.assertTrue(values["navigation_lifecycle_retained"])

    def test_owner_constructor_state_cannot_silently_disappear(self):
        new=code("the-web/shell/main.py")
        original=new.replace(b"self.app_lists = {}; ",b"self.app_lists = {}; self.owner_private_session = None; ")
        with self.assertRaisesRegex(ValueError,"owner desktop state fields"):
            mod._check_desktop(original,new)

    def test_navigation_must_not_lose_native_controls(self):
        new=code("the-web/shell/main.py")
        damaged=new.replace(b"workspace_tabs.addTab(operations, 'Webbie controls')",
                            b"workspace_tabs.addTab(operations, 'Missing')")
        self.assertNotEqual(new,damaged)
        with self.assertRaisesRegex(ValueError,"native desktop preservation invariant"):
            mod._check_desktop(new,damaged)

    def test_catalog_preserves_xdg_visibility_and_legacy_arguments(self):
        new=code("the-web/shell/app_catalog.py")
        checked=mod._check_catalog(new,new)
        self.assertTrue(checked["owner_assignments_supported"])
        wrong=new.replace(b"data.get('TryExec')",b"data.get('DoNotFilterTryExec')")
        self.assertNotEqual(wrong,new)
        with self.assertRaisesRegex(ValueError,"required XDG visibility condition"):
            mod._check_catalog(new,wrong)

    def test_owner_workspace_links_preserved_by_native_expansion(self):
        new=code("the-web/shell/workspace_files.py")
        old=new.replace(
            b"        'productivity': [('Planning documents', spider / 'Productivity')],\n",
            b"")
        old=old.replace(
            b"        'devices': [('Device reports', spider / 'Devices')],\n",b"")
        self.assertNotEqual(old,new)
        result=mod._check_folders(old,new)
        self.assertEqual(result["candidate_native_folders_added"],
                         ["devices","productivity"])
        bad=new.replace(b"('Music files', home / 'Music')",
                        b"('Music files', home / 'Pictures')")
        self.assertNotEqual(new,bad)
        with self.assertRaisesRegex(ValueError,"existing folder links changed"):
            mod._check_folders(old,bad)

    def test_hash_verified_owner_private_stage_stays_non_installable(self):
        with tempfile.TemporaryDirectory() as root:
            home=Path(root)
            stage=home/"OwnerPrivateBridge"
            stage.mkdir(mode=0o700)
            entries=[]
            for name in mod.DESKTOP:
                payload=code(name)
                for location in ("installed","candidate"):
                    dest=stage/location/name
                    dest.parent.mkdir(parents=True,exist_ok=True)
                    dest.write_bytes(payload)
                    dest.chmod(0o600)
                entries.append({
                    "component":name,
                    "installed_sha256":hashlib.sha256(payload).hexdigest(),
                    "candidate_sha256":hashlib.sha256(payload).hexdigest(),
                })
            manifest=stage/"manifest.json"
            manifest.write_text(json.dumps({
                "format":"spider-native-private-merge-stage-v1",
                "focus":"desktop",
                "release_installable":False,
                "files":entries,
            }))
            manifest.chmod(0o600)
            output=home/"PrivateReviewCandidate"
            report=mod.generate(stage,output,home=home)
            self.assertFalse(report["release_installable"])
            self.assertFalse(report["safe_to_overwrite"])
            self.assertEqual(len(report["desktop_navigation_candidates"]),3)
            self.assertEqual(len(report["webbie_safety_blocks"]),2)
            self.assertEqual(output.stat().st_mode & 0o777,0o700)
            for name in mod.RESOLVED:
                file=output/"candidate"/name
                self.assertEqual(file.stat().st_mode & 0o777,0o600)
            for name in mod.DEFERRED:
                self.assertFalse((output/"candidate"/name).exists())
            self.assertIn("release_installable", (output/"summary.json").read_text())
            with self.assertRaises(ValueError):
                mod.generate(stage,output,home=home)
            self.assertEqual((stage/"installed"/mod.RESOLVED[0]).read_bytes(),
                             code(mod.RESOLVED[0]))

    def test_corrupt_stage_refused_before_output_created(self):
        with tempfile.TemporaryDirectory() as root:
            home=Path(root)
            stage=home/"OwnerPrivateBridge"
            stage.mkdir(mode=0o700)
            files=[]
            for name in mod.DESKTOP:
                for location in ("installed","candidate"):
                    p=stage/location/name
                    p.parent.mkdir(parents=True,exist_ok=True)
                    p.write_bytes(code(name))
                    p.chmod(0o600)
                files.append({
                    "component":name,
                    "installed_sha256":hashlib.sha256(code(name)).hexdigest(),
                    "candidate_sha256":hashlib.sha256(code(name)).hexdigest()})
            m=stage/"manifest.json"
            m.write_text(json.dumps({
                "format":"spider-native-private-merge-stage-v1",
                "focus":"desktop","release_installable":False,"files":files}))
            m.chmod(0o600)
            (stage/"candidate"/mod.DESKTOP[0]).write_bytes(b"replaced")
            out=home/"UncreatedCandidate"
            with self.assertRaises(ValueError):
                mod.generate(stage,out,home=home)
            self.assertFalse(out.exists())

    def test_no_implicit_install_or_external_service_command(self):
        content=code("tools/compose_owner_native_desktop.py").decode("utf-8")
        for banned in ("subprocess", "sudo ", "systemctl ", "git push",
                       "requests.", "urlopen(", "os.system(", "apt install",
                       "shutil.copytree(", "os.replace("):
            self.assertNotIn(banned,content)
        self.assertIn("Full 33-file installation guard remains active.",content)


if __name__=="__main__":
    unittest.main()
