"""Offscreen tests for explicit spoken visual questions and local socket consent."""
import importlib.util
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'the-web/shell'))
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication
from webbie_vision_bridge import VisionBridge

spec = importlib.util.spec_from_file_location('resident_vision_query',
    ROOT / 'webbie/agent/vision_query.py')
voice = importlib.util.module_from_spec(spec)
spec.loader.exec_module(voice)
APP = QApplication.instance() or QApplication([])


class VoiceVisionBridgeTests(unittest.TestCase):
    def test_only_deliberate_visual_questions_are_routed(self):
        for question in (
            'What do you see?', 'What can you see over there?',
            'Look around', 'Can you see me?', 'Describe the room'
        ):
            self.assertTrue(voice.visual_question(question), question)
        for other in ('open terminal', 'read my email', 'look at my calendar',
                      'what time is it', 'good morning'):
            self.assertFalse(voice.visual_question(other), other)

    def test_without_camera_consent_the_voice_query_cannot_enable_it(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertIn('camera is off', voice.ask_vision(
                'What do you see?', runtime=folder).lower())
            self.assertFalse((Path(folder) / 'webbie-vision.sock').exists())

    def test_consent_server_answers_one_new_look_then_turns_off(self):
        with tempfile.TemporaryDirectory() as folder:
            bridge = VisionBridge(folder)
            self.assertTrue(bridge.activate())
            self.assertEqual(bridge.path.stat().st_mode & 0o777, 0o600)
            requested = []
            def on_look():
                requested.append(True)
                QTimer.singleShot(5, lambda: bridge.reply('I can see a lamp and a notebook.'))
            bridge.lookRequested.connect(on_look)
            result = {}
            def listener():
                result['text'] = voice.ask_vision('what do you see',
                                                   runtime=folder, timeout=4)
            client = threading.Thread(target=listener, daemon=True)
            client.start()
            deadline = time.monotonic() + 5
            while client.is_alive() and time.monotonic() < deadline:
                APP.processEvents()
                time.sleep(.005)
            client.join(.1)
            self.assertFalse(client.is_alive(), 'visual request timed out')
            self.assertEqual(result['text'], 'I can see a lamp and a notebook.')
            self.assertEqual(len(requested), 1)
            bridge.deactivate()
            APP.processEvents()
            self.assertFalse(bridge.path.exists())
            self.assertIn('camera is off', voice.ask_vision(
                'what do you see', runtime=folder).lower())

    def test_switching_off_cancels_pending_look(self):
        with tempfile.TemporaryDirectory() as folder:
            bridge = VisionBridge(folder)
            bridge.activate()
            requested = []
            bridge.lookRequested.connect(lambda: requested.append(True))
            result = {}
            client = threading.Thread(target=lambda: result.update(
                text=voice.ask_vision('look around', runtime=folder, timeout=4)))
            client.start()
            deadline = time.monotonic() + 5
            while not requested and time.monotonic() < deadline:
                APP.processEvents()
                time.sleep(.005)
            self.assertTrue(requested)
            bridge.deactivate()
            until = time.monotonic() + 5
            while client.is_alive() and time.monotonic() < until:
                APP.processEvents()
                time.sleep(.005)
            client.join(.1)
            self.assertFalse(client.is_alive())
            self.assertIn('turned off', result['text'].lower())

    def test_busy_camera_answers_without_hanging_speech(self):
        from unittest.mock import patch
        from webbie_panel import WebbiePanel
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict(os.environ, {'XDG_RUNTIME_DIR': folder}), patch('webbie_panel.camera_devices', return_value=['/dev/video0']):
                panel = WebbiePanel(ROOT)
                panel.timer.stop()
                panel.camera_allowed = True
                panel.vision_bridge = VisionBridge(folder, panel)
                panel.vision_bridge.lookRequested.connect(panel.look_now)
                panel.vision_bridge.activate()
                self.assertTrue(panel.camera_allowed)
                # Do not open physical camera; mimic a worker already running.
                class Busy:
                    def isRunning(self): return True
                    def requestInterruption(self): pass
                panel.camera_worker = Busy()
                result = {}
                client = threading.Thread(target=lambda: result.update(
                    text=voice.ask_vision('what can you see', runtime=folder, timeout=4)))
                client.start()
                deadline = time.monotonic() + 4
                while client.is_alive() and time.monotonic() < deadline:
                    APP.processEvents()
                    time.sleep(.005)
                client.join(.1)
                self.assertFalse(client.is_alive())
                self.assertIn('already looking', result['text'])
                panel.camera_worker = None
                panel.stop_camera()
                panel.close()

    def test_voice_response_handles_unicode_at_byte_limit(self):
        with tempfile.TemporaryDirectory() as folder:
            bridge = VisionBridge(folder)
            bridge.activate()
            bridge.lookRequested.connect(
                lambda: QTimer.singleShot(1, lambda: bridge.reply('💜' * 1200))
            )
            result = {}
            client = threading.Thread(target=lambda: result.update(
                text=voice.ask_vision('look around', runtime=folder, timeout=4)))
            client.start()
            deadline = time.monotonic() + 5
            while client.is_alive() and time.monotonic() < deadline:
                APP.processEvents()
                time.sleep(.005)
            client.join(.1)
            self.assertFalse(client.is_alive())
            self.assertTrue(result['text'].startswith('💜'))
            self.assertNotIn('\ufffd', result['text'])
            bridge.deactivate()

    def test_voice_module_import_is_headless_and_does_not_reconfigure_mic(self):
        code = (ROOT / 'webbie/agent/vision_query.py').read_text()
        self.assertNotIn('PyQt5', code)
        self.assertNotIn('arecord', code)
        self.assertNotIn('whisper_listener', code)
        agent = (ROOT / 'webbie/agent/webbie.py').read_text()
        self.assertIn('if voice and visual_question(command):', agent)
        self.assertIn('reply = ask_vision(command)', agent)
        self.assertTrue((ROOT / 'webbie/voice/whisper_listener.py').is_file())


if __name__ == '__main__':
    unittest.main()
