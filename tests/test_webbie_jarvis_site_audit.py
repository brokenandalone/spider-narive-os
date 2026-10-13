"""JARVIS website audit inspects local evidence only, never deploys."""
from pathlib import Path
import tempfile
import os
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"webbie/actions"))
from jarvis_site_audit import inspect_site_project,render_site_report

class JarvisSiteAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home=Path(self.temp.name)/"home"
        self.site=self.home/"Websites"/"BCN Network"
        (self.site/"assets").mkdir(parents=True)
        (self.site/"pages").mkdir()
        (self.site/"index.html").write_text(
            '<img src="assets/logo.png">'
            '<script src="/assets/main.js"></script>'
            '<link rel="stylesheet" href="assets/missing.css">'
            '<a href="https://example.org/">External</a>'
            '<img src="assets/absent.jpg">')
        (self.site/"pages"/"band.html").write_text(
            '<img src="../assets/logo.png">'
            '<img src="https://example.org/photo.png">')
        (self.site/"assets"/"logo.png").write_bytes(b"valid")
        (self.site/"assets"/"main.js").write_text("console.log('hello')")

    def test_missing_assets_located_without_changes(self):
        before=(self.site/"index.html").read_text()
        result=inspect_site_project(self.site,home=self.home)
        self.assertEqual(result["html_pages"],2)
        self.assertEqual(result["missing_local_assets"],[
            {"page":"index.html","reference":"assets/missing.css"},
            {"page":"index.html","reference":"assets/absent.jpg"},
        ])
        self.assertTrue(result["has_root_index"])
        self.assertEqual(result["deployment"],"not attempted")
        self.assertEqual(before,(self.site/"index.html").read_text())
        self.assertIn("missing.css",render_site_report(result))

    def test_no_symlink_or_parent_escape(self):
        outside=self.home/"elsewhere"
        outside.mkdir()
        (outside/"bad.html").write_text('<img src="stolen.png">')
        os.symlink(outside,self.site/"external_dir")
        (self.site/"pages"/"escape.html").write_text(
            '<img src="../../../outside.css">')
        data=inspect_site_project(self.site,home=self.home)
        self.assertEqual(data["html_pages"],3)
        self.assertEqual(data["deployment"],"not attempted")
        self.assertNotIn("external_dir",str(data))

    def test_project_must_be_under_owner_home_and_explicit(self):
        with self.assertRaises(PermissionError):
            inspect_site_project(self.home,home=self.home)
        with self.assertRaises(PermissionError):
            inspect_site_project(self.site.parent.parent,home=self.home)

if __name__=="__main__":
    unittest.main()
