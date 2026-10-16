"""Private native Spider OS merge staging: no installed writes, no leaks."""
import importlib.util
from pathlib import Path
import os
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "spider_private_merge_stage", ROOT / "tools/stage_native_merge.py")
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class PrivateStageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.source = self.home / "review-source"
        self.installed = self.home / "review-installed"
        self.source.mkdir()
        self.installed.mkdir()
        (self.source / "system").mkdir()
        (self.source / "system/release_batch.py").write_text(
            "APP_FILES = " + repr(mod.FOCI["desktop"]) + "\n",
            encoding="utf-8")
        self.originals = {}
        for relative in mod.FOCI["desktop"]:
            live = self.installed / relative
            candidate = self.source / relative
            live.parent.mkdir(parents=True, exist_ok=True)
            candidate.parent.mkdir(parents=True, exist_ok=True)
            live.write_text(
                "def local_owner_method():\n    return 'PRIVATE LOCAL DATA'\n", encoding="utf-8")
            candidate.write_text(
                "def candidate_feature():\n    return 1\n", encoding="utf-8")
            self.originals[relative] = live.read_bytes()

    def test_stages_private_five_file_pairs_without_touching_owner(self):
        output = self.home / "SpiderOS-Desktop-Merge-Private"
        report = mod.stage(
            self.source, self.installed, output,
            focus="desktop", home=self.home, scope=mod.FOCI["desktop"])
        self.assertEqual(len(report["files"]), 5)
        self.assertFalse(report["installed_files_modified"])
        self.assertFalse(report["release_installable"])
        self.assertTrue(report["contains_private_owner_source"])
        self.assertEqual(output.stat().st_mode & 0o777, 0o700)
        for relative in mod.FOCI["desktop"]:
            local = output / "installed" / relative
            candidate = output / "candidate" / relative
            diff = output / "diffs" / (relative + ".diff")
            self.assertTrue(local.is_file())
            self.assertTrue(candidate.is_file())
            self.assertTrue(diff.is_file())
            for item in (local, candidate, diff):
                self.assertEqual(item.stat().st_mode & 0o777, 0o600)
            self.assertEqual(local.read_bytes(), self.originals[relative])
            self.assertEqual((self.installed / relative).read_bytes(),
                             self.originals[relative])
        # The report contains symbol names only, not code bodies.
        manifest = (output / "manifest.json").read_text()
        self.assertNotIn("PRIVATE LOCAL DATA", manifest)
        self.assertIn("local_owner_method", manifest)

    def test_missing_installed_native_module_is_staged_as_addition(self):
        relative = mod.FOCI["desktop"][0]
        (self.installed / relative).unlink()
        output = self.home / "stage-new-module"
        report = mod.stage(
            self.source, self.installed, output,
            focus="desktop", home=self.home, scope=mod.FOCI["desktop"])
        row = next(item for item in report["files"] if item["component"] == relative)
        self.assertEqual(row["state"], "new_candidate_only")
        self.assertIsNone(row["installed_sha256"])
        self.assertTrue(row["requires_owner_review"])
        self.assertFalse((output / "installed" / relative).exists())
        self.assertTrue((output / "candidate" / relative).is_file())
        self.assertFalse(report["release_installable"])

    def test_unsafe_existing_directory_still_blocks_staging(self):
        relative = mod.FOCI["desktop"][0]
        (self.installed / relative).unlink()
        (self.installed / relative).mkdir()
        with self.assertRaises(ValueError):
            mod.stage(self.source, self.installed, self.home / "stage-unsafe",
                      focus="desktop", home=self.home, scope=mod.FOCI["desktop"])

    def test_cannot_overwrite_existing_stage_or_stage_in_candidate(self):
        output = self.home / "private-review"
        output.mkdir()
        with self.assertRaises(ValueError):
            mod.stage(self.source, self.installed, output, focus="desktop",
                      home=self.home, scope=mod.FOCI["desktop"])
        with self.assertRaises(ValueError):
            mod.stage(self.source, self.installed, self.source / "not-allowed",
                      focus="desktop", home=self.home, scope=mod.FOCI["desktop"])

    def test_refuses_symlinked_installed_code(self):
        target = self.installed / mod.FOCI["desktop"][0]
        target.unlink()
        private = self.home / "secret.txt"
        private.write_text("SENSITIVE LOCAL USER FILE")
        target.symlink_to(private)
        output = self.home / "spider-review-symlink"
        with self.assertRaises(ValueError):
            mod.stage(self.source, self.installed, output, focus="desktop",
                      home=self.home, scope=mod.FOCI["desktop"])
        self.assertFalse(output.exists())
        self.assertEqual(private.read_text(), "SENSITIVE LOCAL USER FILE")

    def test_missing_release_file_cannot_silently_disappear(self):
        with self.assertRaises(ValueError):
            mod.stage(self.source, self.installed, self.home / "stage",
                      focus="desktop", home=self.home,
                      scope=("the-web/shell/main.py",))

    def test_native_bays_only_stages_existing_native_components(self):
        expected = {
            "the-web/shell/home_dashboard.py",
            "the-web/shell/bay_missions.py",
            "the-web/shell/bay_mission_panel.py",
            "the-web/shell/native_utility_bays.py",
            "the-web/shell/art_workbench.py",
            "the-web/shell/webbie_research_panel.py",
            "the-web/shell/immersive_bays.py",
        }
        self.assertEqual(set(mod.FOCI["native-bays"]), expected)
        self.assertFalse(any(path.startswith("studio/") for path in expected))
        release = (ROOT / "system/release_batch.py").read_text()
        for path in expected:
            self.assertIn(repr(path), release)
        self.assertFalse(any("webbie_panel.py" in path for path in expected))

    def test_noninstalling_staging_does_not_execute_or_upload_code(self):
        content = (ROOT / "tools/stage_native_merge.py").read_text()
        for forbidden in ("os.system(", "subprocess.Popen(", "urllib",
                          "requests.", "shutil.copytree(", "sudo ",
                          "do-release-upgrade", "pip install"):
            self.assertNotIn(forbidden, content)
        self.assertIn("GUARDED INSTALL REMAINS BLOCKED", content)


if __name__ == "__main__":
    unittest.main()
