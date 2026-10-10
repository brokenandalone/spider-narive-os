"""Webbie full-screen face: display mode and click-through safety tests."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'the-web/overlay/webbie_face.py'
try:
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QApplication
    CAN_TEST_QT = True
except ImportError:
    CAN_TEST_QT = False


@unittest.skipUnless(CAN_TEST_QT, 'PyQt5 is required for overlay tests')
class FullscreenWebbieTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        spec = importlib.util.spec_from_file_location('webbie_face_fullscreen_test', SOURCE)
        cls.face = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.face)

    def test_display_mode_is_separate_from_sleep(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'webbie-face-display.json'
            self.assertFalse(self.face.full_screen_display(path))
            self.assertTrue(self.face.set_display_mode('fullscreen', path))
            self.assertTrue(self.face.full_screen_display(path))
            self.assertFalse(self.face.set_display_mode('toggle-display', path))
            self.assertFalse(self.face.full_screen_display(path))
            with self.assertRaises(ValueError):
                self.face.set_display_mode('nothing', path)

    def test_full_screen_is_transparent_to_input(self):
        with patch.object(self.face, 'full_screen_display', return_value=True):
            overlay = self.face.WebbieOverlay(full_screen_check=lambda: False)
            self.assertTrue(overlay.testAttribute(Qt.WA_TransparentForMouseEvents))
            self.assertTrue(overlay.windowFlags() & Qt.WindowTransparentForInput)
            self.assertTrue(overlay.full_screen_mode)
            screen = QApplication.primaryScreen().geometry()
            self.assertEqual((overlay.width(), overlay.height()),
                             (screen.width(), screen.height()))
            # No XFixes input-shape check succeeds offscreen: fail closed.
            overlay.refresh()
            self.assertFalse(overlay.isVisible())
            overlay.caption.close()
            overlay.close()


if __name__ == '__main__':
    unittest.main()
