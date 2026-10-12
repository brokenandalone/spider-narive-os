"""Read-only UI listening signal and temporary audio marker tests."""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"the-web/shell"))
try:
    from webbie_panel import observed_state
    from PyQt5.QtWidgets import QApplication
    QT=True
except ImportError:
    QT=False

@unittest.skipUnless(QT,"Qt needed for Webbie portrait state tests")
class ListeningIndicatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])

    def test_recent_capture_marker_reports_listening(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            listening=root/"webbie-listening"
            listening.touch()
            state,label=observed_state(root)
            self.assertEqual(state,"listening")
            self.assertIn("configured microphone",label)
            self.assertNotIn("verified",label.lower())

    def test_stale_marker_does_not_claim_hearing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            listening=root/"webbie-listening"
            listening.touch()
            then=time.time()-40
            os.utime(listening,(then,then))
            state,_=observed_state(root)
            self.assertEqual(state,"offline")

    def test_symlink_marker_does_not_claim_hearing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            elsewhere=root/"elsewhere"
            elsewhere.touch()
            (root/"webbie-listening").symlink_to(elsewhere)
            state,_=observed_state(root)
            self.assertEqual(state,"offline")

    def test_speaking_marker_has_precedence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"webbie-speaking").touch()
            (root/"webbie-listening").touch()
            state,_=observed_state(root)
            self.assertEqual(state,"speaking")

if __name__=="__main__":
    unittest.main()
