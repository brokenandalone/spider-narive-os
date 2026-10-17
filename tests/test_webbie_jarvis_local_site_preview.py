"""Webbie JARVIS can host only public static assets on localhost."""
from pathlib import Path
from urllib.request import urlopen,Request
from urllib.error import HTTPError
import os
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"webbie/actions"))
from jarvis_local_site_preview import LocalSitePreview
from jarvis_orchestrator import JarvisCore
from owner_authorization_store import update_policy

class JarvisStaticLocalHostTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home=Path(self.temp.name)/"home"
        self.website=self.home/"Websites"/"BCN"
        (self.website/"assets").mkdir(parents=True)
        (self.website/"index.html").write_text("<h1>BCN TEST</h1>")
        (self.website/"assets"/"site.css").write_text("body{color:white}")
        (self.website/".env").write_text("API_TOKEN=never_expose")
        (self.website/"private").mkdir()
        (self.website/"private"/"notes.html").write_text("secret content")
        os.symlink(self.website/"index.html",self.website/"other.html")
        self.preview=LocalSitePreview()
        self.addCleanup(self.preview.stop)

    def test_actual_loopback_static_html_and_blocked_private_assets(self):
        data=self.preview.start(self.website,home=self.home)
        self.assertEqual(data["loopback_only"],True)
        self.assertTrue(data["url"].startswith("http://127.0.0.1:"))
        with urlopen(data["url"],timeout=3) as page:
            self.assertIn(b"BCN TEST",page.read())
            self.assertEqual(page.headers["X-Content-Type-Options"],"nosniff")
        with urlopen(data["url"]+"assets/site.css",timeout=3) as css:
            self.assertIn(b"color:white",css.read())
        for path in (".env","private/notes.html","other.html",
                     "missing.html","../other.html"):
            with self.subTest(path=path),self.assertRaises(HTTPError):
                urlopen(data["url"]+path,timeout=3)

    def test_uploads_and_delete_calls_are_not_served(self):
        data=self.preview.start(self.website,home=self.home)
        for method in ("POST","PUT","DELETE"):
            req=Request(data["url"],data=b"not allowed",method=method)
            with self.subTest(method=method),self.assertRaises(HTTPError):
                urlopen(req,timeout=3)

    def test_close_releases_static_site_server(self):
        self.preview.start(self.website,home=self.home)
        self.assertTrue(self.preview.status()["running"])
        self.preview.stop()
        self.assertFalse(self.preview.status()["running"])
        self.preview.stop()

    def test_permissions_gate_real_server_and_stop_shuts_it_down(self):
        policy=Path(self.temp.name)/"private_auth"/"policy.json"
        core=JarvisCore(policy_path=policy,preview=self.preview)
        refused=core.run("site.preview",source="owner_gui",
                         folder=self.website,home=self.home)
        self.assertEqual(refused.status,"denied")
        self.assertFalse(self.preview.status()["running"])
        update_policy("authorize",owner_clicked=True,path=policy)
        granted=core.run("site.preview",source="owner_gui",
                         folder=self.website,home=self.home)
        self.assertEqual(granted.status,"observed")
        self.assertTrue(self.preview.status()["running"])
        core.stop()
        self.assertFalse(self.preview.status()["running"])
        update_policy("pause",path=policy)
        self.assertEqual(core.run("site.preview",source="owner_gui",
                                   folder=self.website,
                                   home=self.home).status,"denied")

if __name__=="__main__":
    unittest.main()
