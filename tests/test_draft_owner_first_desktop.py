"""Local-first desktop preview regression tests: never overwrite owner methods."""
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
    "spider_owner_first_review",ROOT/"tools/draft_owner_first_desktop.py")
tool=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=tool
spec.loader.exec_module(tool)


class OwnerFirstReviewTests(unittest.TestCase):
    def test_preserves_owner_method_bodies_while_adding_candidate_unique_gui(self):
        owner=b"""from live_owner_bridge import working_local
APP_NAME = 'OWNER, PRESERVE EXACTLY'
class TheWeb:
    def __init__(self):
        self.native = working_local()
    def open_workspace(self, name):
        return 'PRIVATE EXISTING WORKFLOW'
def old_control():
    return 1
"""
        candidate=b"""from home_dashboard import SpiderHomeDashboard
APP_NAME = 'CANDIDATE, DO NOT REPLACE'
ADDED_NUMBER = 20
class TheWeb:
    def __init__(self):
        self.home = SpiderHomeDashboard()
    def open_workspace(self, name):
        return 'NEW WORKFLOW'
    def open_new_instrument(self):
        return SpiderHomeDashboard()
def candidate_purpose():
    return 2
"""
        combined,report=tool._stitch(owner,candidate,"the-web/shell/main.py")
        out=combined.decode("utf-8")
        self.assertIn("PRIVATE EXISTING WORKFLOW",out)
        self.assertNotIn("NEW WORKFLOW",out)
        self.assertIn("APP_NAME = 'OWNER, PRESERVE EXACTLY'",out)
        self.assertNotIn("APP_NAME = 'CANDIDATE, DO NOT REPLACE'",out)
        self.assertIn("from home_dashboard import SpiderHomeDashboard",out)
        self.assertIn("def open_new_instrument(self)",out)
        self.assertIn("def candidate_purpose()",out)
        self.assertIn("ADDED_NUMBER = 20",out)
        self.assertIn("TheWeb.open_workspace", report["unresolved_conflicts"])
        self.assertIn("TheWeb.__init__",report["unresolved_conflicts"])
        self.assertFalse(report["install_allowed"])
        self.assertNotIn("PRIVATE EXISTING WORKFLOW",str(report))
        ast.parse(out)

    def test_preserves_local_webbie_workflows_and_candidate_only_worker(self):
        owner=b"""from trusted_local_flow import safe_default
class WebbieCognitiveDialog:
    def __init__(self):
        self.workflow_dialog = safe_default
    def offer_workflow(self):
        return self.workflow_dialog
    def open_workflows(self):
        return self.offer_workflow()
    def open_workflow(self):
        return 'OWNER PERMISSION PATH'
"""
        candidate=b"""from generic_controls import new_worker
class WebbieCognitiveDialog:
    def __init__(self):
        self.workflow_callback = new_worker
    def open_workflow(self):
        return 'CANDIDATE PERMISSION PATH'
    def read_only_diagnostics(self):
        return True
class NewWorker:
    def run(self):
        return 'new feature'
"""
        joined,report=tool._stitch(owner,candidate,"webbie_cognitive_center.py")
        result=joined.decode()
        self.assertIn("def offer_workflow(self):",result)
        self.assertIn("def open_workflows(self):",result)
        self.assertIn("OWNER PERMISSION PATH",result)
        self.assertNotIn("CANDIDATE PERMISSION PATH",result)
        self.assertIn("class NewWorker:",result)
        self.assertIn("def read_only_diagnostics(self):",result)
        self.assertIn("WebbieCognitiveDialog.open_workflow",
                      report["unresolved_conflicts"])
        self.assertFalse(report["install_allowed"])
        ast.parse(joined)

    def test_cannot_silently_drop_existing_class_method_body(self):
        owner=b"""class A:
    def existing(self):
        return 100
"""
        incoming=b"""class A:
    def existing(self):
        return 200
    @staticmethod
    def added():
        return 3
"""
        merged,notes=tool._stitch(owner,incoming,"test.py")
        self.assertIn("return 100",merged.decode())
        self.assertNotIn("return 200",merged.decode())
        self.assertIn("@staticmethod\n    def added():",merged.decode())
        self.assertEqual(notes["unresolved_conflicts"], ["A.existing"])

    def test_private_stage_gate_and_outputs_are_owner_only(self):
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder)
            stage=home/"StagedOriginals"
            stage.mkdir(mode=0o700)
            installed=b"def owner():\n    return 'MY PRIVATE SOURCE'\n"
            candidate=b"def candidate():\n    return 1\n"
            entries=[]
            for name in tool.DESKTOP:
                for label,data in (("installed",installed),
                                   ("candidate",candidate)):
                    file=stage/label/name
                    file.parent.mkdir(parents=True,exist_ok=True)
                    file.write_bytes(data)
                    file.chmod(0o600)
                entries.append({
                    "component":name,
                    "installed_sha256":hashlib.sha256(installed).hexdigest(),
                    "candidate_sha256":hashlib.sha256(candidate).hexdigest(),
                })
            manifest=stage/"manifest.json"
            manifest.write_text(json.dumps({
                "format":"spider-native-private-merge-stage-v1",
                "focus":"desktop", "release_installable":False,
                "files":entries,
            }))
            manifest.chmod(0o600)
            output=home/"OwnerFirst"
            result=tool.stage_local_first(stage,output,home=home)
            self.assertFalse(result["release_installable"])
            self.assertFalse(result["safe_to_overwrite"])
            self.assertEqual(output.stat().st_mode & 0o777, 0o700)
            for name in tool.DESKTOP:
                preview=output/"review-only"/name
                self.assertEqual(preview.stat().st_mode & 0o777, 0o600)
                self.assertIn(b"MY PRIVATE SOURCE",preview.read_bytes())
                self.assertEqual((stage/"installed"/name).read_bytes(),
                                 installed)
            self.assertNotIn("MY PRIVATE SOURCE",
                             (output/"summary.json").read_text())
            with self.assertRaises(ValueError):
                tool.stage_local_first(stage,output,home=home)

    def test_missing_imports_cannot_precede_future_header(self):
        installed=b"""# header
from __future__ import annotations
import os
def local(): pass
"""
        candidate=b"""from __future__ import annotations
from dataclasses import dataclass
def local(): pass
@dataclass
class C:
    thing: str
"""
        merged,result=tool._stitch(installed,candidate,"main.py")
        parsed=ast.parse(merged)
        self.assertEqual(parsed.body[0].module,"__future__")
        self.assertIn(b"from dataclasses import dataclass",merged)
        self.assertIn(b"@dataclass\nclass C:",merged)

    def test_does_not_execute_install_or_upload(self):
        src=(ROOT/"tools/draft_owner_first_desktop.py").read_text()
        for phrase in ("subprocess.Popen(", "os.system(", "sudo ",
                       "git push", "requests.", "urlopen(", "apt install",
                       "systemctl ", "shutil.copytree("):
            self.assertNotIn(phrase,src)


if __name__=="__main__":
    unittest.main()
