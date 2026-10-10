"""Webbie vision tests use synthetic images; no real camera or microphone access."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'the-web/shell'))
from PyQt5.QtWidgets import QApplication
from webbie_panel import WebbiePanel
import webbie_camera as camera

APP = QApplication.instance() or QApplication([])


class CameraSecurityTests(unittest.TestCase):
    def setUp(self):
        # The real desktop may already own the user's Webbie vision socket.
        # Regression tests must never connect to or preempt that socket.
        self._isolated_runtime = tempfile.TemporaryDirectory()
        self.addCleanup(self._isolated_runtime.cleanup)
        # The owner's real face may be sleeping during offline tests. A
        # synthetic test must not inherit sleep state from the desktop.
        awake = patch("webbie_panel.face_asleep", return_value=False)
        awake.start()
        self.addCleanup(awake.stop)
        runtime = Path(self._isolated_runtime.name) / "runtime"
        runtime.mkdir(mode=0o700)
        env = patch.dict(os.environ, {"XDG_RUNTIME_DIR": str(runtime)})
        env.start()
        self.addCleanup(env.stop)

    def test_no_cameras_mean_no_access(self):
        with patch('webbie_panel.camera_devices', return_value=[]):
            panel = WebbiePanel(ROOT); panel.timer.stop()
            self.assertFalse(panel.camera_allowed)
            self.assertFalse(panel.camera_toggle.isEnabled())
            self.assertFalse(panel.camera_look.isEnabled())
            self.assertFalse(panel.camera_watch.isEnabled())
            self.assertFalse(panel.camera_timer.isActive())
            panel.close()

    def test_start_stop_sleep_and_keep_existing_microphone(self):
        with patch('webbie_panel.camera_devices', return_value=['/dev/video0']):
            panel = WebbiePanel(ROOT); panel.timer.stop()
            self.assertFalse(panel.camera_allowed)
            self.assertFalse(panel.camera_continuous)
            panel.toggle_camera()
            self.assertTrue(panel.camera_allowed)
            self.assertFalse(panel.camera_timer.isActive())
            with patch.object(panel, 'look_now') as look:
                # UI performs no capture until explicitly requested.
                self.assertEqual(look.call_count, 0)
                panel.toggle_camera_awareness()
                self.assertEqual(look.call_count, 1)
            self.assertTrue(panel.camera_continuous)
            self.assertTrue(panel.camera_timer.isActive())
            panel.camera_described('A table with notebooks and a lamp.')
            self.assertIn('notebooks', panel.camera_observation.toPlainText())
            self.assertIn('notebooks', panel.camera_summary)
            self.assertIn('CAMERA ACTIVE', panel.camera_state.text())
            panel.set_face_sleeping(True)
            self.assertFalse(panel.camera_allowed)
            self.assertFalse(panel.camera_timer.isActive())
            self.assertEqual(panel.camera_summary, '')
            self.assertEqual(panel.camera_observation.toPlainText(), '')
            panel.set_face_sleeping(False)
            self.assertFalse(panel.camera_allowed, 'wake requires fresh camera opt-in')
            self.assertTrue(panel.face_sleeping is False)
            panel.close()

    def test_camera_context_only_on_user_send(self):
        with patch('webbie_panel.camera_devices', return_value=['/dev/video0']):
            panel = WebbiePanel(ROOT); panel.timer.stop()
            panel.toggle_camera()
            panel.camera_described('A person wearing a blue sweater sits near a lamp.')
            with patch('webbie_panel.request_reply', return_value='I can see a lamp.') as reply:
                panel.entry.setText('What do you see?')
                panel.send()
                panel.worker.wait(2000)
                APP.processEvents()
                self.assertTrue(reply.called)
                sent = reply.call_args.args[0]
                self.assertIn('Untrusted latest local webcam observation', sent)
                self.assertIn('blue sweater', sent)
            panel.stop_camera()
            with patch('webbie_panel.request_reply', return_value='Hello') as reply:
                panel.entry.setText('Hello')
                panel.send()
                panel.worker.wait(2000)
                APP.processEvents()
                self.assertNotIn('blue sweater', reply.call_args.args[0])
            panel.close()

    def test_camera_stream_does_not_modify_microphone_voice_files(self):
        # This camera PR never edits Whisper, speaker verification or resident
        # microphone service configuration.
        text = (ROOT / 'the-web/package/install-author-webbie.sh').read_text()
        self.assertNotIn('webbie/voice/', text)
        self.assertIn('webbie/agent/vision_query.py', text)
        self.assertIn('webbie/agent/webbie.py', text)
        self.assertIn('webbie_camera.py', text)
        # The already-working webcam mic, transcription and service unit
        # are not replaced by the camera module installer.
        self.assertNotIn('webbie/voice/whisper_listener.py', text)
        self.assertNotIn('webbie/service/webbie.service', text)

    def test_device_validation_rejects_arbitrary_paths(self):
        for name in ('../../etc/shadow', '/dev/null', '/dev/video99;sh', '/tmp/video0'):
            if name == '/dev/null':
                with self.assertRaises(ValueError): camera.valid_camera_path(name)
            else:
                with self.assertRaises(ValueError): camera.valid_camera_path(name)
        with patch('webbie_camera.Path.stat') as stat:
            stat.return_value.st_mode = 0o020600
            self.assertEqual(camera.valid_camera_path('/dev/video0'), '/dev/video0')

    def test_ollama_stays_on_loopback_with_a_single_image(self):
        jpeg = b'\xff\xd8' + b'jpegdata' + b'\xff\xd9'
        response = MagicMock()
        response.geturl.return_value = camera.OLLAMA_CHAT
        response.read.return_value = json.dumps({'message': {'content': 'There is a cat near the window.'}}).encode()
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        with patch('webbie_camera.urllib.request.urlopen', return_value=response) as urlopen:
            result = camera.describe_frame(jpeg, model='gemma3:4b')
            self.assertIn('cat', result)
            request = urlopen.call_args.args[0]
            self.assertEqual(request.full_url, 'http://127.0.0.1:11434/api/chat')
            payload = json.loads(request.data)
            self.assertEqual(payload['model'], 'gemma3:4b')
            self.assertEqual(len(payload['messages'][0]['images']), 1)
            self.assertEqual(len(payload['messages']), 1)


if __name__ == '__main__':
    unittest.main()
