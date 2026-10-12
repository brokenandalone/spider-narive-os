"""JARVIS Workflow Board is a bounded, non-automating owner checklist."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "webbie/agent"))
from workflow_board import (
    BLUEPRINTS, MAX_SECONDS, WORKSPACES, WorkflowSession, blueprint_for,
)


class WorkflowPlanTests(unittest.TestCase):
    def test_all_workflows_use_fixed_native_workspaces_with_bounded_steps(self):
        self.assertGreaterEqual(len(BLUEPRINTS), 5)
        for template in BLUEPRINTS:
            with self.subTest(plan=template.key):
                self.assertIs(blueprint_for(template.key), template)
                self.assertTrue(1 <= len(template.steps) <= 6)
                for step in template.steps:
                    self.assertIn(step.workspace, WORKSPACES)
                    self.assertTrue(step.title and step.instruction)

    def test_no_arbitrary_model_or_injected_commands(self):
        for text in ("studio;rm -rf /", "https://example.org", "../../tmp",
                     "Record then auto publish", "", None, ["recording"]):
            with self.subTest(value=text), self.assertRaises(ValueError):
                blueprint_for(text)
        source = (ROOT / "webbie/agent/workflow_board.py").read_text()
        for forbidden in ("subprocess", "eval(", "exec(", "os.system",
                          "shell=True", "xdotool", "keyboard.type"):
            self.assertNotIn(forbidden, source)

    def test_unapproved_start_never_begins(self):
        flow = WorkflowSession(clock=lambda: 20)
        with self.assertRaises(PermissionError):
            flow.begin("school")
        self.assertFalse(flow.status()["active"])

    def test_only_explicit_sequential_owner_confirmations_advance(self):
        now = [40.]
        flow = WorkflowSession(clock=lambda: now[0])
        item = flow.begin("school", owner_approved=True)
        self.assertEqual(item.workspace, "study")
        self.assertEqual(flow.status()["step"], 1)
        with self.assertRaises(PermissionError):
            flow.complete(expected_position=0)
        with self.assertRaises(ValueError):
            flow.complete(owner_confirmed=True, expected_position=1)
        self.assertEqual(flow.status()["step"], 1)
        next_item = flow.complete(owner_confirmed=True, expected_position=0)
        self.assertEqual(next_item.workspace, "deep-forage")
        self.assertEqual(flow.status()["step"], 2)
        flow.cancel()
        self.assertFalse(flow.status()["active"])

    def test_bound_duration_and_expiration(self):
        now = [100.]
        flow = WorkflowSession(clock=lambda: now[0])
        with self.assertRaises(ValueError):
            flow.begin("recording", owner_approved=True, seconds=MAX_SECONDS+1)
        with self.assertRaises(ValueError):
            flow.begin("recording", owner_approved=True, seconds=True)
        flow.begin("recording", owner_approved=True, seconds=3)
        now[0] = 103.
        self.assertIsNone(flow.current())
        self.assertFalse(flow.status()["active"])
        self.assertIsNone(flow.complete(owner_confirmed=True, expected_position=0))

    def test_new_owner_approved_workflow_replaces_old(self):
        flow = WorkflowSession(clock=lambda: 20)
        flow.begin("canon", owner_approved=True)
        flow.complete(owner_confirmed=True, expected_position=0)
        flow.begin("maintenance", owner_approved=True)
        self.assertEqual(flow.status()["workspace"], "system")
        self.assertEqual(flow.status()["step"], 1)

    def test_stops_at_last_step_without_implicit_followup(self):
        flow = WorkflowSession(clock=lambda: 20)
        plan = blueprint_for("broadcast")
        flow.begin("broadcast", owner_approved=True)
        for pos in range(len(plan.steps)):
            flow.complete(owner_confirmed=True, expected_position=pos)
        self.assertFalse(flow.status()["active"])
        self.assertIsNone(flow.current())


if __name__ == "__main__":
    unittest.main()
