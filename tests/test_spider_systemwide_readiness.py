"""Wave Five protected release gates; tests never touch real PC hardware."""
import importlib.util
import json
import shutil
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "systemwide_ready_test", ROOT / "tools/spider_systemwide_readiness.py")
ready = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ready)


class SystemwideReadinessTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.source = Path(temp.name) / "source"
        self.live = Path(temp.name) / "live"
        self.source.mkdir()
        self.live.mkdir()
        self.paths = list(ready.GUARDED)
        for root in (self.source, self.live):
            for name in self.paths:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("original fixture\n")
        self.source.joinpath("system").mkdir()
        shutil.copyfile(ROOT / "system/daily_install_policy.py",
                        self.source / "system/daily_install_policy.py")
        self.release = self.source / ready.BATCH
        self.plan = self.source / ready.PLAN
        self.save_manifest()
        self.write_plan()

    def save_manifest(self, extras=()):
        self.release.write_text("APP_FILES = " + repr(tuple(self.paths + list(extras))) + "\n")
        for path in extras:
            target = self.source / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("extra module\n")

    def write_plan(self, **override):
        gates = {x: True for x in ready.RELEASE_GATES}
        gates.update({"workspaces": [{"name": "The Web"}], "pull_requests": []})
        gates.update(override)
        self.plan.write_text(json.dumps(gates))

    def test_matching_pc_remains_review_only(self):
        report = ready.inspect(self.source, self.live, scan_pc=True,
                               model_checker=lambda *a: "MODEL_SMOKE_PASSED_REVIEW_STILL_REQUIRED")
        self.assertEqual(report["status"], "REVIEW_ONLY")
        self.assertEqual(report["counts"]["pc_matches"], len(self.paths))
        self.assertFalse(report["installation_ready"])

    def test_modified_live_webbie_never_counts_as_matching(self):
        path = self.live / "webbie/brain/brain.py"
        path.write_text("newer owner customized model selector\n")
        report = ready.inspect(self.source, self.live, scan_pc=True,
                               model_checker=lambda *a: "REVIEW_REQUIRED")
        self.assertEqual(report["critical_files"]["webbie/brain/brain.py"], "different")
        self.assertFalse(report["installation_ready"])
        self.assertTrue(any("reconcile" in s for s in report["warnings"]))

    def test_model_not_verified_blocks(self):
        report = ready.inspect(self.source, self.live, scan_pc=True,
                               model_checker=lambda *a: "BLOCKED")
        self.assertEqual(report["status"], "BLOCKED")
        self.assertTrue(any("model" in s.lower() for s in report["blockers"]))

    def test_secret_or_private_manifest_path_blocks(self):
        self.save_manifest(["webbie/config/default.json"])
        report = ready.inspect(self.source)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertTrue(any("protected" in s for s in report["blockers"]))

    def test_repeated_manifest_path_blocks(self):
        self.save_manifest([self.paths[0]])
        report = ready.inspect(self.source)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertTrue(any("Duplicate" in s for s in report["blockers"]))

    def test_missing_or_symlinked_source_blocks(self):
        (self.source / "webbie/agent/webbie.py").unlink()
        report = ready.inspect(self.source)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertGreater(report["counts"]["candidate_missing_or_unsafe"], 0)

    def test_pending_upgrades_never_approved_by_snapshot(self):
        self.write_plan(source_ci_verified=False,
                        pull_requests=[{"pr": 999, "integrated": False}])
        report = ready.inspect(self.source)
        self.assertIn(999, report["pending_pr_numbers"])
        self.assertFalse(report["installation_ready"])

    def test_production_source_manifest_inventory_is_safe(self):
        report = ready.inspect(ROOT, scan_pc=False)
        self.assertEqual(report["status"], "REVIEW_ONLY", report["blockers"])
        self.assertEqual(report["counts"]["candidate_missing_or_unsafe"], 0)
        self.assertFalse(report["installation_ready"])


if __name__ == "__main__":
    unittest.main()
