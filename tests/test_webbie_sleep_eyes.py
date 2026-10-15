"""Verify that Webbie's sleep effect actually covers the original open eyes."""
import importlib.util
import os
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
try:
    from PyQt5.QtCore import QPoint
    from PyQt5.QtGui import QColor, QImage, QPainter
    from PyQt5.QtWidgets import QApplication
    QT = True
except ImportError:
    QT = False


@unittest.skipUnless(QT, 'PyQt5 required for offscreen painting')
class EyeClosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        source = ROOT / 'the-web/overlay/webbie_face.py'
        spec = importlib.util.spec_from_file_location('webbie_sleep_eyes_test', source)
        cls.overlay = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.overlay)

    def test_sleep_masks_original_bright_pupils(self):
        image = QImage(196, 196, QImage.Format_ARGB32)
        image.fill(QColor(255, 255, 255))
        center_left = QPoint(round(196 * .391), round(196 * .432))
        center_right = QPoint(round(196 * .641), round(196 * .432))
        before = [image.pixelColor(p).name() for p in (center_left, center_right)]
        self.assertEqual(before, ['#ffffff', '#ffffff'])
        painter = QPainter(image)
        self.overlay.paint_sleeping_eyelids(painter)
        painter.end()
        after = [image.pixelColor(p).name() for p in (center_left, center_right)]
        self.assertTrue(all(color != '#ffffff' for color in after))
        self.assertEqual(after[0], after[1])

    def test_sleep_mask_does_not_cover_forehead_or_mouth(self):
        image = QImage(196, 196, QImage.Format_ARGB32)
        image.fill(QColor('white'))
        painter = QPainter(image)
        self.overlay.paint_sleeping_eyelids(painter)
        painter.end()
        for point in (QPoint(85, 30), QPoint(100, 130), QPoint(10, 100)):
            self.assertEqual(image.pixelColor(point).name(), '#ffffff')


if __name__ == '__main__':
    unittest.main()
