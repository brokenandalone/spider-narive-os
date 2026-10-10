"""Supervised Autopilot GUI grants and stop work without capturing PC screen."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock,patch
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'the-web/shell'))
try:
    from PyQt5.QtWidgets import QApplication,QMessageBox
    from webbie_computer_panel import WebbieComputerDialog
    QT=True
except ImportError:
    QT=False


@unittest.skipUnless(QT,'Qt required for Webbie UI regression')
class AutopilotGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])

    def test_owner_approved_autopilot_is_bounded_and_stop_revokes(self):
        with tempfile.TemporaryDirectory() as folder, \
             patch.dict(os.environ,{'DISPLAY':':0}), \
             patch('webbie_operator_bridge.private_socket_directory',
                   return_value=Path(folder)):
            app=SimpleNamespace(name='Audacity',desktop_id='audacity.desktop',
                                workspace='studio',
                                path=Path('/usr/share/applications/audacity.desktop'))
            dialog=WebbieComputerDialog(discover=lambda:[app],launcher=Mock(),
                                        run=Mock())
            try:
                dialog.windows.addItem('Audacity Mix','0x01')
                dialog.operator.target_window='0x01'
                dialog.grant.activate('Navigate audio tracks','audacity.desktop',seconds=300)
                dialog.operator.begin_new_task()
                dialog.operator.target_window='0x01'
                dialog.refresh_status()
                with patch('webbie_computer_panel.QMessageBox.question',
                           return_value=QMessageBox.Yes), \
                     patch('webbie_computer_panel.QTimer.singleShot') as pending:
                    dialog.begin_autopilot()
                    self.assertTrue(dialog.autopilot.active)
                    pending.assert_called_once()
                    self.assertEqual(dialog.autopilot.limit,6)
                    dialog.stop()
                    self.assertFalse(dialog.autopilot.active)
                    self.assertFalse(dialog.grant.status()['active'])
            finally:
                dialog.close()

    def test_rejects_autopilot_without_task_window(self):
        with tempfile.TemporaryDirectory() as folder, \
             patch.dict(os.environ,{'DISPLAY':':0}), \
             patch('webbie_operator_bridge.private_socket_directory',
                   return_value=Path(folder)):
            app=SimpleNamespace(name='Firefox',desktop_id='firefox.desktop',
                                workspace='forage',
                                path=Path('/usr/share/applications/firefox.desktop'))
            dialog=WebbieComputerDialog(discover=lambda:[app],launcher=Mock(),run=Mock())
            try:
                dialog.begin_autopilot()
                self.assertFalse(dialog.autopilot.active)
                self.assertFalse(dialog.grant.status()['active'])
            finally:
                dialog.close()


if __name__=='__main__':
    unittest.main()
