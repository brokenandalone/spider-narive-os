"""Overlay and optional OneDrive behavior in a headless source test.

No real Microsoft login, audio device, desktop clicks, or cloud upload is used.
"""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timezone
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
app = QApplication.instance() or QApplication([])


def load(name, source):
    spec = importlib.util.spec_from_file_location(name, ROOT / source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


overlay = load('spider_overlay_tested', 'the-web/overlay/webbie_face.py')
cloud = load('spider_onedrive_tested', 'system/onedrive.py')


class OverlayTests(unittest.TestCase):
    def test_night_sleep_expires_in_morning_without_mutating_agent(self):
        with tempfile.TemporaryDirectory() as temporary:
            sleep_file = Path(temporary) / 'sleep.json'
            now = datetime(2026, 10, 9, 22, 30, tzinfo=timezone.utc)
            data = overlay.set_sleep('sleep-tonight', sleep_file, now)
            self.assertTrue(overlay.asleep(sleep_file, now=int(now.timestamp())))
            self.assertFalse(overlay.asleep(sleep_file, now=data['until'] + 1))
            overlay.set_sleep('sleep', sleep_file)
            self.assertTrue(overlay.asleep(sleep_file, now=10**12))
            overlay.set_sleep('wake', sleep_file)
            self.assertFalse(overlay.asleep(sleep_file))
            self.assertEqual(sleep_file.stat().st_mode & 0o777, 0o600)

    def test_fullscreen_detector_and_input_flags(self):
        self.assertEqual(overlay.active_window_id(
            '_NET_ACTIVE_WINDOW(WINDOW): window id # 0x023abcd0'), '0x023abcd0')
        self.assertIsNone(overlay.active_window_id(
            '_NET_ACTIVE_WINDOW(WINDOW): window id # 0x00000000'))
        self.assertTrue(overlay.fullscreen_from_properties(
            '_NET_WM_STATE(ATOM) = _NET_WM_STATE_FULLSCREEN, _NET_WM_STATE_FOCUSED'))
        self.assertFalse(overlay.fullscreen_from_properties(
            '_NET_WM_STATE(ATOM) = _NET_WM_STATE_MAXIMIZED_VERT'))
        face = overlay.WebbieOverlay(ROOT, Path('/nonexistent/sleep.json'), lambda: True)
        self.assertTrue(bool(face.windowFlags() & Qt.WindowTransparentForInput))
        self.assertTrue(face.testAttribute(Qt.WA_TranslucentBackground))
        face.refresh()
        self.assertFalse(face.isVisible())
        face.timer.stop()
        face.close()

    def test_overlay_fails_closed_when_input_pass_through_is_unavailable(self):
        with tempfile.TemporaryDirectory() as temporary:
            face = overlay.WebbieOverlay(ROOT, Path(temporary) / 'missing', lambda: False)
            face.timer.stop()
            with patch.object(overlay, 'click_through_x11', return_value=False):
                face.refresh()
            self.assertFalse(face.isVisible())
            self.assertFalse(face.allowed)
            face.close()


class CloudTests(unittest.TestCase):
    def make_configs(self, root):
        home = root / 'local'
        remote = root / 'rclone.conf'
        folder = root / 'workspace'
        remote.write_text('[webbie_onedrive]\ntype = onedrive\ntoken = PRIVATE_SECRET_TOKEN\n')
        return home / 'onedrive.json', remote, folder

    def test_connection_only_after_opt_in_and_no_token_in_status(self):
        with tempfile.TemporaryDirectory() as temporary:
            config, remote, folder = self.make_configs(Path(temporary))
            with patch.object(cloud.shutil, 'which', return_value='/usr/bin/rclone'):
                before = cloud.status(config, remote, folder)
                self.assertFalse(before['connected'])
                cloud.enable(config, remote, folder)
                after = cloud.status(config, remote, folder)
                self.assertTrue(after['connected'])
                self.assertTrue(folder.is_dir())
                self.assertNotIn('PRIVATE_SECRET_TOKEN', json.dumps(after))
                self.assertEqual(config.stat().st_mode & 0o777, 0o600)
                cloud.disable(config)
                self.assertFalse(cloud.status(config, remote, folder)['connected'])

    def test_background_sync_only_explicit_workspace_and_no_deletion(self):
        with tempfile.TemporaryDirectory() as temporary:
            config, remote, folder = self.make_configs(Path(temporary))
            cloud.enable(config, remote, folder)
            (folder / 'a-note.txt').write_text('User explicitly put this note here.')
            calls = []
            class Success:
                returncode = 0
            def fake_runner(args, **kw):
                calls.append((args, kw))
                return Success()
            with patch.object(cloud.shutil, 'which', return_value='/usr/bin/rclone'):
                result = cloud.sync_folder(config, remote, folder, fake_runner)
            self.assertEqual(result, 'copied')
            args, keywords = calls[0]
            self.assertEqual(args[args.index('copy') + 1], str(folder))
            self.assertIn('webbie_onedrive:Spider OS/Webbie', args)
            self.assertIn('--immutable', args)
            self.assertNotIn('sync', args)
            self.assertNotIn('--delete', args)
            self.assertEqual(keywords['timeout'], 145)

    def test_symlinked_workspace_is_rejected_before_cloud_transfer(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config, remote, folder = self.make_configs(root)
            private = root / 'private'
            private.mkdir()
            (private / 'private-note.txt').write_text('KEEP PRIVATE')
            folder.symlink_to(private, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'symbolic-link'):
                cloud.enable(config, remote, folder)
            folder.unlink()
            cloud.enable(config, remote, folder)
            folder.rmdir()
            folder.symlink_to(private, target_is_directory=True)
            with patch.object(cloud.shutil, 'which', return_value='/usr/bin/rclone'):
                with patch.object(cloud.subprocess, 'run') as runner:
                    self.assertEqual(cloud.sync_folder(config, remote, folder), 'unsafe workspace')
                    runner.assert_not_called()

    def test_no_connection_no_cloud_call(self):
        with tempfile.TemporaryDirectory() as temporary:
            config, remote, folder = self.make_configs(Path(temporary))
            with patch.object(cloud.shutil, 'which', return_value='/usr/bin/rclone'):
                with patch.object(cloud.subprocess, 'run') as run:
                    self.assertEqual(cloud.sync_folder(config, remote, folder), 'offline')
                    run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
