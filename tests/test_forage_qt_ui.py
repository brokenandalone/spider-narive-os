"""Headless smoke coverage for Deep Forage's source-only native window."""
import importlib.util
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "forage"))

try:
    from PyQt5.QtWidgets import QApplication
except ImportError:
    QApplication = None


@unittest.skipIf(QApplication is None, "Qt5 unavailable on this host")
class DeepForageQtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_readable_modes_report_history_and_export_controls(self):
        path = ROOT / "forage/deep-forage/deep_forage.py"
        spec = importlib.util.spec_from_file_location("spider_deep_window_test", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        with patch.object(mod, "list_reports", return_value=[]):
            window = mod.DeepForageWindow("Research question")
        try:
            self.assertEqual(window.depth.count(), 3)
            self.assertEqual(window.focus.count(), 4)
            self.assertIn("Academic", [window.focus.itemText(i) for i in range(window.focus.count())])
            self.assertEqual(window.topic.text(), "Research question")
            self.assertIn("QComboBox QAbstractItemView", window.styleSheet())
            self.assertFalse(window.open_report.isEnabled())
            self.assertFalse(window.history_button.isEnabled())
            self.assertFalse(window.stop_button.isEnabled())
            window.export_to("study")
            self.assertIn("No completed", window.status.text())
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
