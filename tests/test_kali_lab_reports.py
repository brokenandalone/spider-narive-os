"""Offline Kali guides, private report export and five-tab UI regressions."""
import importlib.util
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "kali-bay/runtime"
sys.path.insert(0, str(RUNTIME))
import workspace_store as store
import lab_reports as reports


class OfflineLabReportsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        home_patch = patch.object(Path, "home", return_value=self.home)
        base_patch = patch.object(
            store, "BASE",
            self.home / ".local/share/spider-os/kali-bay/projects",
        )
        home_patch.start()
        base_patch.start()
        self.addCleanup(home_patch.stop)
        self.addCleanup(base_patch.stop)

    def test_guides_are_offline_static_and_do_not_create_files(self):
        guides = reports.list_guides()
        self.assertGreaterEqual(len(guides), 8)
        self.assertEqual(len({g["id"] for g in guides}), len(guides))
        self.assertTrue(reports.list_guides("packet"))
        self.assertEqual(reports.list_guides("not-a-real-workflow"), [])
        for guide in guides:
            document = reports.guide_template(guide["id"])
            self.assertIn("AUTHORIZATION AND SCOPE", document)
            self.assertIn("CHECKLIST", document)
            self.assertGreater(len(document), 100)
        with self.assertRaises(store.StorageError):
            reports.guide_template("../../../etc/passwd")
        self.assertFalse(store.BASE.exists())

    def test_explicit_private_no_overwrite_report_files(self):
        lab = store.create_lab("Authorized training lab")
        saved = store.save_lab(
            lab["id"], "Existing logs only. No live probes.",
            expected_revision=lab["revision"],
        )
        path = reports.export_saved_report(saved["id"])
        self.assertEqual(path.suffix, ".md")
        self.assertEqual(path.parent, store.BASE / "reports")
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode), 0o700)
        document = path.read_text(encoding="utf-8")
        self.assertIn("Authorized training lab", document)
        self.assertIn("No live probes", document)
        self.assertIn("not independently verified", document)
        self.assertIn(f"Saved revision: {saved['revision']}", document)
        second = reports.export_saved_report(saved["id"])
        self.assertNotEqual(path, second)
        self.assertEqual(path.read_text(encoding="utf-8"), document)

    def test_linked_report_directory_rejected(self):
        lab = store.create_lab("Evidence")
        external = self.home / "external"
        external.mkdir()
        (store.BASE / "reports").symlink_to(external, target_is_directory=True)
        with self.assertRaisesRegex(store.StorageError, "linked"):
            reports.export_saved_report(lab["id"])
        self.assertFalse(list(external.iterdir()))

    def test_no_shell_network_or_automatic_webbie(self):
        source = (RUNTIME / "lab_reports.py").read_text()
        for token in ("subprocess", "requests.", "socket.", "webbie.sock", "os.system"):
            self.assertNotIn(token, source)


class GuidesQtTests(unittest.TestCase):
    def test_guides_tab_and_explicit_export(self):
        script = r"""
import importlib.util, sys, tempfile
from pathlib import Path
from unittest.mock import patch
from subprocess import CompletedProcess
from PyQt5.QtWidgets import QApplication, QMessageBox
root = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("kali_guide_ui",root/"kali-bay/ui/kali_bay.py")
ui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ui)
app = QApplication([])
with tempfile.TemporaryDirectory() as d:
    home=Path(d)
    base=home/".local/share/spider-os/kali-bay/projects"
    with patch.object(Path,"home",return_value=home), \
         patch.object(ui.kali_store,"BASE",base), \
         patch.object(ui.subprocess,"run",
                      return_value=CompletedProcess([],0,"missing","")):
        win=ui.KaliBayWindow()
        assert win.security_tabs.count()==6
        assert win.security_tabs.tabText(4)=="LAB GUIDES"
        assert win.security_tabs.tabText(5)=="EVIDENCE LEDGER"
        assert win.guide_list.count()>=8
        win.guide_search.setText("packet")
        assert win.guide_list.count()==1
        with patch.object(QMessageBox,"question",return_value=QMessageBox.Yes):
            win.create_guided_lab()
        assert win.active_lab is not None
        saved = ui.kali_store.get_lab(win.active_lab["id"])
        assert "CHECKLIST:" in saved["notes"]
        assert win.security_tabs.currentIndex()==3
        win.export_active_lab_report()
        export_dir=base/"reports"
        exports=list(export_dir.glob("*.md"))
        assert len(exports)==1
        assert saved["title"] in exports[0].read_text()
        win.lab_editor.setPlainText("UNSAVED EDITS")
        with patch.object(QMessageBox,"information") as inform:
            win.export_active_lab_report()
            assert inform.called
        assert len(list(export_dir.glob("*.md")))==1
        assert win.webbie_worker is None
        assert not win.webbie_chat_log.toPlainText()
        win.close()
"""
        result = subprocess.run(
            [sys.executable,"-c",script,str(ROOT)],
            cwd=ROOT,env=dict(os.environ,QT_QPA_PLATFORM="offscreen"),
            capture_output=True,text=True,timeout=30,
        )
        self.assertEqual(result.returncode,0,result.stderr)


if __name__=="__main__":
    unittest.main()
