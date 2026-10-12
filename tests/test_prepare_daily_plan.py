"""Next-day Spider OS release plans NEVER copy approvals from yesterday."""
from datetime import date, datetime
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("spider_new_day_test", ROOT/"tools/prepare_daily_plan.py")
planmod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(planmod)
S = importlib.util.spec_from_file_location("spider_batch_nextday_test", ROOT/"system/release_batch.py")
batch = importlib.util.module_from_spec(S)
sys.modules[S.name] = batch
S.loader.exec_module(batch)


class NewDailyPlanTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        (self.root/"system").mkdir()
        self.old = self.root/"system/daily_release_plan_20261011.json"
        self.old.write_text(json.dumps({
            "schema_version": 1, "release_date": "2026-10-11",
            "timezone": "America/Indiana/Indianapolis",
            "candidate_commit": "f"*40, "source_ci_verified": True,
            "installed_pc_reconciled": True, "rollback_validated": True,
            "owner_approved_install": True, "installer_daily_guard_connected": True,
            "voice_pipeline_verified": True, "model_compatibility_verified": True,
            "max_system_installs_per_local_day": 1,
            "resolved_shared_paths": [{"path": "webbie.py", "reviewed": True}],
            "workspaces": [{"name": "Webbie"}], "pull_requests": [],
        }))

    def test_day_rollover_revokes_every_permission(self):
        nextday = date(2026, 10, 12)
        newpath = planmod.prepare(root=self.root, day=nextday)
        self.assertEqual(newpath.name, "daily_release_plan_20261012.json")
        updated = json.loads(newpath.read_text())
        self.assertEqual(updated["release_date"], "2026-10-12")
        self.assertEqual(updated["candidate_commit"], None)
        self.assertEqual(updated["resolved_shared_paths"], [])
        for key in planmod.FLAGS:
            self.assertIs(updated[key], False, key)
        self.assertEqual(updated["max_system_installs_per_local_day"], 1)
        self.assertEqual(batch.daily_manifest_path(self.root, nextday), newpath)
        self.assertTrue(json.loads(self.old.read_text())["owner_approved_install"])

    def test_cannot_overwrite_existing_daily_manifest(self):
        day = date(2026, 10, 12)
        planmod.prepare(root=self.root, day=day)
        with self.assertRaisesRegex(ValueError, "already exists"):
            planmod.prepare(root=self.root, day=day)

    def test_without_new_plan_installer_returns_only_stale_diagnostic(self):
        stale = batch.daily_manifest_path(self.root, date(2026,10,12))
        self.assertEqual(stale, self.old)
        current = json.loads(stale.read_text())
        self.assertNotEqual(current["release_date"], "2026-10-12")

    def test_timezone_is_explicit_not_system_utc(self):
        instant = datetime(2026,10,12,2,30,tzinfo=ZoneInfo("UTC"))
        self.assertEqual(planmod.current_day(instant), date(2026,10,11))


if __name__ == "__main__":
    unittest.main()
