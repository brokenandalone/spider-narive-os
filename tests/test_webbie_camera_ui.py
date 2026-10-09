"""Camera widget is always opt-in and does not activate hardware at startup."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from PyQt5.QtWidgets import QApplication, QMessageBox

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'the-web/shell'))
from webbie_panel import WebbiePanel

APP = QApplication.instance() or QApplication([])


class CameraUIConsentTests(unittest.TestCase):
    def test_panel_startup_is_camera_off(self):
        with patch('webbie_panel.CameraWorker') as worker:
            panel = WebbiePanel(ROOT)
            panel.timer.stop()
            panel.cloud_timer.stop()
            self.assertIn('CAMERA OFF', panel.camera_status.text())
            self.assertIsNone(panel.camera_worker)
            worker.assert_not_called()
            panel.close()

    def test_missing_model_or_rejected_permission_stays_off(self):
        panel = WebbiePanel(ROOT)
        panel.timer.stop()
        panel.cloud_timer.stop()
        panel.vision_model.setText('')
        with patch('webbie_panel.CameraWorker') as worker:
            panel.look_once()
            worker.assert_not_called()
            panel.vision_model.setText('gemma3:4b')
            with patch('webbie_panel.QMessageBox.question', return_value=QMessageBox.No):
                panel.look_once()
            worker.assert_not_called()
            self.assertEqual(panel.camera_status.text(), 'CAMERA OFF · opt-in only')
        panel.close()


if __name__ == '__main__':
    unittest.main()
