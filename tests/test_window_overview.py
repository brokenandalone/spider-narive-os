"""Qt test for user-controlled X11 windows overview and safe close requests."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'the-web/shell'))
from PyQt5.QtWidgets import QApplication
from desktop import Task
import window_overview as overview

APP=QApplication.instance() or QApplication([])


class WindowOverviewTests(unittest.TestCase):
    def test_valid_ids_cannot_include_shell_arguments(self):
        for bad in ('', '0x0', '0xABC;shutdown', '-e', '0x12 /tmp', None, 123, '123'):
            self.assertFalse(overview.valid_id(bad))
        self.assertTrue(overview.valid_id('0x00a55b'))

    def test_overview_is_searchable_and_uses_regular_wm_requests(self):
        data=[Task('0x00111','Browser'),Task('0x00222','Writer Notes'),
              Task('0x00333','Video Player')]
        with patch.object(overview,'list_tasks',return_value=data) as reader, \
             patch.object(overview,'wm_command') as activate, \
             patch.object(overview,'minimize_window',return_value=True) as minimize, \
             patch.object(overview,'maximize_window') as maximize, \
             patch.object(overview,'close_window') as close:
            panel=overview.WindowOverview(excluded=lambda:('0x999',))
            self.assertTrue(panel.worker.wait(4000))
            APP.processEvents()
            reader.assert_called_with(('0x999',))
            self.assertEqual(panel.list.count(),3)
            panel.search.setText('writer')
            self.assertEqual(panel.list.count(),1)
            self.assertEqual(panel.selected_id(),'0x00222')
            panel.activate()
            activate.assert_called_once_with('-i','-a','0x00222')
            panel.minimize(); minimize.assert_called_once_with('0x00222')
            panel.maximize(); maximize.assert_called_once_with('0x00222')
            panel.close_selected(); close.assert_called_once_with('0x00222')
            self.assertIn('may ask you to save',panel.status.text())
            panel.close()

    def test_unknown_windows_and_missing_manager_are_safe(self):
        with patch.object(overview,'list_tasks',return_value=[Task('bad','Malicious'),
                                                               Task('0x0000','Invalid')]):
            panel=overview.WindowOverview()
            self.assertTrue(panel.worker.wait(4000))
            APP.processEvents()
            self.assertEqual(panel.list.count(),0)
            self.assertIsNone(panel.selected_id())
            with patch.object(overview,'close_window') as close:
                panel.close_selected()
                close.assert_not_called()
            panel.close()

    def test_failed_minimize_does_not_kill_processes(self):
        with patch.object(overview,'list_tasks',return_value=[Task('0x00222','Editor')]), \
             patch.object(overview,'minimize_window',return_value=False), \
             patch.object(overview,'close_window') as close:
            panel=overview.WindowOverview()
            self.assertTrue(panel.worker.wait(4000))
            APP.processEvents()
            panel.minimize()
            self.assertIn('Unable to minimize',panel.status.text())
            close.assert_not_called()
            panel.close()


if __name__=='__main__':
    unittest.main()
