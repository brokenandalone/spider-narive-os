"""Future regression checks for manual-only Spider Operations projects."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "system"))
from operations_wave8_projects import (
    SCHEMA, TEMPLATES, new_plan, mark_step, plan_summary, save_plan, load_plan,
)


class LocalProjectPlans(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)

    def test_all_fixed_templates_are_bounded(self):
        for name in TEMPLATES:
            plan = new_plan(name, "A private project")
            self.assertEqual(plan["schema"], SCHEMA)
            self.assertGreaterEqual(len(plan["steps"]), 1)
            self.assertLessEqual(len(plan["steps"]), 6)
            self.assertFalse(any(x["complete"] for x in plan["steps"]))

    def test_mark_step_does_not_mutate_original(self):
        plan = new_plan("record_song", "Band session")
        changed = mark_step(plan, 0, True)
        self.assertFalse(plan["steps"][0]["complete"])
        self.assertTrue(changed["steps"][0]["complete"])
        self.assertEqual(plan_summary(changed)["tasks_remaining"], 5)

    def test_exclusive_private_save_and_reload(self):
        plan = new_plan("finish_assignment", "PSY project")
        source = self.folder / "plan.json"
        save_plan(plan, source)
        self.assertEqual(load_plan(source)["title"], "PSY project")
        self.assertEqual(os.stat(source).st_mode & 0o777, 0o600)
        with self.assertRaises(ValueError):
            save_plan(plan, source)

    def test_refuses_dynamic_templates_and_steps(self):
        with self.assertRaises(ValueError):
            new_plan("execute_shell", "Anything")
        plan = new_plan("write_chapter", "Broken City")
        plan["steps"][0]["title"] = "Run arbitrary command"
        path = self.folder / "unsafe.json"
        path.write_text(json.dumps(plan), encoding="utf-8")
        with self.assertRaises(ValueError):
            load_plan(path)

    def test_refuses_symlinked_save(self):
        plan = new_plan("system_release", "OS")
        ordinary = self.folder / "original.json"
        ordinary.write_text("protected", encoding="utf-8")
        symlink = self.folder / "link.json"
        symlink.symlink_to(ordinary)
        with self.assertRaises(ValueError):
            save_plan(plan, symlink)
        self.assertEqual(ordinary.read_text(), "protected")


if __name__ == "__main__":
    unittest.main()
