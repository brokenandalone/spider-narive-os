"""Offscreen Webbie receipts GUI: website open request is never 'page loaded'."""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"the-web/shell"))
try:
    from PyQt5.QtWidgets import QApplication,QMessageBox,QLabel
    from webbie_computer_panel import WebbieComputerDialog
    QT=True
except ImportError:
    QT=False

@unittest.skipUnless(QT,"PyQt5 required for Jarvis receipt UI tests")
class ReceiptGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])

    def test_browser_request_and_stop_report_truthful_result(self):
        with tempfile.TemporaryDirectory() as tmp,patch.dict(
                os.environ,{"DISPLAY":":0"}),patch(
                "webbie_operator_bridge.private_socket_directory",
                return_value=Path(tmp)):
            entry=Path(tmp)/"test.desktop"
            entry.write_text("[Desktop Entry]\nName=Test Browser\nCategories=Network;WebBrowser;\n")
            app=SimpleNamespace(name="Test Browser",
                                desktop_id="test.desktop",workspace="forage",path=entry)
            opener=Mock(return_value=True)
            dialog=WebbieComputerDialog(discover=lambda:[app],run=Mock(),
                                        launcher=Mock(),browser_opener=opener)
            try:
                self.assertIsNotNone(dialog.findChild(QLabel,"webbieLastActionReceipt"))
                dialog.offer_site("github.com")
                dialog.grant.activate("Owner-reviewed website task","test.desktop")
                dialog.operator.begin_new_task()
                with patch("webbie_computer_panel.QMessageBox.question",
                           return_value=QMessageBox.Yes):
                    self.assertTrue(dialog.open_website())
                label=dialog.receipt_label.text()
                self.assertIn("completion not verified",label)
                self.assertNotIn("github.com",label)
                self.assertEqual(opener.call_count,1)
                dialog.stop()
                self.assertIn("canceled",dialog.receipt_label.text())
            finally:
                dialog.close()

    def test_denial_never_calls_browser(self):
        with tempfile.TemporaryDirectory() as tmp,patch.dict(
                os.environ,{"DISPLAY":":0"}),patch(
                "webbie_operator_bridge.private_socket_directory",
                return_value=Path(tmp)):
            entry=Path(tmp)/"test.desktop"
            entry.write_text("[Desktop Entry]\nName=Test Browser\nCategories=Network;WebBrowser;\n")
            app=SimpleNamespace(name="Test Browser",desktop_id="test.desktop",
                                workspace="forage",path=entry)
            opener=Mock(return_value=True)
            dialog=WebbieComputerDialog(discover=lambda:[app],run=Mock(),
                                        launcher=Mock(),browser_opener=opener)
            try:
                self.assertFalse(dialog.open_website("github.com"))
                self.assertIn("denied",dialog.receipt_label.text())
                opener.assert_not_called()
            finally:
                dialog.close()

if __name__=="__main__":
    unittest.main()
