"""Test notification popup behavior without accessing live DBus services."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import json
from pathlib import Path
import tempfile
import unittest
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'the-web/shell'))
from PyQt5.QtWidgets import QApplication
from notification_center import save_state
from notification_toast import NotificationToast,newest_event
APP=QApplication.instance() or QApplication([])

class PopupTests(unittest.TestCase):
    def test_new_notification_appears_and_dnd_suppresses_next(self):
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary)
            state=base/'notifications.json'
            journal=base/'external-notifications.jsonl'
            save_state(state,{'dnd':False,'items':[]})
            toast=NotificationToast(state_path=state)
            def log(n):
                journal.write_text(json.dumps({'app':'Mail','title':'Message '+str(n),
                    'message':'Testing','time':str(n)})+'\n')
            log(1);toast.refresh()
            self.assertTrue(toast.isVisible())
            self.assertIn('Message 1',toast.title.text())
            toast.hide()
            save_state(state,{'dnd':True,'items':[]})
            log(2);toast.refresh()
            self.assertFalse(toast.isVisible())
            toast.close()

    def test_identical_notifications_with_distinct_ids_both_appear(self):
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary)
            state=base/'notifications.json'
            journal=base/'external-notifications.jsonl'
            save_state(state,{'dnd':False,'items':[]})
            toast=NotificationToast(state_path=state)
            data={'app':'Mail','title':'Same event','message':'Identical text',
                  'time':'2026-10-09T15:00:00'}
            data['id']='event-one'
            journal.write_text(json.dumps(data)+'\n')
            toast.refresh()
            first=toast.last_key
            toast.hide()
            data['id']='event-two'
            journal.write_text(json.dumps(data)+'\n')
            toast.refresh()
            self.assertTrue(toast.isVisible())
            self.assertNotEqual(toast.last_key,first)
            self.assertEqual(toast.message.text(),'Identical text')
            toast.close()

    def test_external_markup_is_rendered_as_plain_text(self):
        from PyQt5.QtCore import Qt
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary)
            state=base/'notifications.json'
            journal=base/'external-notifications.jsonl'
            save_state(state,{'dnd':False,'items':[]})
            toast=NotificationToast(state_path=state)
            journal.write_text(json.dumps({'app':'Mail','title':'<b>Fake alert</b>',
                'message':'<a href="https://invalid.example">Unexpected link</a>',
                'time':'t','id':'plain-text-test'})+'\n')
            toast.refresh()
            self.assertEqual(toast.title.textFormat(),Qt.PlainText)
            self.assertEqual(toast.message.textFormat(),Qt.PlainText)
            self.assertTrue(toast.isVisible())
            toast.close()

    def test_journal_symlink_is_not_read(self):
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary)
            private=base/'sensitive'
            private.write_text('secret')
            journal=base/'external-notifications.jsonl'
            journal.symlink_to(private)
            self.assertIsNone(newest_event(journal))
            self.assertEqual(private.read_text(),'secret')

if __name__=='__main__':
    unittest.main()
