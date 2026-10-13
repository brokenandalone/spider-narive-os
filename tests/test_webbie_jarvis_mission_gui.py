"""Offscreen JARVIS Mission Center UI tests; no PC actions or network access."""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"the-web/shell"))
sys.path.insert(0,str(ROOT/"webbie/actions"))
try:
    from PyQt5.QtWidgets import QApplication,QPushButton,QComboBox
    from PyQt5.QtTest import QTest
    from webbie_jarvis_mission_center import JarvisMissionCenter
    from jarvis_orchestrator import MissionResult
    HAS_QT=True
except ImportError:
    HAS_QT=False

class FakeCore:
    def __init__(self):
        self.calls=[]
        self.stop=Mock()
        self.preview=type("Preview",(),{
            "status":lambda self:{"running":False,"url":"","scope":""}})()

    def run(self,action,*,source,folder=None,query=None,home=None):
        self.calls.append((action,source,folder,query))
        return MissionResult(action,"observed","Test evidence, no changes.",True)

@unittest.skipUnless(HAS_QT,"PyQt5 is required for native Webbie UI")
class JarvisMissionCenterUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])

    def test_visible_owner_action_picker_and_stop_controls(self):
        fake=FakeCore()
        allstop=Mock()
        dlg=JarvisMissionCenter(core=fake,stop_callback=allstop)
        try:
            self.assertIsNotNone(
                dlg.findChild(QPushButton,"webbieJarvisRun"))
            self.assertIsNotNone(
                dlg.findChild(QPushButton,"webbieJarvisChooseFolder"))
            self.assertIsNotNone(
                dlg.findChild(QPushButton,"webbieJarvisGlobalStop"))
            self.assertIsNotNone(
                dlg.findChild(QComboBox,"webbieJarvisOperation"))
            self.assertFalse(dlg.run_button.isEnabled())
            self.assertEqual(fake.calls,[])
            dlg.action.setCurrentIndex(
                dlg.action.findData("system.health")) # no file root
            self.assertTrue(dlg.run_button.isEnabled())
            dlg.run_button.click()
            QTest.qWait(200)
            self.assertEqual(
                fake.calls,[("system.health","owner_gui",None,"")])
            self.assertIn("observed",dlg.report.toPlainText())
            dlg.stop_all()
            allstop.assert_called_once()
            fake.stop.assert_called()
        finally:
            dlg.close()

    def test_folder_required_before_file_or_site_action(self):
        fake=FakeCore()
        dlg=JarvisMissionCenter(core=fake)
        try:
            self.assertFalse(dlg.run_button.isEnabled())
            with tempfile.TemporaryDirectory() as temp:
                dlg.folder=str(Path(temp))
                dlg.refresh()
                self.assertTrue(dlg.run_button.isEnabled())
                dlg.query.setText("Broken City")
                dlg.run_button.click()
                QTest.qWait(200)
                self.assertEqual(fake.calls[0][0],"local.evidence")
                self.assertEqual(fake.calls[0][1],"owner_gui")
        finally:
            dlg.close()

    def test_main_webbie_and_cognitive_center_share_mission_entry(self):
        panel=(ROOT/"the-web/shell/webbie_panel.py").read_text()
        cognitive=(ROOT/"the-web/shell/webbie_cognitive_center.py").read_text()
        self.assertIn("webbieJarvisMissionCenterButton",panel)
        self.assertIn("open_jarvis_mission_center",panel)
        self.assertIn("jarvis_mission_dialog.core.stop()",panel)
        self.assertIn("webbieJarvisMissionCognitiveButton",cognitive)
        self.assertIn("mission_callback=self.open_jarvis_mission_center",panel)

if __name__=="__main__":
    unittest.main()
