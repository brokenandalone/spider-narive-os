"""Native Jarvis navigation review tests, completely offline."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"the-web/shell"))
try:
    from PyQt5.QtWidgets import QApplication
    from webbie_computer_panel import WebbieComputerDialog
    QT=True
except ImportError:
    QT=False


@unittest.skipUnless(QT,"PyQt5 required for native Jarvis mission tests")
class NavigationGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])

    def panel(self,folder,browser=True):
        entry=Path(folder)/"selected.desktop"
        entry.write_text("[Desktop Entry]\nName=Browser Test\nCategories="+
                         ("WebBrowser;Network;" if browser else "Office;")+"\n")
        app=SimpleNamespace(name="Browser Test",desktop_id="selected.desktop",
                            workspace="forage",path=entry)
        commands=[]
        def runner(args,**kwargs):
            commands.append(args)
            if args==["wmctrl","-lp"]:
                return SimpleNamespace(stdout="0x1 0 123 localhost Browser Test\n")
            if args==["xdotool","getactivewindow"]:
                return SimpleNamespace(stdout="1\n")
            return SimpleNamespace(stdout="")
        gui=WebbieComputerDialog(discover=lambda:[app],run=runner,
                                 launcher=Mock(),browser_opener=Mock())
        return gui,commands

    def approve_target(self,gui):
        # Simulate trusted local GUI approval and owner window selection;
        # the tests do not turn on microphone or click outside this process.
        gui.grant.activate("Help navigate this window","selected.desktop")
        gui.operator.begin_new_task()
        gui.windows.addItem("Browser Test","0x1")
        gui.operator.target_window="0x1"
        gui.refresh_status()

    def test_proposal_does_not_press_keys(self):
        with tempfile.TemporaryDirectory() as temp,patch.dict(
                os.environ,{"DISPLAY":":0"}),patch(
                "webbie_operator_bridge.private_socket_directory",
                return_value=Path(temp)):
            gui,calls=self.panel(temp)
            try:
                self.assertTrue(gui.offer_navigation("scroll down twice"))
                self.assertFalse(gui.grant.status()["active"])
                self.assertEqual(calls,[])
                gui.preview_navigation()
                self.assertIsNone(gui.nav_mission.plan)
                self.assertEqual(calls,[])
            finally:
                gui.close()

    def test_each_step_requires_separate_owner_click(self):
        with tempfile.TemporaryDirectory() as temp,patch.dict(
                os.environ,{"DISPLAY":":0"}),patch(
                "webbie_operator_bridge.private_socket_directory",
                return_value=Path(temp)):
            gui,calls=self.panel(temp)
            try:
                self.approve_target(gui)
                gui.offer_navigation("scroll down twice")
                gui.preview_navigation()
                self.assertIsNotNone(gui.nav_mission.plan)
                self.assertEqual(calls,[])
                gui.run_navigation_step()
                keystrokes=[a for a in calls if a[:2]==["xdotool","key"]]
                self.assertEqual(len(keystrokes),1)
                self.assertIn("Page_Down",keystrokes[0])
                self.assertIsNotNone(gui.nav_mission.plan)
                gui.run_navigation_step()
                keystrokes=[a for a in calls if a[:2]==["xdotool","key"]]
                self.assertEqual(len(keystrokes),2)
                self.assertIsNone(gui.nav_mission.plan)
                self.assertIn("Navigation plan finished",gui.activity.toPlainText())
            finally:
                gui.close()

    def test_stop_revokes_pending_sequence(self):
        with tempfile.TemporaryDirectory() as temp,patch.dict(
                os.environ,{"DISPLAY":":0"}),patch(
                "webbie_operator_bridge.private_socket_directory",
                return_value=Path(temp)):
            gui,calls=self.panel(temp)
            try:
                self.approve_target(gui)
                gui.offer_navigation("scroll up twice")
                gui.preview_navigation()
                gui.stop()
                gui.run_navigation_step()
                self.assertEqual([x for x in calls if x[:2]==["xdotool","key"]],[])
                self.assertIn("Desktop control stopped",gui.activity.toPlainText())
            finally:
                gui.close()

    def test_browser_only_shortcut_denied_in_office_app(self):
        with tempfile.TemporaryDirectory() as temp,patch.dict(
                os.environ,{"DISPLAY":":0"}),patch(
                "webbie_operator_bridge.private_socket_directory",
                return_value=Path(temp)):
            gui,calls=self.panel(temp,browser=False)
            try:
                self.approve_target(gui)
                gui.offer_navigation("go back")
                gui.preview_navigation()
                self.assertIsNone(gui.nav_mission.plan)
                gui.run_navigation_step()
                self.assertEqual([x for x in calls if x[:2]==["xdotool","key"]],[])
            finally:
                gui.close()

    def test_voice_stages_without_executing(self):
        with tempfile.TemporaryDirectory() as temp,patch.dict(
                os.environ,{"DISPLAY":":0"}),patch(
                "webbie_operator_bridge.private_socket_directory",
                return_value=Path(temp)):
            gui,calls=self.panel(temp)
            try:
                self.approve_target(gui)
                gui.handle_voice_navigation("Webbie scroll down twice")
                self.assertIn("scroll down twice",gui.navigation_input.text())
                self.assertIsNone(gui.nav_mission.plan)
                self.assertEqual(calls,[])
            finally:
                gui.close()


if __name__=="__main__":
    unittest.main()
