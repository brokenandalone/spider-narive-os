"""Familiar-face profiles are voluntary and never required for Webbie operation."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import importlib.util
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'the-web/shell'))
from PyQt5.QtWidgets import QApplication
from webbie_faces import FaceProfiles, PROFILES, find_enrolled_faces
from webbie_face_profiles_ui import FaceProfileControls

APP = QApplication.instance() or QApplication([])


class OptInProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'private' / 'faces.json'
        self.profiles = FaceProfiles(self.path)
        self.a = [0.] * 128
        self.b = [0.75] * 128

    def tearDown(self):
        self.temp.cleanup()

    def test_both_profiles_empty_and_not_required(self):
        self.assertEqual(PROFILES, ('Cory', 'Shayna'))
        self.assertFalse(self.profiles.any_enrolled())
        self.assertEqual(self.profiles.status(), {'Cory': 0, 'Shayna': 0})
        # No local recognition model is imported until a consenting user
        # actually requests enrollment or vision-based matching.
        with patch('webbie_faces._face_backend', side_effect=AssertionError('unexpected')):
            self.assertEqual(find_enrolled_faces(b'unused', self.profiles), [])

    def test_cory_and_shayna_enroll_independently_and_can_delete(self):
        self.profiles.enroll_descriptor('Cory', self.a)
        self.assertEqual(self.profiles.status(), {'Cory': 1, 'Shayna': 0})
        self.assertEqual(self.profiles.match_descriptor(self.a), 'Cory')
        self.profiles.enroll_descriptor('Shayna', self.b)
        self.assertEqual(self.profiles.match_descriptor(self.b), 'Shayna')
        self.assertEqual(self.profiles.match_descriptor([0.3] * 128), None)
        recovered = FaceProfiles(self.path)
        self.assertEqual(recovered.status(), {'Cory': 1, 'Shayna': 1})
        self.assertTrue(stat.S_IMODE(self.path.stat().st_mode) == 0o600)
        recovered.forget('Cory')
        self.assertEqual(recovered.status(), {'Cory': 0, 'Shayna': 1})
        self.assertEqual(recovered.match_descriptor(self.a), None)
        recovered.forget('Shayna')
        self.assertFalse(recovered.any_enrolled())

    def test_rejects_unrecognized_identity_and_invalid_descriptor(self):
        with self.assertRaises(ValueError):
            self.profiles.enroll_descriptor('Guest', self.a)
        with self.assertRaises(ValueError):
            self.profiles.enroll_descriptor('Cory', [0.] * 127)
        with self.assertRaises(ValueError):
            self.profiles.enroll_descriptor('Shayna', [float('nan')] * 128)

    def test_face_controls_dont_open_camera_automatically(self):
        with patch('webbie_face_profiles_ui.FaceProfiles', return_value=self.profiles):
            controls = FaceProfileControls(lambda: '/dev/video0', lambda: False)
            self.assertEqual(controls.profiles.status(), {'Cory': 0, 'Shayna': 0})
            self.assertFalse(controls.active())
            controls.start_enrollment()
            self.assertFalse(controls.active())
            self.assertIn('Turn the webcam on', controls.status.text())
            controls.close()


if __name__ == '__main__':
    unittest.main()
