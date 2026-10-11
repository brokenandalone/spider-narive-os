"""Jarvis browser GUI permission tests: no real windows, browser, or network."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "the-web/shell"))
try:
    from PyQt5.QtWidgets import QApplication, QMessageBox, QScrollArea
    from webbie_computer_panel import WebbieComputerDialog
    QT = True
except ImportError:
    QT = False


@unittest.skipUnless(QT, "PyQt5 is needed for native Jarvis GUI")
class JarvisBrowserGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make(self, folder, browser=True, opener=None):
        entry = Path(folder) / "app.desktop"
        entry.write_text("[Desktop Entry]\nName=Test app\nCategories=" +
                         ("Network;WebBrowser;" if browser else "Office;") + "\n")
        app = SimpleNamespace(
            name="Test app", desktop_id="test.desktop", workspace="forage",
            path=entry)
        panel = WebbieComputerDialog(discover=lambda: [app], run=Mock(),
                                    launcher=Mock(), browser_opener=opener)
        return panel

    def test_control_panel_has_scrollable_layout(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(
                os.environ, {"DISPLAY": ":0"}), patch(
                "webbie_operator_bridge.private_socket_directory",
                return_value=Path(temp)):
            panel = self.make(temp, opener=Mock(return_value=True))
            try:
                self.assertIsNotNone(
                    panel.findChild(QScrollArea, "webbieControlsScrollable"))
            finally:
                panel.close()

    def test_voice_proposal_never_grants_or_launches(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(
                os.environ, {"DISPLAY": ":0"}), patch(
                "webbie_operator_bridge.private_socket_directory",
                return_value=Path(temp)):
            open_url = Mock(return_value=True)
            panel = self.make(temp, opener=open_url)
            try:
                self.assertTrue(panel.offer_site("https://github.com/"))
                self.assertEqual(panel.browser_url.text(), "https://github.com/")
                self.assertFalse(panel.grant.status()["active"])
                self.assertFalse(panel.open_website())
                open_url.assert_not_called()
            finally:
                panel.close()

    def test_browser_open_requires_grant_and_url_confirmation(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(
                os.environ, {"DISPLAY": ":0"}), patch(
                "webbie_operator_bridge.private_socket_directory",
                return_value=Path(temp)):
            open_url = Mock(return_value=True)
            panel = self.make(temp, opener=open_url)
            try:
                self.assertTrue(panel.offer_site("github.com"))
                panel.grant.activate("Open one website", "test.desktop")
                panel.operator.begin_new_task()
                with patch("webbie_computer_panel.QMessageBox.question",
                           return_value=QMessageBox.No):
                    self.assertFalse(panel.open_website())
                open_url.assert_not_called()
                with patch("webbie_computer_panel.QMessageBox.question",
                           return_value=QMessageBox.Yes):
                    self.assertTrue(panel.open_website())
                self.assertEqual(open_url.call_count, 1)
                self.assertEqual(open_url.call_args.args[0].toString(),
                                 "https://github.com/")
                panel.stop()
                self.assertFalse(panel.open_website())
                self.assertEqual(open_url.call_count, 1)
            finally:
                panel.close()

    def test_nonbrowser_grant_cannot_open_website(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(
                os.environ, {"DISPLAY": ":0"}), patch(
                "webbie_operator_bridge.private_socket_directory",
                return_value=Path(temp)):
            open_url = Mock(return_value=True)
            panel = self.make(temp, browser=False, opener=open_url)
            try:
                self.assertFalse(panel.offer_site("github.com"))
                panel.grant.activate("edit a document", "test.desktop")
                panel.operator.begin_new_task()
                self.assertFalse(panel.open_website("https://github.com/"))
                open_url.assert_not_called()
            finally:
                panel.close()


if __name__ == "__main__":
    unittest.main()
