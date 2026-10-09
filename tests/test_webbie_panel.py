"""UI responsiveness, speech-only lip movement and existing socket compatibility."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import socket
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'the-web/shell'))
from PyQt5.QtCore import QTimer, QEventLoop
from PyQt5.QtWidgets import QApplication
from webbie_panel import WebbiePanel, observed_state, request_reply
from webbie_overlay import WebbieOverlay
from desktop import close_window

APP = QApplication.instance() or QApplication([])


class PortraitTests(unittest.TestCase):
    def test_marker_gates_lips_and_stops_without_speech(self):
        with tempfile.TemporaryDirectory() as folder:
            panel = WebbiePanel(ROOT); panel.runtime = Path(folder); panel.timer.stop()
            self.assertFalse(panel.face.closed.isNull()); self.assertFalse(panel.face.opened.isNull())
            panel.pending = True; panel.refresh_state()
            self.assertEqual(panel.face.mouth_opacity, 0)
            marker = panel.runtime / 'webbie-speaking'; marker.write_text('speaking')
            panel.refresh_state(); panel.refresh_state()
            self.assertGreater(panel.face.mouth_opacity, 0)
            frame = panel.face.grab().toImage()
            self.assertFalse(frame.isNull())
            marker.unlink(); panel.refresh_state()
            self.assertEqual(panel.face.mouth_opacity, 0)
            self.assertEqual(observed_state(panel.runtime)[0], 'offline')
            panel.close()

    def test_sleeping_avatar_stays_visible_and_obviously_asleep(self):
        # Real face image remains visible and click-through; close-eye
        # treatment and the SLEEPING label render in sleeping mode.
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict(os.environ, {'XDG_CONFIG_HOME': folder}), patch('webbie_overlay.fullscreen_active', return_value=False):
                avatar = WebbieOverlay(ROOT)
                APP.processEvents()
                avatar.sleep(True)
                APP.processEvents()
                self.assertTrue(avatar.isVisible(), 'sleep should not hide Webbie')
                self.assertTrue(avatar.face_sleeping)
                self.assertTrue(avatar.portrait.sleeping)
                self.assertEqual(avatar.portrait.mouth_opacity, 0)
                self.assertNotEqual(avatar.portrait.grab().toImage().pixelColor(80, 80), avatar.portrait.closed.toImage().pixelColor(80, 80))
                avatar.stop()
                reopened = WebbieOverlay(ROOT)
                self.assertTrue(reopened.face_sleeping, 'sleep persists through desktop restart')
                self.assertTrue(reopened.isVisible())
                reopened.sleep(False)
                self.assertFalse(reopened.portrait.sleeping)
                reopened.stop()

    def test_fullscreen_hides_asleep_avatar_only_during_playback(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict(os.environ, {'XDG_CONFIG_HOME': folder}), patch('webbie_overlay.fullscreen_active', return_value=False):
                avatar = WebbieOverlay(ROOT)
                avatar.sleep(True)
                self.assertTrue(avatar.isVisible())
                with patch('webbie_overlay.fullscreen_active', return_value=True):
                    avatar.refresh()
                    self.assertFalse(avatar.isVisible())
                avatar.refresh()
                self.assertTrue(avatar.isVisible())
                avatar.stop()

    def test_shared_panel_follows_same_sleep_visual_without_blocking_chat(self):
        panel = WebbiePanel(ROOT)
        panel.timer.stop()
        panel.set_face_sleeping(True)
        self.assertTrue(panel.face.sleeping)
        self.assertIn('Portrait sleeping', panel.state_label.text())
        panel.set_face_sleeping(False)
        self.assertFalse(panel.face.sleeping)
        panel.close()

    def test_slow_reply_keeps_event_loop_and_safe_close(self):
        release = threading.Event(); ticks = []
        def slow(*args):
            release.wait(2); return '<b>literal text</b>'
        panel = WebbiePanel(ROOT); panel.entry.setText('<img src="bad">')
        with patch('webbie_panel.request_reply', side_effect=slow):
            panel.send(); self.assertTrue(panel.pending)
            self.assertFalse(panel.close())
            panel.entry.setText('second message'); panel.send()
            loop = QEventLoop()
            QTimer.singleShot(30, lambda: (ticks.append(True), release.set()))
            panel.worker.finished.connect(loop.quit); QTimer.singleShot(3000, loop.quit)
            loop.exec_(); APP.processEvents()
            self.assertTrue(ticks); self.assertFalse(panel.pending)
            self.assertTrue(panel.send_button.isEnabled())
            self.assertIn('<b>literal text</b>', panel.chat.toPlainText())
            self.assertIn('<img src="bad">', panel.chat.toPlainText())
        panel.close()

    def test_failed_request_allows_retry(self):
        panel = WebbiePanel(ROOT); panel.entry.setText('Hello')
        with patch('webbie_panel.request_reply', side_effect=OSError('missing service')):
            panel.send(); panel.worker.wait(3000); APP.processEvents()
            self.assertFalse(panel.pending); self.assertTrue(panel.send_button.isEnabled())
            self.assertIn('missing service', panel.chat.toPlainText())
        panel.close()

    def test_socket_receives_split_unicode_reply(self):
        reply = ('Violet 💜 ' * 10000).encode()
        # This runner forbids AF_UNIX sockets; exercise transport framing with
        # split reads including a split multibyte code point instead.
        with patch('webbie_panel.socket.socket') as factory:
            client = factory.return_value.__enter__.return_value
            client.recv.side_effect = [reply[:17], reply[17:], b'']
            self.assertEqual(request_reply('Hello', Path('/test/webbie.sock')), reply.decode())
            client.connect.assert_called_once_with('/test/webbie.sock')
            client.sendall.assert_called_once_with(b'Hello')

    def test_close_uses_normal_wm_request_only(self):
        with patch('desktop.wm_command') as wm:
            close_window('0x0012abcd'); wm.assert_called_once_with('-i', '-c', '0x0012abcd')
            for value in ('-9', '0x0', 'x;kill', None):
                with self.assertRaises(ValueError): close_window(value)
            self.assertEqual(wm.call_count, 1)


if __name__ == '__main__':
    unittest.main()
