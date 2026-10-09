"""Tests for alerts expanding the existing open-window taskbar."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import sys
import tempfile
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'the-web/shell'))
from PyQt5.QtWidgets import QApplication
from notification_center import NotificationCenter, load_state
APP=QApplication.instance() or QApplication([])

class TaskbarAlertTests(unittest.TestCase):
    def test_notification_history_dnd_and_clear(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'state/notifications.json'
            center=NotificationCenter(path=path)
            self.assertTrue(center.add_notification('Webbie','New reply ready'))
            self.assertEqual(center.history.count(),1)
            center.dnd.setChecked(True)
            self.assertFalse(center.add_notification('Spider OS','Backup ready'))
            self.assertEqual(center.history.count(),2)
            self.assertTrue(load_state(path)['dnd'])
            center.close()
            reopened=NotificationCenter(path=path)
            self.assertEqual(reopened.history.count(),2)
            reopened.clear()
            self.assertEqual(reopened.history.count(),0)
            reopened.close()

    def test_clear_removes_both_external_app_history_and_local_alerts(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            state=Path(tmp)/'state/notifications.json'
            center=NotificationCenter(path=state)
            center.add_notification('Webbie','Reply ready')
            center.external_path.write_text(json.dumps({'app':'Mail','title':'Inbox',
                'message':'New message','time':'1'})+'\\n')
            center.refresh()
            self.assertEqual(center.history.count(),2)
            center.dnd.setChecked(True)
            center.clear()
            self.assertEqual(center.history.count(),0)
            self.assertEqual(center.external_path.read_text(),'')
            self.assertEqual(center.external_path.stat().st_mode & 0o777,0o600)
            self.assertTrue(load_state(state)['dnd'])
            center.refresh()
            self.assertEqual(center.history.count(),0)
            center.close()

    def test_external_journal_symlink_blocks_clear_without_touching_private_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            state=root/'notifications.json'
            private=root/'private_message'
            private.write_text('do not change')
            center=NotificationCenter(path=state)
            center.add_notification('System','Pending')
            center.external_path.symlink_to(private)
            with self.assertRaises(OSError):
                center.clear()
            self.assertEqual(private.read_text(),'do not change')
            self.assertEqual(len(load_state(state)['items']),1)
            center.close()

    def test_corrupt_external_log_line_does_not_hide_other_notifications(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            state=Path(tmp)/'notifications.json'
            center=NotificationCenter(path=state)
            content='not json\\n'+json.dumps({
                'app':'Mail','title':'Still here','message':'Visible',
                'time':'2'})+'\\n'
            center.external_path.write_text(content)
            center.refresh()
            self.assertEqual(center.history.count(),1)
            self.assertIn('Still here',center.history.item(0).text())
            center.close()

    def test_symlink_file_rejected_without_overwriting_private_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            private=root/'owner_private'
            private.write_text('no modifications')
            alias=root/'notifications.json'
            alias.symlink_to(private)
            self.assertEqual(load_state(alias)['items'],[])
            center=NotificationCenter(path=alias)
            with self.assertRaises(OSError):
                center.add_notification('Notice','Test')
            self.assertEqual(private.read_text(),'no modifications')
            center.close()

if __name__=='__main__':
    unittest.main()
