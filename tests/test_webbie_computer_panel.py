"""Computer control GUI must require explicit owner approval and revoke."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'the-web/shell'))
try:
    from PyQt5.QtWidgets import QApplication, QMessageBox
    from webbie_computer_panel import WebbieComputerDialog, parse_open_request
    QT=True
except ImportError:
    QT=False


@unittest.skipUnless(QT, 'PyQt5 required for native Webbie operator panel')
class WebbieComputerPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])

    def sample(self):
        return SimpleNamespace(name='Audacity',desktop_id='audacity.desktop',
                               workspace='studio',path=Path('/usr/share/applications/audacity.desktop'))

    def test_voice_open_parser_does_not_open_other_app(self):
        apps=[self.sample()]
        self.assertEqual(parse_open_request('Webby open Audacity',apps).desktop_id,'audacity.desktop')
        self.assertEqual(parse_open_request('open Audacity',apps).desktop_id,'audacity.desktop')
        self.assertIsNone(parse_open_request('open uninstalled tool',apps))
        self.assertIsNone(parse_open_request('Webbie delete my documents',apps))

    def test_panel_grant_is_local_and_stop_revokes(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,{'DISPLAY':':0'}), \
             patch('webbie_operator_bridge.private_socket_directory',
                   return_value=Path(tmp)):
            app=self.sample()
            started=Mock()
            dialog=WebbieComputerDialog(
                discover=lambda:[app], launcher=started,
                run=Mock())
            try:
                self.assertFalse(dialog.grant.status()['active'])
                self.assertTrue(dialog.operator.cancelled.is_set())
                started.assert_not_called()
                dialog.task.setText('Help me edit a recording')
                with patch('webbie_computer_panel.QMessageBox.question',
                           return_value=QMessageBox.Yes):
                    dialog.authorize()
                self.assertTrue(dialog.grant.status()['active'])
                self.assertTrue(dialog.bridge.server.isListening())
                # Grant is not an instruction to open anything.
                started.assert_not_called()
                dialog.stop()
                self.assertFalse(dialog.grant.status()['active'])
                self.assertFalse(dialog.bridge.server.isListening())
                started.assert_not_called()
            finally:
                dialog.close()


if __name__=='__main__':unittest.main()
