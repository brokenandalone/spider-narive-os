"""Selected-window screenshot permissions and local-only vision transport."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock
import json
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
try:
    from PyQt5.QtGui import QPixmap
    from PyQt5.QtWidgets import QApplication
    CAN_QT = True
except ImportError:
    CAN_QT = False


@unittest.skipUnless(CAN_QT, 'PyQt5 needed')
class ScreenCaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        spec = importlib.util.spec_from_file_location(
            'screen_capture_test', Path(__file__).resolve().parents[1] /
            'webbie/actions/screen_capture.py')
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_screen_never_captured_without_separate_true_approval(self):
        screen = Mock()
        with self.assertRaises(PermissionError):
            self.module.capture_window('0x01', screen=screen)
        with self.assertRaises(PermissionError):
            self.module.capture_window('0x01', approved=1, screen=screen)
        screen.grabWindow.assert_not_called()

    def test_selected_window_only_and_jpeg_in_memory(self):
        pixmap = QPixmap(64, 64)
        pixmap.fill()
        screen = Mock()
        screen.grabWindow.return_value = pixmap
        data = self.module.capture_window('0x0000002a', approved=True, screen=screen)
        screen.grabWindow.assert_called_once_with(42)
        self.assertTrue(data.startswith(b'\xff\xd8'))
        self.assertTrue(data.endswith(b'\xff\xd9'))
        with self.assertRaises(ValueError):
            self.module.capture_window('0x01;rm', approved=True, screen=screen)

    def test_image_sent_to_local_ollama_only_when_called(self):
        image = b'\xff\xd8' + b'abc' + b'\xff\xd9'
        response = Mock()
        response.geturl.return_value = self.module.OLLAMA_CHAT
        response.read.return_value = json.dumps({
            'message': {'content': 'An Audacity editing window is visible.'}
        }).encode()
        ctx = Mock()
        ctx.__enter__ = Mock(return_value=response)
        ctx.__exit__ = Mock(return_value=False)
        opener = Mock(return_value=ctx)
        result = self.module.describe_window(image, 'What controls can you see?', opener=opener)
        self.assertIn('Audacity', result)
        self.assertEqual(opener.call_args.args[0].full_url, self.module.OLLAMA_CHAT)
        wire = json.loads(opener.call_args.args[0].data.decode())
        self.assertIn('UNTRUSTED', wire['messages'][0]['content'])
        self.assertTrue(wire['messages'][0]['images'])
        with self.assertRaises(ValueError):
            self.module.describe_window(b'not jpeg', 'test', opener=opener)


if __name__ == '__main__':
    unittest.main()
