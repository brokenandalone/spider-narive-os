"""The Spider OS PC acceptance tool runs only against temporary code trees."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "spider_daily_pc_acceptance_test", ROOT / "tools/daily_pc_acceptance.py"
)
acceptance = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(acceptance)


class DailyPCAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.source = root / "candidate"
        self.installed = root / "installed"
        for area in (self.source, self.installed):
            for path in acceptance.FILES.values():
                dest = area / path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text("source = 'original'\n")

    def test_preinstall_review_detects_changes_without_touching_installed(self):
        source = self.source / acceptance.FILES["Webbie"]
        source.write_text("source = 'upgraded'\n")
        before = (self.installed / acceptance.FILES["Webbie"]).read_bytes()
        result = acceptance.inspect(self.source, self.installed,
                                    phase="before", check_services=False)
        self.assertEqual(result["status"], "REVIEW REQUIRED")
        self.assertEqual(result["files"]["Webbie"]["state"], "different")
        self.assertEqual(result["blockers"], [])
        self.assertEqual(before, (self.installed / acceptance.FILES["Webbie"]).read_bytes())

    def test_kali_evidence_and_report_sources_are_required(self):
        source = self.source / acceptance.FILES["Kali evidence chain"]
        installed = self.installed / acceptance.FILES["Kali evidence chain"]
        source.write_text("new evidence ledger source\\n")
        check = acceptance.inspect(
            self.source, self.installed, phase="after", check_services=False
        )
        self.assertEqual(check["status"], "BLOCKED")
        self.assertEqual(check["files"]["Kali evidence chain"]["state"], "different")
        self.assertTrue(any("Kali evidence chain" in item
                            for item in check["blockers"]))
        installed.write_bytes(source.read_bytes())
        check = acceptance.inspect(
            self.source, self.installed, phase="after", check_services=False
        )
        self.assertEqual(check["files"]["Kali evidence chain"]["state"], "matching")

        report = self.installed / acceptance.FILES["Kali report engine"]
        report.unlink()
        check = acceptance.inspect(
            self.source, self.installed, phase="before", check_services=False
        )
        self.assertEqual(check["status"], "BLOCKED")
        self.assertEqual(check["files"]["Kali report engine"]["state"],
                         "installed_unavailable")
        self.assertFalse(report.exists())

    def test_postinstall_rejects_unreconciled_code(self):
        (self.source / acceptance.FILES["Forage"]).write_text("new version")
        result = acceptance.inspect(self.source, self.installed,
                                    phase="after", check_services=False)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("Forage" in reason for reason in result["blockers"]))
        self.assertEqual(result["files"]["Studio"]["state"], "matching")

    def test_missing_and_symlinked_installed_source_blocks_in_both_phases(self):
        bad = self.installed / acceptance.FILES["Author"]
        bad.unlink()
        bad.symlink_to(self.source / acceptance.FILES["Author"])
        for phase in ("before", "after"):
            result = acceptance.inspect(self.source, self.installed,
                                        phase=phase, check_services=False)
            self.assertEqual(result["status"], "BLOCKED")
            self.assertEqual(result["files"]["Author"]["state"], "installed_unavailable")
            self.assertIn("symlink", result["files"]["Author"]["reason"])

    def test_parent_directory_symlink_is_not_traversed(self):
        nested = self.installed / "study"
        source = self.source / "study"
        for p in nested.iterdir():
            p.unlink()
        nested.rmdir()
        nested.symlink_to(source, target_is_directory=True)
        result = acceptance.inspect(self.source, self.installed,
                                    phase="before", check_services=False)
        self.assertEqual(result["files"]["Study"]["state"], "installed_unavailable")

    def test_healthy_services_and_nova_are_checked_only_after_install(self):
        def run(args, **kwargs):
            return Mock(stdout="active\n", returncode=0)
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def read(self, length): return b'{"ok":true,"service":"Spider AI DJ"}'
        with patch.object(acceptance, "inspect_services",
                          return_value={unit: "active" for unit in acceptance.SERVICES}), \
             patch.object(acceptance, "inspect_nova_health", return_value="healthy"):
            result = acceptance.inspect(self.source, self.installed, phase="after")
        self.assertEqual(result["status"], "SOURCE MATCHING")
        self.assertEqual(result["blockers"], [])
        self.assertEqual(acceptance.inspect_services(runner=run)["webbie.service"], "active")
        self.assertEqual(acceptance.inspect_nova_health(opener=lambda *a, **kw: Response()),
                         "healthy")

    def test_failed_or_unverifiable_service_does_not_claim_success(self):
        with patch.object(acceptance, "inspect_services", return_value={
            "webbie.service": "inactive", "spider-ai-dj.service": "unverified",
        }), patch.object(acceptance, "inspect_nova_health", return_value="unverified"):
            result = acceptance.inspect(self.source, self.installed, phase="after")
        self.assertEqual(result["status"], "BLOCKED")
        self.assertGreaterEqual(len(result["blockers"]), 3)

    def test_absent_service_lookup_fails_closed_and_never_starts_service(self):
        mock = Mock(side_effect=FileNotFoundError)
        status = acceptance.inspect_services(runner=mock)
        self.assertEqual(status["webbie.service"], "unverified")
        self.assertTrue(all(args.args[0][1:3] == ["--user", "is-active"]
                            for args in mock.call_args_list))
        self.assertNotIn("start", str(mock.call_args_list))


if __name__ == "__main__":
    unittest.main()
