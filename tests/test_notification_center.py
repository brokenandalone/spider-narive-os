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
