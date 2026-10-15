"""Regression tests for read-only Spider OS Git-to-install reconciliation."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "audit_installed_sources", ROOT / "tools" / "audit_installed_sources.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class InstalledSourceAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.installed = self.root / "installed"
        self.repo.mkdir()
        self.installed.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)

    def source(self, name, data):
        target = self.repo / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(data)
        subprocess.run(["git", "add", "--", name], cwd=self.repo, check=True)
        return target

    def deployed(self, name, data):
        target = self.installed / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(data)
        return target

    def test_tracks_vendored_max_source_without_reading_private_files(self):
        self.source("spider_max_source/spider_monster/max_catalog.py", "safe")
        self.deployed("spider_max_source/spider_monster/max_catalog.py", "safe")
        result = module.audit(self.repo, self.installed)
        self.assertEqual(result["total_tracked"], 1)
        self.assertEqual(result["components"]["spider_max_source"]["matching"], 1)

    def test_identical_public_files_match(self):
        self.source("webbie/agent/webbie.py", "print('hi')")
        self.deployed("webbie/agent/webbie.py", "print('hi')")
        result = module.audit(self.repo, self.installed)
        self.assertEqual(result["matching"], 1)
        self.assertEqual(result["changed"], [])
        self.assertEqual(result["missing"], [])

    def test_changed_missing_and_private_files_not_collected(self):
        self.source("studio/bin/studio.py", "expected")
        self.deployed("studio/bin/studio.py", "local fix")
        self.source("author/main.py", "expected")
        self.deployed("studio/private-credential.txt", "not-for-report")
        self.source("README.md", "not a Spider component")
        result = module.audit(self.repo, self.installed)
        self.assertEqual(result["total_tracked"], 2)
        self.assertEqual(result["changed"], ["studio/bin/studio.py"])
        self.assertEqual(result["missing"], ["author/main.py"])
        self.assertNotIn("private-credential", str(result))


if __name__ == "__main__":
    unittest.main()
