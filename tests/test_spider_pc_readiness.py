"""No-install hardware and customized-file reconciliation regression tests."""
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module_from(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    instance = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(instance)
    return instance


hardware = module_from("tools/pc_hardware_compatibility.py", "spider_hardware_test")
bundle = module_from("tools/spider_pc_readiness.py", "spider_pc_bundle_test")
acceptance = module_from("tools/daily_pc_acceptance.py", "spider_pc_acceptance_expanded")


class HardwareInventoryTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.folder = Path(tmp.name)
        (self.folder / "os-release").write_text('ID=ubuntu\nVERSION_ID="24.04"\n')
        (self.folder / "meminfo").write_text(
            "MemTotal:       16384000 kB\nMemAvailable:  8192000 kB\n")

    def test_privacy_safe_audio_probes_never_expose_source_identifiers(self):
        private_device = "webcam-OWNER-SERIAL-123"
        calls = []
        def fake_run(argv, **kwargs):
            calls.append(argv)
            if argv[-1] == "sources":
                return SimpleNamespace(
                    stdout="12 " + private_device + " PipeWire s16le 2ch 48000Hz RUNNING\n"
                           "13 speaker.monitor PipeWire s32le 2ch 48000Hz SUSPENDED\n",
                    returncode=0)
            return SimpleNamespace(stdout=private_device + "\n", returncode=0)
        data = hardware.inspect_hardware(
            installed_root=self.folder, os_release=self.folder / "os-release",
            meminfo=self.folder / "meminfo", dri=self.folder / "dri",
            runner=fake_run,
            which=lambda s: "/usr/bin/" + s,
            disk_usage=lambda path: SimpleNamespace(free=20 * hardware.GIB),
            environ={"XDG_SESSION_TYPE": "x11", "KDE_FULL_SESSION": "true"})
        serialized = json.dumps(data)
        self.assertNotIn(private_device, serialized)
        self.assertEqual(data["microphone"]["default_microphone"], "selected")
        self.assertEqual(data["os"]["version"], "24.04")
        self.assertEqual(data["install_volume_free_gib"], 20)
        self.assertEqual(calls, [
            ["pactl", "list", "short", "sources"],
            ["pactl", "get-default-source"],
        ])

    def test_missing_audio_and_low_space_require_review_but_never_record(self):
        def refuse(*a, **kw):
            raise AssertionError("No programs should execute when pactl is absent")
        data = hardware.inspect_hardware(
            installed_root=self.folder, os_release=self.folder / "os-release",
            meminfo=self.folder / "meminfo", dri=self.folder / "dri",
            runner=refuse, which=lambda s: None,
            disk_usage=lambda path: SimpleNamespace(free=3 * hardware.GIB),
            environ={})
        self.assertEqual(data["microphone"]["default_microphone"], "unverified")
        self.assertGreaterEqual(len(data["review_flags"]), 3)
        self.assertIn("owner consent", " ".join(data["physical_verification_pending"]))


class PrivatePCReportTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.installed = Path(tmp.name) / "installed"
        self.installed.mkdir()
        (self.installed / "owner-stuff").write_text("DO NOT TOUCH")
        self.owned_file = self.installed / "owner-stuff"

    def _collect(self, **kwargs):
        def source(*args, **kwargs):
            return {
                "phase": "before", "status": "REVIEW REQUIRED",
                "blockers": [],
                "files": {
                    "Webbie": {"file": "webbie/agent/webbie.py",
                               "state": "different",
                               "installed_sha256": "ABC123OWNERHASH",
                               "candidate_sha256": "NEWCANDIDATEHASH",
                               "reason": None},
                    "Author": {"file": "author/main.py",
                               "state": "matching",
                               "installed_sha256": "123",
                               "candidate_sha256": "123",
                               "reason": None}},
                "services": {"webbie.service": "active"},
                "nova_health": "healthy",
            }
        result = bundle.collect(
            ROOT, self.installed, source_inspector=source,
            hardware_inspector=lambda **kw: {"review_flags": ["hardware manual test"]},
            receipt_inspector=lambda *a: "no_same_day_receipt_seen",
            sha_reader=lambda *a: "a" * 40,
            **kwargs,
        )
        return result

    def test_default_report_redacts_hashes_and_never_signs_off(self):
        before = self.owned_file.read_bytes()
        result = self._collect()
        self.assertFalse(result["safe_to_install"])
        self.assertEqual(result["status"], "REVIEW REQUIRED")
        self.assertEqual(result["files_summary"]["different"], 1)
        self.assertNotIn("ABC123OWNERHASH", json.dumps(result))
        self.assertNotIn("NEWCANDIDATEHASH", json.dumps(result))
        self.assertIn("Webbie", result["files"])
        self.assertEqual(before, self.owned_file.read_bytes())

    def test_local_explicit_hashes_and_expected_commit_mismatch(self):
        report = self._collect(include_hashes=True, expected_sha="b" * 40)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertFalse(report["expected_commit_matches"])
        self.assertIn("CHECKOUT SHA MISMATCH", " ".join(report["blockers"]))
        self.assertEqual(
            report["files"]["Webbie"]["installed_sha256"], "ABC123OWNERHASH")

    def test_new_wave_module_absence_is_pending_but_symlink_blocks(self):
        for label in ("Webbie model resilience", "Author canon intelligence",
                      "Studio PCM quality", "Study reading passages"):
            self.assertIn(label, acceptance.PLANNED_NEW)
            self.assertIn(label, acceptance.FILES)
        with tempfile.TemporaryDirectory() as folder:
            candidate = Path(folder) / "candidate"
            installed = Path(folder) / "installed"
            for root in (candidate, installed):
                for rel in acceptance.FILES.values():
                    file = root / rel
                    file.parent.mkdir(parents=True, exist_ok=True)
                    file.write_text("original\n")
            new = installed / acceptance.FILES["Studio PCM quality"]
            new.unlink()
            result = acceptance.inspect_files(candidate, installed)
            self.assertEqual(result["Studio PCM quality"]["state"], "pending_add")
            new.symlink_to(candidate / acceptance.FILES["Studio PCM quality"])
            result = acceptance.inspect_files(candidate, installed)
            self.assertEqual(result["Studio PCM quality"]["state"],
                             "installed_unavailable")


if __name__ == "__main__":
    unittest.main()
