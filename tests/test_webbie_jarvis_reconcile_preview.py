"""Private no-install JARVIS source reconciliation tests."""
from pathlib import Path
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from jarvis_reconcile_preview import (
    compare_release,render,_blob_hash,_git_blobs_at_paths,
    _stage_directory,
)


class DummyRelease:
    def __init__(self,items,states):
        self.items=items
        self.states=states

    def prepare_items(self,**kwargs):
        return self.items

    def inspect(self,items,**kwargs):
        return [(item,self.states[item.reference],
                 "private secret installed text") for item in items]

    def safe_path(self,path):
        return not Path(path).is_symlink()


class JarvisReconcileTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.home=self.root/"home"
        self.home.mkdir()
        self.source=self.home/"Checkout"
        self.install=self.home/"Installed"
        self.source.mkdir()
        self.install.mkdir()
        subprocess.run(["git","init","-q",str(self.source)],
                       check=True,stdout=subprocess.DEVNULL)
        self.relative="webbie/agent/webbie.py"
        (self.source/"webbie/agent").mkdir(parents=True)
        (self.install/"webbie/agent").mkdir(parents=True)
        self.src=self.source/self.relative
        self.dest=self.install/self.relative
        self.src.write_text("WEBBIE = 'baseline'\n")
        subprocess.run(
            ["git","-C",str(self.source),"add",self.relative],check=True)
        subprocess.run(["git","-C",str(self.source),
                        "-c","user.email=ci@example.invalid",
                        "-c","user.name=CI","commit","-qm","baseline"],
                       check=True)
        self.dest.write_text("WEBBIE = 'baseline'\n")
        self.src.write_text("WEBBIE = 'proposed'\n")
        subprocess.run(
            ["git","-C",str(self.source),"add",self.relative],check=True)
        subprocess.run(["git","-C",str(self.source),
                        "-c","user.email=ci@example.invalid",
                        "-c","user.name=CI","commit","-qm","proposed"],
                       check=True)
        self.item=type("Item",(),{
            "source":self.src,"target":self.dest,
            "reference":self.relative,
        })()
        self.release=DummyRelease([self.item],{self.relative:"BLOCKED"})

    def evaluate(self,**kw):
        return compare_release(
            self.source,self.install,home=self.home,
            release=self.release,**kw)

    def test_exact_historical_git_blob_provenance(self):
        report=self.evaluate()
        self.assertEqual(report["blocked_files"],1)
        self.assertEqual(report["items"][0]["classification"],
                         "recognized_git_blob_manual_review")
        self.assertTrue(report["items"][0]["exact_git_history_match"])
        self.assertFalse(report["installation_authorized"])
        self.assertEqual(self.dest.read_text(),"WEBBIE = 'baseline'\n")
        self.assertFalse((self.home/"diffs").exists())

    def test_custom_working_code_stays_preserved_and_diff_private(self):
        original="WEBBIE = 'owner custom with sensitive sample'\n"
        self.dest.write_text(original)
        out=self.home/"PrivateReview"
        report=self.evaluate(output=out)
        self.assertEqual(report["items"][0]["classification"],
                         "custom_code_manual_merge")
        self.assertFalse(report["items"][0]["exact_git_history_match"])
        private_diff=out/"diffs"/(self.relative+".diff")
        self.assertTrue(private_diff.is_file())
        self.assertIn("owner custom",private_diff.read_text())
        self.assertEqual(stat.S_IMODE(out.stat().st_mode),0o700)
        self.assertEqual(stat.S_IMODE(private_diff.stat().st_mode),0o600)
        self.assertEqual(stat.S_IMODE((out/"summary.json").stat().st_mode),
                         0o600)
        self.assertEqual(self.dest.read_text(),original)
        self.assertNotIn("owner custom",render(report))
        self.assertNotIn("owner custom",json.dumps(report))
        self.assertFalse(report["installed_files_modified"])

    def test_not_a_git_blob_file_excluded_from_diff(self):
        self.dest.unlink()
        other=self.home/"credentials.py"
        other.write_text("secret\n")
        self.dest.symlink_to(other)
        report=self.evaluate()
        self.assertEqual(report["items"][0]["classification"],
                         "unsafe_path_manual_review")
        self.assertEqual(other.read_text(),"secret\n")

    def test_missing_or_too_large_installed_files_stay_review_only(self):
        self.dest.write_bytes(b"x"*(1_000_001))
        report=self.evaluate()
        self.assertEqual(report["items"][0]["classification"],
                         "unreadable_or_large_manual_review")

    def test_current_source_and_install_never_mixed(self):
        with self.assertRaises(RuntimeError):
            compare_release(self.source,self.source,release=self.release)

    def test_never_overwrite_existing_review_folder(self):
        existing=self.home/"Previous"
        existing.mkdir()
        with self.assertRaisesRegex(RuntimeError,"new absolute"):
            self.evaluate(output=existing)
        self.assertEqual(list(existing.iterdir()),[])

    def test_review_directory_cannot_be_inside_installed_tree(self):
        with self.assertRaisesRegex(RuntimeError,"cannot reside inside"):
            self.evaluate(output=self.install/"Subfolder")

    def test_paths_outside_owner_home_are_not_review_destinations(self):
        with self.assertRaisesRegex(RuntimeError,"owner-home"):
            self.evaluate(output=self.root/"NotUnderHome")

    def test_unrecognized_status_is_refused(self):
        self.release.states[self.relative]="SKIP_SECURITY"
        with self.assertRaisesRegex(RuntimeError,"Unknown source"):
            self.evaluate()

    def test_git_history_identification_handles_empty_or_non_git(self):
        no_repo=self.home/"not_git"
        no_repo.mkdir()
        self.assertEqual(_git_blobs_at_paths(no_repo,{self.relative}),{})
        self.assertEqual(_git_blobs_at_paths(self.source,set()),{})

    def test_only_blocked_items_returned_in_review(self):
        self.release.states[self.relative]="CURRENT"
        report=self.evaluate()
        self.assertEqual(report["blocked_files"],0)
        self.assertEqual(report["items"],[])

if __name__=="__main__":
    unittest.main()
