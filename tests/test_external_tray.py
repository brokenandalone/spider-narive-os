"""Background tray and third-party notification source tests."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'the-web/shell'))
from PyQt5.QtWidgets import QApplication
import notification_bridge as bridge
import status_tray
from notification_center import NotificationCenter
from tray_panel import TrayPanel
APP=QApplication.instance() or QApplication([])

class ExternalTrayTests(unittest.TestCase):
    def test_private_external_history_visible_in_alerts(self):
        with tempfile.TemporaryDirectory() as tmp:
            state=Path(tmp)/'notifications.json'
            bridge.append_history(state.parent/'external-notifications.jsonl','New mail','A message arrived','Mail')
            panel=NotificationCenter(path=state)
            self.assertEqual(panel.history.count(),1)
            self.assertIn('Mail',panel.history.item(0).text())
            panel.close()

    def test_external_journal_rejects_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            private=root/'private'
            private.write_text('do not overwrite')
            target=root/'external-notifications.jsonl'
            target.symlink_to(private)
            with self.assertRaises(OSError):
                bridge.append_history(target,'Test','message','App')
            self.assertEqual(private.read_text(),'do not overwrite')

    def test_status_notifier_identifier_validation(self):
        self.assertEqual(status_tray.split_item('org.example.App/StatusNotifierItem'),
                         ('org.example.App','/StatusNotifierItem'))
        for value in ('','/StatusNotifierItem','org.example.App/../bad'):
            with self.assertRaises(ValueError):
                status_tray.split_item(value)

    def test_tray_metadata_renders_names_and_menu_capabilities(self):
        detail={'id':'org.example.App/StatusNotifierItem','service':'org.example.App',
                'title':'My Background App','status':'Active',
                'icon_name':'application-icon','menu':True}
        with patch('tray_panel.get_status_items',return_value=[detail['id']]), \
             patch('tray_panel.get_item_details',return_value=detail):
            panel=TrayPanel()
            panel.worker.wait(3000)
            APP.processEvents()
            self.assertEqual(panel.list.count(),1)
            self.assertIn('My Background App',panel.list.item(0).text())
            self.assertEqual(panel.items[0]['icon_name'],'application-icon')
            panel.close()

    def test_icon_names_are_restricted_to_theme_not_files(self):
        detail={'id':'org.example.App/StatusNotifierItem','service':'org.example.App',
                'title':'Music Service','status':'Active','icon_name':'audio-x-generic',
                'menu':False}
        with patch('tray_panel.get_status_items',return_value=[detail['id']]), \
             patch('tray_panel.get_item_details',return_value=detail):
            panel=TrayPanel()
            panel.worker.wait(3000)
            APP.processEvents()
            self.assertEqual(panel.list.count(),1)
            self.assertEqual(panel.items[0]['icon_name'],'audio-x-generic')
            panel.close()

    def test_tray_panel_lists_background_apps(self):
        with patch('tray_panel.get_status_items',return_value=[]):
            panel=TrayPanel()
            panel.worker.wait(3000)
            APP.processEvents()
            self.assertIn('No registered',panel.status.text())
            panel.close()

if __name__=='__main__':
    unittest.main()
