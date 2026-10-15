"""File evidence search never escapes an explicitly selected project folder."""
from pathlib import Path
import tempfile
import os
import unittest
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"webbie/actions"))
from jarvis_local_evidence import (
    approved_root,search_local_evidence,render_evidence,
)

class JarvisLocalEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home=Path(self.temp.name)/"home"
        self.project=self.home/"Documents"/"Spider Projects"/"BCN"
        self.project.mkdir(parents=True)
        (self.project/"index.html").write_text(
            "<h1>Broken City Radio</h1>\nBroken Sorrow live website\n")
        (self.project/"readme.md").write_text(
            "Broken City continuity and research\n")
        self.private=self.project/".secrets"
        self.private.mkdir()
        (self.private/"secret.md").write_text("Broken City API KEY secret")
        (self.project/"passwords.txt").write_text("Broken City PASSWORD")
        os.symlink(self.home/"Documents",self.project/"external")

    def test_bounded_search_only_owner_selected_text(self):
        answer=search_local_evidence(
            self.project,"Broken City",home=self.home)
        self.assertEqual(answer["root"],"BCN")
        self.assertEqual(
            {x["path"] for x in answer["matches"]},
            {"index.html","readme.md"})
        self.assertEqual(answer["read_only"],True)
        self.assertNotIn("PASSWORD",render_evidence(answer))
        self.assertNotIn("secret",render_evidence(answer).lower())

    def test_selected_root_must_remain_under_owner_home(self):
        for root in (self.home,self.home.parent,Path("/etc"),
                     self.private,self.project/"external"):
            with self.subTest(root=root),self.assertRaises(
                    (PermissionError,ValueError)):
                approved_root(root,home=self.home)

    def test_skip_symlinked_files_hidden_and_binary(self):
        other=self.home/"Documents"/"external.txt"
        other.write_text("Broken City classified")
        os.symlink(other,self.project/"link.txt")
        (self.project/".env").write_text("Broken City SECRET")
        (self.project/"media.mp4").write_bytes(b"Broken City audio")
        response=search_local_evidence(
            self.project,"Broken City",home=self.home)
        paths=[x["path"] for x in response["matches"]]
        self.assertNotIn("link.txt",paths)
        self.assertNotIn(".env",paths)
        self.assertNotIn("media.mp4",paths)

    def test_reject_unbounded_queries_and_guard_limits(self):
        for term in ("", "a", "x"*91, "term\nsudo"):
            with self.assertRaises(ValueError):
                search_local_evidence(self.project,term,home=self.home)
        with self.assertRaises(ValueError):
            search_local_evidence(
                self.project,"Broken City",home=self.home,max_results=1000)

    def test_private_assignment_line_is_redacted(self):
        (self.project/"notes.txt").write_text(
            "Broken City\napi_key = Broken City dangerous secret")
        data=search_local_evidence(
            self.project,"dangerous",home=self.home)
        self.assertEqual(data["matches"][0]["snippet"],
                         "[sensitive assignment redacted]")

if __name__=="__main__":
    unittest.main()
