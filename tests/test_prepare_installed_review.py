"""Review-only archive test: synthetic Git source, no owner PC or network."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location("source_review", TOOLS / "prepare_installed_review.py")
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class SourceReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.repo = base / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", review.BRANCH, str(self.repo)], check=True)
        for k, v in [("user.name", "Synthetic Reviewer"), ("user.email", "test@example.invalid")]:
            subprocess.run(["git", "-C", str(self.repo), "config", k, v], check=True)
        self.changed = [f"webbie/agent/changed_{i:02d}.py" for i in range(39)]
        self.extra = sorted(review.ALLOWED_UNTRACKED_SOURCE)
        for rel in self.changed:
            p = self.repo / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("old_source = True\n")
        subprocess.run(["git", "-C", str(self.repo), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.repo), "commit", "-qm", "test source"], check=True)
        installed_sha = {}
        for rel in self.changed:
            (self.repo / rel).write_text("new_source = True\n")
        for rel in self.extra:
            p = self.repo / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("new_module = True\n")
            installed_sha[rel] = {"sha256": review.sha(p.read_bytes())}
        self.manifest = base / "manifest.json"
        self.manifest.write_text(json.dumps({
            "repo_commit": "mock-revision",
            "groups": {"different": self.changed, "installed_only": self.extra},
            "installed_sha256": installed_sha,
        }))
        self.output = base / "private.zip"

    def test_archive_contains_only_intended_code(self):
        result = review.make_archive(self.repo, self.manifest, self.output)
        self.assertEqual((result["changed"], result["extra"]), (39, 8))
        with zipfile.ZipFile(self.output) as z:
            names = z.namelist()
            self.assertEqual(len(names), 10)
            self.assertIn("installed-source.patch", names)
            self.assertIn("new-source/webbie/agent/webbie_ai_worker.py", names)
            self.assertIn(b"new_source = True",
                          [z.read("installed-source.patch")][0])
        self.assertTrue((self.repo / self.changed[0]).exists())
        self.assertFalse((self.repo / "private.zip").exists())

    def test_refuses_untracked_extra_file(self):
        (self.repo / "PRIVATE_CREDS.txt").write_text("something")
        with self.assertRaisesRegex(ValueError, "Untracked paths differ"):
            review.make_archive(self.repo, self.manifest, self.output)
        self.assertFalse(self.output.exists())

    def test_refuses_credential_in_new_source(self):
        p = self.repo / self.extra[0]
        p.write_text("token='ghp_" + "A" * 25 + "'\n")
        metadata = json.loads(self.manifest.read_text())
        metadata["installed_sha256"][self.extra[0]] = {"sha256": review.sha(p.read_bytes())}
        self.manifest.write_text(json.dumps(metadata))
        with self.assertRaisesRegex(ValueError, "Potential credential"):
            review.make_archive(self.repo, self.manifest, self.output)
        self.assertFalse(self.output.exists())

    def test_refuses_wrong_hash_or_duplicate_target(self):
        p = self.repo / self.extra[0]
        p.write_text("new_module = False\n")
        with self.assertRaisesRegex(ValueError, "changed since audit"):
            review.make_archive(self.repo, self.manifest, self.output)
        p.write_text("new_module = True\n")
        self.output.write_text("do not overwrite")
        with self.assertRaisesRegex(ValueError, "already exists"):
            review.make_archive(self.repo, self.manifest, self.output)


if __name__ == "__main__":
    unittest.main()
