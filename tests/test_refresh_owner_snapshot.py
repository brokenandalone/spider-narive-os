"""Refreshing a changed owner's native source must be private and lossless."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
spec=importlib.util.spec_from_file_location(
    "owner_snapshot_refresh",ROOT/"tools/refresh_owner_snapshot.py")
refresh=importlib.util.module_from_spec(spec)
spec.loader.exec_module(refresh)


class OwnerSnapshotRefreshTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        home=Path(tmp.name)
        self.live=home/"installed"
        self.prior=home/"earlier.zip"
        self.new=home/"fresh-review"
        self.contents={}
        for name in refresh.OWNER_FILES:
            path=self.live/name
            path.parent.mkdir(parents=True,exist_ok=True)
            raw=(b"def old_function():\n    return 1\n"
                 if name.endswith(".py") else b"#!/bin/bash\ntrue\n")
            path.write_bytes(raw)
            self.contents[name]=raw
        with zipfile.ZipFile(self.prior,"w",zipfile.ZIP_DEFLATED) as z:
            for name,data in self.contents.items():
                z.writestr("installed/"+name,data)
        self.prior_bytes=self.prior.read_bytes()

    def test_changed_live_nova_creates_fresh_private_owner_zip(self):
        path=self.live/"media/ai-dj/service.py"
        changed=b"def new_dj_voice():\n    return 'existing-newer-code'\n"
        path.write_bytes(changed)
        summary=refresh.make_snapshot(self.prior,self.live,self.new)
        self.assertEqual(summary["status"],"FRESH_OWNER_SNAPSHOT_REVIEW_ONLY")
        self.assertEqual(summary["changed_file_count"],1)
        self.assertEqual(summary["changed_files"][0]["path"],"media/ai-dj/service.py")
        self.assertTrue(summary["previous_archive_preserved"])
        self.assertEqual(self.prior.read_bytes(),self.prior_bytes)
        new_zip=self.new/"Spider_OS_Current_31_Source.zip"
        current=refresh.load_owner_zip(new_zip)
        self.assertEqual(len(current),31)
        self.assertEqual(current["media/ai-dj/service.py"],changed)
        for name in refresh.OWNER_FILES:
            self.assertEqual(current[name],(self.live/name).read_bytes())
        report=json.loads((self.new/"owner-source-drift.json").read_text())
        self.assertEqual(report["changed_file_count"],1)
        self.assertNotIn("existing-newer-code",(self.new/"owner-source-drift.json").read_text())

    def test_preexisting_directory_is_not_overwritten(self):
        self.new.mkdir()
        (self.new/"keep.txt").write_text("my original")
        with self.assertRaisesRegex(ValueError,"New review"):
            refresh.make_snapshot(self.prior,self.live,self.new)
        self.assertEqual((self.new/"keep.txt").read_text(),"my original")

    def test_invalid_live_file_blocks_before_creating_review(self):
        (self.live/"media/ai-dj/service.py").write_text("def broken(:")
        with self.assertRaises(SyntaxError):
            refresh.make_snapshot(self.prior,self.live,self.new)
        self.assertFalse(self.new.exists())

    def test_missing_installed_file_blocks_without_changing_prior(self):
        (self.live/"media/ai-dj/service.py").unlink()
        with self.assertRaises(ValueError):
            refresh.make_snapshot(self.prior,self.live,self.new)
        self.assertFalse(self.new.exists())
        self.assertEqual(self.prior.read_bytes(),self.prior_bytes)

    def test_unchanged_source_is_not_promoted_to_installed_release(self):
        summary=refresh.make_snapshot(self.prior,self.live,self.new)
        self.assertEqual(summary["changed_file_count"],0)
        self.assertFalse(summary["installed_files_modified"])
        self.assertEqual(summary["status"],"FRESH_OWNER_SNAPSHOT_REVIEW_ONLY")


if __name__=="__main__":
    unittest.main()
