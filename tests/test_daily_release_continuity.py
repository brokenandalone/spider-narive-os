"""Spider OS daily release continuity contract, entirely in disposable trees."""
import copy
from datetime import datetime
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "spider_daily_continuity_tests", ROOT / "tools/daily_release_continuity.py"
)
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)
BASE_PLAN = json.loads((ROOT / "system/daily_release_plan_20261011.json").read_text())
TODAY = datetime(2026, 10, 11, 16, 0, tzinfo=ZoneInfo("America/Indiana/Indianapolis"))


class DailyContinuityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.staged = self.folder / "checkout"
        self.backups = self.folder / "backups"
        self.staged.mkdir()
        self.plan = copy.deepcopy(BASE_PLAN)

    def stage_complete_fixture(self):
        for component in self.plan["workspaces"]:
            for path in component["required_files"]:
                target = self.staged / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("# synthetic release candidate\n")
        batch = self.staged / "system/release_batch.py"
        sources = sorted({
            path for group in self.plan["workspaces"]
            for path in group["required_files"]
            if not path.startswith(("system/", "tools/"))
        })
        batch.write_text("APP_FILES = " + repr(tuple(sources))
                         + "\n# daily_install_guard(backup_root)\n")
        shutil.copyfile(ROOT / "system/daily_install_policy.py",
                        self.staged / "system/daily_install_policy.py")

    def ready_plan(self):
        self.plan["candidate_commit"] = "a" * 40
        for flag in ("source_ci_verified", "installed_pc_reconciled",
                     "rollback_validated", "owner_approved_install",
                     "installer_daily_guard_connected"):
            self.plan[flag] = True
        for entry in self.plan["pull_requests"]:
            entry["integrated"] = True
        self.plan["resolved_shared_paths"] = [
            {"path": name, "pull_requests": ids, "reviewed": True}
            for name, ids in gate.overlapping_paths(self.plan).items()
        ]
        self.stage_complete_fixture()

    def test_real_october_plan_is_blocked_for_valid_reasons(self):
        blocked, notes = gate.audit(self.plan, ROOT, now=TODAY)
        self.assertTrue(any("NOT YET INTEGRATED" in msg for msg in blocked))
        self.assertTrue(any("UNRESOLVED CROSS-BRANCH OVERLAP" in msg
                            for msg in blocked))
        self.assertTrue(any("DAILY RECEIPT STATUS UNVERIFIED" in msg
                            for msg in blocked))
        self.assertTrue(any("Tracked system workspaces: 9" in msg for msg in notes))

    def test_simulated_fully_reviewed_release_and_empty_backup_can_pass(self):
        self.ready_plan()
        blocked, _ = gate.audit(self.plan, self.staged, self.backups, TODAY)
        self.assertEqual(blocked, [])

    def test_missing_workspace_or_unmerged_branch_blocks(self):
        self.ready_plan()
        self.plan["workspaces"] = [
            x for x in self.plan["workspaces"] if x["name"] != "Kali Bay"
        ]
        errors, _ = gate.audit(self.plan, self.staged, self.backups, TODAY)
        self.assertIn("MISSING SYSTEM WORKSPACE: Kali Bay", errors)
        self.ready_plan()
        self.plan["pull_requests"][1]["integrated"] = False
        errors, _ = gate.audit(self.plan, self.staged, self.backups, TODAY)
        self.assertTrue(any("NOT YET INTEGRATED" in e for e in errors))

    def test_shared_entrypoints_require_explicit_cross_branch_review(self):
        self.ready_plan()
        self.assertEqual(
            gate.overlapping_paths(self.plan)["webbie/agent/webbie.py"],
            [54, 55, 58, 61],
        )
        self.plan["resolved_shared_paths"] = []
        errors, _ = gate.audit(self.plan, self.staged, self.backups, TODAY)
        self.assertTrue(any("webbie/agent/webbie.py" in e for e in errors))
        self.assertTrue(any("system/release_batch.py" in e for e in errors))

    def test_daily_limit_one_and_pc_proof_are_fail_closed(self):
        self.ready_plan()
        self.plan["max_system_installs_per_local_day"] = 2
        self.plan["installed_pc_reconciled"] = False
        errors, _ = gate.audit(self.plan, self.staged, self.backups, TODAY)
        self.assertIn("DAILY INSTALL LIMIT MUST BE ONE", errors)
        self.assertIn("INSTALLED PC CUSTOMIZATIONS NOT RECONCILED", errors)

    def test_missing_selected_source_or_batch_manifest_blocks(self):
        self.ready_plan()
        (self.staged / "study/flashcards.py").unlink()
        errors, _ = gate.audit(self.plan, self.staged, self.backups, TODAY)
        self.assertIn("MISSING IN CANDIDATE: study/flashcards.py", errors)

    def test_receipt_blocks_repeat_system_install(self):
        self.ready_plan()
        stamp = self.backups / "spider-batch-20261011-154500-000000"
        stamp.mkdir(parents=True)
        (stamp / "manifest.json").write_text('{"version":1,"files":[]}')
        errors, _ = gate.audit(self.plan, self.staged, self.backups, TODAY)
        self.assertIn("DAILY INSTALL SLOT ALREADY USED OR AMBIGUOUS", errors)

    def test_wrong_date_or_missing_verified_installer_hook_blocks(self):
        self.ready_plan()
        future = datetime(2026, 10, 12, 9, 0,
                          tzinfo=ZoneInfo("America/Indiana/Indianapolis"))
        errors, _ = gate.audit(self.plan, self.staged, self.backups, future)
        self.assertIn("RELEASE DAY DOES NOT MATCH OWNER LOCAL DAY", errors)
        file = self.staged / "system/release_batch.py"
        file.write_text(file.read_text().replace("daily_install_guard(backup_root)",
                                                 "installer_guard_not_connected"))
        errors, _ = gate.audit(self.plan, self.staged, self.backups, TODAY)
        self.assertIn("DAILY GUARD NOT WIRED TO MAIN BATCH INSTALLER", errors)


if __name__ == "__main__":
    unittest.main()
