"""Kali Bay owner-PC continuity audit must be dry-run and preserve changes."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "kali-bay/package/audit-upgrade.py"
SPEC = importlib.util.spec_from_file_location("kali_preflight", SCRIPT)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class UpgradeAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.source = root / "source"
        self.installed = root / "installed"
        for name in mod.FILES:
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("new source: " + name + "\n")

    def make_installed(self, files):
        for name in files:
            path = self.installed / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((self.source / name).read_bytes())

    def test_missing_new_modules_are_additive_not_silent_installs(self):
        self.make_installed(mod.KALI_CORE)
        before = sorted(self.installed.rglob("*"))
        report = mod.audit(self.source, self.installed)
        self.assertTrue(report["safe_for_automatic_replacement"])
        core = [x for x in report["files"] if x["group"] == "core"]
        self.assertTrue(all(x["status"] == "identical" for x in core))
        new = [x for x in report["files"] if x["group"] == "module"]
        self.assertTrue(all(x["status"] == "new_module" for x in new))
        self.assertEqual(before, sorted(self.installed.rglob("*")))

    def test_customized_owner_ui_blocks_release(self):
        self.make_installed(mod.KALI_CORE)
        altered = self.installed / "kali-bay/ui/kali_bay.py"
        altered.write_text("OWNER PERSONALIZATION\n")
        report = mod.audit(self.source, self.installed)
        self.assertFalse(report["safe_for_automatic_replacement"])
        self.assertIn("blocked_customized", [
            x["status"] for x in report["files"]
        ])
        self.assertEqual(altered.read_text(), "OWNER PERSONALIZATION\n")

    def test_symlinked_installed_file_blocks_without_following(self):
        self.make_installed(mod.KALI_CORE)
        external = self.installed.parent / "external"
        external.write_text("outside")
        app = self.installed / "kali-bay/ui/kali_bay.py"
        app.unlink()
        app.symlink_to(external)
        report = mod.audit(self.source, self.installed)
        self.assertFalse(report["safe_for_automatic_replacement"])
        self.assertIn("blocked_symlink", [
            x["status"] for x in report["files"]
        ])
        self.assertEqual(external.read_text(), "outside")

    def test_missing_existing_manager_blocks(self):
        self.make_installed(["kali-bay/ui/kali_bay.py"])
        report = mod.audit(self.source, self.installed)
        self.assertFalse(report["safe_for_automatic_replacement"])
        self.assertIn("blocked_missing_core", [
            x["status"] for x in report["files"]
        ])

    def test_cli_json_requires_no_sudo_and_is_readonly(self):
        self.make_installed(mod.KALI_CORE)
        call = subprocess.run(
            [sys.executable, str(SCRIPT),
             "--source-root", str(self.source),
             "--installed-root", str(self.installed),
             "--json"],
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(call.returncode, 0, call.stderr)
        result = json.loads(call.stdout)
        self.assertTrue(result["safe_for_automatic_replacement"])
        self.assertEqual(len(result["files"]), len(mod.FILES))
        self.assertFalse((self.installed / "kali-bay/runtime").exists())

    def test_no_side_effects_or_system_calls(self):
        source = SCRIPT.read_text()
        for marker in (
            "subprocess", "os.system", "os.makedirs", "mkdir(",
            "podman exec", "distrobox enter", "systemctl start",
        ):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
