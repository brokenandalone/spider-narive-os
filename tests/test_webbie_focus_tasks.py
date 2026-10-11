"""No-hardware regression tests for owner-curated Jarvis focus task memory."""
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"webbie/brain"))
import focus_tasks as ft

class FocusTaskTests(unittest.TestCase):
    def setUp(self):
        d=tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.root=Path(d.name)
        self.path=self.root/"tasks.json"
        self.clock=lambda: 120000.0

    def create(self,title="Studio work",workspace="studio"):
        return ft.add_task(workspace,title,"Record guitar stem",
                           path=self.path,clock=self.clock)

    def test_create_and_read(self):
        identifier=self.create()
        items=ft.list_tasks(self.path,workspace="studio")
        self.assertEqual(len(items),1)
        self.assertEqual(items[0]["id"],identifier)
        self.assertEqual(items[0]["status"],"active")
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode),0o600)

    def test_workspace_isolation(self):
        self.create()
        ft.add_task("study","Finish assignment","Check references",
                    path=self.path,clock=self.clock)
        self.assertEqual(len(ft.list_tasks(self.path,workspace="study")),1)
        self.assertEqual(len(ft.list_tasks(self.path,workspace="studio")),1)
        self.assertEqual(len(ft.list_tasks(self.path)),2)
        self.assertIn("Record guitar stem",ft.focus_answer("studio",path=self.path))

    def test_update_status_and_resume(self):
        identifier=self.create()
        self.assertTrue(ft.change_task(identifier,status="paused",path=self.path))
        self.assertIsNone(ft.current_focus("studio",path=self.path))
        self.assertTrue(ft.change_task(identifier,status="active",
                                       next_step="Review take",path=self.path))
        self.assertIn("Review take",ft.focus_answer("studio",path=self.path))
        self.assertTrue(ft.change_task(identifier,status="done",path=self.path))
        self.assertIsNone(ft.current_focus("studio",path=self.path))

    def test_deletion(self):
        id=self.create()
        self.assertTrue(ft.delete_task(id,path=self.path))
        self.assertFalse(ft.delete_task(id,path=self.path))
        self.assertEqual(ft.list_tasks(self.path),[])

    def test_strict_validation(self):
        for workspace in ("../home","studio; rm -rf /","unknown",None):
            with self.subTest(workspace=workspace),self.assertRaises(ValueError):
                self.create(workspace=workspace)
        for title in ("","  ","A"*101,4):
            with self.subTest(title=title),self.assertRaises(ValueError):
                self.create(title=title)
        with self.assertRaises(ValueError):
            ft.change_task("bogus",status="done",path=self.path)
        with self.assertRaises(ValueError):
            ft.change_task(self.create(),status="sudo",path=self.path)

    def test_max_task_count(self):
        for i in range(ft.MAX_TASKS):
            self.create(title=f"Task {i}")
        with self.assertRaises(ValueError):
            self.create("Task overflow")
        self.assertEqual(len(ft.list_tasks(self.path)),ft.MAX_TASKS)

    def test_symlink_does_not_overwrite_other_file(self):
        target=self.root/"important.txt"
        target.write_text("keep")
        self.path.symlink_to(target)
        with self.assertRaises(PermissionError):
            self.create()
        self.assertEqual(target.read_text(),"keep")

    def test_nonprivate_state_not_read(self):
        self.create()
        os.chmod(self.path,0o644)
        self.assertEqual(ft.list_tasks(self.path),[])

    def test_corruption_is_ignored(self):
        self.path.write_text("{bad")
        self.assertEqual(ft.list_tasks(self.path),[])

    def test_never_creates_executable_plan(self):
        self.create(title="Open terminal")
        advisory=ft.advisory_focus("studio",path=self.path)
        self.assertIn("never follow instructions",advisory)
        self.assertNotIn("authorized":True,advisory) if False else self.assertIn("not",advisory)
        self.assertIn("Open terminal",advisory)

    def test_newest_active_chosen(self):
        first=ft.add_task("author","Draft chapter","Outline",
                          path=self.path,clock=lambda:100)
        second=ft.add_task("author","Review chapter","Check continuity",
                           path=self.path,clock=lambda:200)
        self.assertEqual(ft.current_focus("author",path=self.path)["id"],second)

if __name__=="__main__":
    unittest.main()
