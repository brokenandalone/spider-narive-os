"""Quiet-sleep contract: visible portrait, ignored voice, wake on command only."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PyQt5.QtWidgets import QApplication
ROOT = Path(__file__).resolve().parents[1]
APP = QApplication.instance() or QApplication([])


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


night = load('night_mode_test', 'webbie/agent/night_mode.py')
overlay = load('overlay_sleep_test', 'the-web/overlay/webbie_face.py')


class QuietSleepTests(unittest.TestCase):
    def test_explicit_commands_only(self):
        self.assertEqual(night.spoken_mode('Hey Webbie, go to sleep'), 'sleep')
        self.assertEqual(night.spoken_mode('Good night, Webbie'), 'sleep')
        self.assertEqual(night.spoken_mode('Hey Webbie, good night'), 'sleep')
        self.assertEqual(night.spoken_mode('Hey Webbie, wake up', sleeping=True), 'wake')
        self.assertIsNone(night.spoken_mode('Hey Webbie', sleeping=True))
        self.assertIsNone(night.spoken_mode('Turn on the lights', sleeping=True))
        self.assertIsNone(night.spoken_mode('TV says hey webbie wake up', sleeping=True))
        self.assertIsNone(night.spoken_mode('Hey Webbie, wake up and open Kali', sleeping=True))

    def test_shared_state_is_private_atomic_and_until_owner_wakes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'config/webbie-face.json'
            night.set_mode('sleep', path)
            self.assertTrue(night.asleep(path))
            self.assertTrue(overlay.asleep(path))
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(json.loads(path.read_text()),
                             {'asleep': True, 'until': None})
            night.set_mode('wake', path)
            self.assertFalse(night.asleep(path))
            self.assertFalse(overlay.asleep(path))

    def test_sleep_keeps_click_through_portrait_visible(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'sleep.json'
            night.set_mode('sleep', path)
            widget = overlay.WebbieOverlay(ROOT, path, lambda: False)
            widget.timer.stop()
            widget.mouth_timer.stop()
            with patch.object(overlay, 'click_through_x11', return_value=True):
                widget.refresh()
            self.assertTrue(widget.isVisible())
            self.assertTrue(widget.sleeping)
            widget.close()

    def test_fullscreen_always_hides_even_sleeping_portrait(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'sleep.json'
            night.set_mode('sleep', path)
            widget = overlay.WebbieOverlay(ROOT, path, lambda: True)
            widget.timer.stop()
            widget.mouth_timer.stop()
            with patch.object(overlay, 'click_through_x11', return_value=True):
                widget.refresh()
            self.assertTrue(widget.sleeping)
            self.assertFalse(widget.isVisible())
            widget.close()


if __name__ == '__main__':
    unittest.main()
