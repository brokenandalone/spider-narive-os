"""Source regression tests for Spider OS volume controls."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import sys
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'the-web/shell'))
from PyQt5.QtWidgets import QApplication
import volume_panel
APP=QApplication.instance() or QApplication([])

class VolumeTests(unittest.TestCase):
    def test_volume_bounds(self):
        for value in (-1,101,1.5,True):
            with self.assertRaises(ValueError):
                volume_panel.set_volume_percent(value)

    def test_command_is_bounded_and_device_scoped(self):
        with patch.object(volume_panel.shutil,'which',return_value='/usr/bin/wpctl'),patch.object(volume_panel.subprocess,'run',return_value=MagicMock(returncode=0)) as runner:
            volume_panel.set_volume_percent(62)
            runner.assert_called_once()
            self.assertEqual(runner.call_args.args[0],['/usr/bin/wpctl','set-volume','--limit','1.0','@DEFAULT_AUDIO_SINK@','62%'])
            self.assertLessEqual(runner.call_args.kwargs['timeout'],3)

    def test_mute_toggle_only_default_output(self):
        with patch.object(volume_panel.shutil,'which',return_value='/usr/bin/wpctl'),patch.object(volume_panel.subprocess,'run',return_value=MagicMock(returncode=0)) as runner:
            volume_panel.toggle_mute()
            self.assertEqual(runner.call_args.args[0],['/usr/bin/wpctl','set-mute','@DEFAULT_AUDIO_SINK@','toggle'])

    def test_missing_wireplumber_disables_controls(self):
        with patch.object(volume_panel.shutil,'which',return_value=None):
            panel=volume_panel.VolumePanel()
            self.assertTrue(panel.worker.wait(3000))
            APP.processEvents()
            self.assertFalse(panel.slider.isEnabled())
            self.assertFalse(panel.mute.isEnabled())
            self.assertIn('unavailable',panel.status.text().lower())
            panel.close()

    def test_volume_and_mute_render(self):
        with patch.object(volume_panel,'volume_state',return_value=(36,True)):
            panel=volume_panel.VolumePanel()
            self.assertTrue(panel.worker.wait(3000))
            APP.processEvents()
            self.assertEqual(panel.slider.value(),36)
            self.assertIn('Muted',panel.status.text())
            panel.close()

    def test_refresh_starts_worker_without_blocking_qt_gui(self):
        import threading
        started=threading.Event()
        proceed=threading.Event()
        def delayed_read():
            started.set()
            if not proceed.wait(2):
                return (None,False)
            return (44,False)
        with patch.object(volume_panel,'volume_state',side_effect=delayed_read):
            panel=volume_panel.VolumePanel()
            self.assertTrue(started.wait(2))
            self.assertFalse(panel.mute.isEnabled())
            # GUI is still responsive while the audio query is running.
            APP.processEvents()
            self.assertTrue(panel.worker.isRunning())
            proceed.set()
            self.assertTrue(panel.worker.wait(3000))
            APP.processEvents()
            self.assertEqual(panel.slider.value(),44)
            self.assertTrue(panel.mute.isEnabled())
            panel.close()

if __name__ == '__main__':
    unittest.main()
