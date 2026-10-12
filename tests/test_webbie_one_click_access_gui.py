"""One-click Webbie UI uses one deliberate click and never starts risky actions."""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"the-web/shell"))
try:
    from PyQt5.QtWidgets import QApplication,QMessageBox,QPushButton
    from webbie_computer_panel import WebbieComputerDialog
    from webbie_panel import WebbiePanel
    QT=True
except ImportError:
    QT=False

@unittest.skipUnless(QT,"Qt is needed for one-click owner access UI")
class OwnerOneClickUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])

    @staticmethod
    def apps():
        return [
            SimpleNamespace(name="Audacity",desktop_id="audacity.desktop",
                            workspace="studio",path=Path("/usr/share/applications/audacity.desktop")),
            SimpleNamespace(name="Firefox",desktop_id="firefox.desktop",
                            workspace="web",path=Path("/usr/share/applications/firefox.desktop")),
            SimpleNamespace(name="Terminal",desktop_id="konsole.desktop",
                            workspace="system",path=Path("/usr/share/applications/konsole.desktop")),
        ]

    def test_single_click_enables_two_apps_without_dialog_or_program_launch(self):
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{"DISPLAY":":0"}),patch(
                "webbie_operator_bridge.private_socket_directory",
                return_value=Path(folder)):
            started=Mock()
            dialog=WebbieComputerDialog(
                discover=self.apps,launcher=started,run=Mock())
            try:
                button=dialog.findChild(QPushButton,"webbieOneClickSafeAccess")
                self.assertIsNotNone(button)
                with patch("webbie_computer_panel.QMessageBox.question",
                           side_effect=AssertionError("No repeated auth")):
                    button.click()
                self.assertTrue(dialog.grant.status()["wide"])
                self.assertEqual(dialog.grant.status()["eligible_apps"],2)
                self.assertTrue(dialog.bridge.server.isListening())
                started.assert_not_called()
                self.assertFalse(dialog.click_button.isEnabled())
                self.assertFalse(dialog.type_button.isEnabled())
                self.assertFalse(dialog.close_button.isEnabled())
                self.assertFalse(dialog.open_web_button.isEnabled())
                self.assertTrue(dialog.open_button.isEnabled())
                self.assertTrue(dialog.findChild(QPushButton,"webbieSafeServicesStatus").isEnabled())
                dialog.stop()
                self.assertFalse(dialog.grant.status()["active"])
                started.assert_not_called()
            finally:
                dialog.close()

    def test_selection_changes_eligible_apps_without_reauthorizing(self):
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{"DISPLAY":":0"}),patch(
                "webbie_operator_bridge.private_socket_directory",
                return_value=Path(folder)):
            dialog=WebbieComputerDialog(discover=self.apps,run=Mock())
            try:
                dialog.authorize_wide_access()
                dialog.app_select.setCurrentIndex(1)
                self.assertEqual(
                    dialog.grant.status()["selected_app_id"],"firefox.desktop")
                self.assertTrue(dialog.grant.authorize(
                    "app.open","app_id=firefox.desktop"))
                dialog.app_select.setCurrentIndex(2)
                self.assertEqual(dialog.grant.status()["selected_app_id"],"")
                self.assertFalse(dialog.grant.authorize(
                    "app.open","app_id=konsole.desktop"))
            finally:
                dialog.close()

    def test_already_approved_typing_open_starts_safe_program_without_new_prompt(self):
        with tempfile.TemporaryDirectory() as folder,patch.dict(
                os.environ,{"DISPLAY":":0"}),patch(
                "webbie_operator_bridge.private_socket_directory",
                return_value=Path(folder)):
            started=Mock()
            dialog=WebbieComputerDialog(
                discover=self.apps,launcher=started,run=Mock())
            try:
                dialog.authorize_wide_access()
                with patch("desktop_control.app_catalog",return_value=
                           SimpleNamespace(launch_command=lambda app:[
                               "gio","launch",str(app.path)])),patch(
                           "webbie_computer_panel.QMessageBox.question",
                           side_effect=AssertionError("No new approval")):
                    self.assertTrue(dialog.open_program_safe("audacity.desktop"))
                    self.assertTrue(dialog.open_program_safe("firefox.desktop"))
                self.assertEqual(started.call_count,2)
                self.assertFalse(dialog.open_program_safe("konsole.desktop"))
                self.assertEqual(started.call_count,2)
            finally:
                dialog.close()

    def test_no_bypass_of_existing_owner_confirmation_when_not_wide(self):
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{"DISPLAY":":0"}),patch(
                "webbie_operator_bridge.private_socket_directory",
                return_value=Path(folder)):
            dialog=WebbieComputerDialog(discover=self.apps,run=Mock())
            try:
                self.assertFalse(dialog.grant.status()["wide"])
                dialog.task.setText("Owner-chosen editing task")
                with patch("webbie_computer_panel.QMessageBox.question",
                           return_value=QMessageBox.No):
                    dialog.authorize()
                self.assertFalse(dialog.grant.status()["active"])
            finally:
                dialog.close()

    def test_main_panel_shows_explicit_one_click_and_revoke_controls(self):
        source=(ROOT/"the-web/shell/webbie_panel.py").read_text()
        self.assertIn("webbieOwnerOneClickAccess",source)
        self.assertIn("webbieOwnerRevokeAll",source)
        self.assertIn("self.computer_dialog.authorize_wide_access()",source)
        self.assertIn("revoke.clicked.connect(self.stop_sensitive_actions)",source)

if __name__=="__main__":
    unittest.main()
