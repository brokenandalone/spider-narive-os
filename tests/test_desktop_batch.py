"""Batch receipt integrity and selected-player Linux media controls."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'the-web/shell'))
import build_info
import media_transport as media
from system_status import health_summary


class BuildTests(unittest.TestCase):
    def make_sources(self, directory):
        root = Path(directory)
        for name in build_info.TRACKED:
            target = root / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(b'payload')
        return root

    def test_receipt_detects_later_change_without_reading_private_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = self.make_sources(folder)
            receipt = build_info.write_receipt(root, root, '/backups/test')
            self.assertEqual(build_info.inspect_receipt(root)['integrity'], 'Managed files match receipt')
            (root / build_info.TRACKED[0]).write_bytes(b'changed')
            report = build_info.inspect_receipt(root)
            self.assertEqual(report['mismatches'], [build_info.TRACKED[0]])
            receipt['sha256']['../../private.txt'] = '0' * 64
            (root / 'the-web/install-receipt.json').write_text(json.dumps(receipt))
            self.assertEqual(build_info.inspect_receipt(root)['integrity'], 'Could not validate receipt')

    def test_install_mismatch_never_writes_success_receipt(self):
        with tempfile.TemporaryDirectory() as folder:
            root = self.make_sources(Path(folder) / 'source'); target = self.make_sources(Path(folder) / 'installed')
            (target / build_info.TRACKED[0]).write_text('bad')
            with self.assertRaisesRegex(ValueError, 'differs'): build_info.write_receipt(root, target, '/backups/test')
            self.assertFalse((target / 'the-web/install-receipt.json').exists())

    def test_health_covers_failed_ai_audio_and_full_disk(self):
        report = {'services': [('Webbie','webbie.service','failed','',''), ('PipeWire','pipewire.service','inactive','','')],
                  'storage': [('Home','/home/user','100 GiB','1 GiB','99%')], 'build': {'mismatches': ['main.py']}}
        rows = health_summary(report)
        self.assertEqual({row[0] for row in rows}, {'Webbie','PipeWire','Home storage','Desktop build'})


class MediaTests(unittest.TestCase):
    def test_only_mpris_names_are_discovered(self):
        with patch.object(media, 'call', return_value='string "org.freedesktop.DBus"\nstring "org.mpris.MediaPlayer2.vlc"\nstring "org.mpris.MediaPlayer2.vlc"\nstring "org.mpris.MediaPlayer2.bad;cmd"'):
            self.assertEqual(media.discover_players(), ['org.mpris.MediaPlayer2.vlc'])

    def test_explicit_target_and_microsecond_seek(self):
        name = 'org.mpris.MediaPlayer2.vlc'
        with patch.object(media, 'call') as call:
            media.control(name, 'Back10')
            self.assertEqual(call.call_args.args, (name, '/org/mpris/MediaPlayer2', 'org.mpris.MediaPlayer2.Player.Seek', 'int64:-10000000'))
            media.control(name, 'PlayPause')
            self.assertEqual(call.call_args.args[-1], 'org.mpris.MediaPlayer2.Player.PlayPause')
            for target in (None, 'vlc', '--dest=bad'):
                with self.assertRaises(ValueError): media.control(target, 'Stop')
            with self.assertRaises(ValueError): media.control(name, 'Delete')
            self.assertEqual(call.call_count, 2)

    def test_failure_is_bounded(self):
        with patch.object(media.subprocess, 'run', side_effect=media.subprocess.TimeoutExpired('dbus-send', 2)) as run:
            with self.assertRaisesRegex(RuntimeError, 'unavailable'): media.discover_players()
            self.assertEqual(run.call_args.kwargs['timeout'], 2)
            self.assertNotIn('shell', run.call_args.kwargs)

    def test_playback_status(self):
        with patch.object(media, 'call', return_value='variant string "Paused"'):
            self.assertEqual(media.player_state('org.mpris.MediaPlayer2.vlc'), 'Paused')


if __name__ == '__main__': unittest.main()


class AudioAndWindowTests(unittest.TestCase):
    def test_volume_limit_and_mute_are_allowlisted(self):
        import audio_controls
        with patch.object(audio_controls, 'audio_command', return_value='') as command:
            audio_controls.adjust_audio('Up')
            self.assertEqual(command.call_args.args[0], ['set-volume', '--limit', '1.0', '@DEFAULT_AUDIO_SINK@', '5%+'])
            audio_controls.adjust_audio('Mute')
            self.assertEqual(command.call_args.args[0], ['set-mute', '@DEFAULT_AUDIO_SINK@', 'toggle'])
            with self.assertRaises(ValueError): audio_controls.adjust_audio('Run')
            self.assertEqual(command.call_count, 2)

    def test_volume_parses_muted_output(self):
        import audio_controls
        with patch.object(audio_controls, 'audio_command', return_value='Volume: 0.42 [MUTED]'):
            self.assertEqual(audio_controls.output_level(), 'Output: 42% · Muted')

    def test_minimize_and_maximize_validate_ids_and_use_wm(self):
        import desktop
        with patch.object(desktop.ctypes.util, 'find_library', return_value='libX11.so'), patch.dict(desktop.os.environ, {'DISPLAY': ':1'}), patch.object(desktop.ctypes, 'CDLL') as library:
            x = library.return_value; x.XOpenDisplay.return_value = 123; x.XDefaultScreen.return_value = 0; x.XIconifyWindow.return_value = 1
            self.assertTrue(desktop.minimize_window('0x12ab'))
            x.XIconifyWindow.assert_called_once_with(123, 0x12ab, 0)
            x.XCloseDisplay.assert_called_once_with(123)
        with patch.object(desktop, 'wm_command') as command:
            desktop.maximize_window('0x12ab')
            command.assert_called_once_with('-i', '-r', '0x12ab', '-b', 'toggle,maximized_vert,maximized_horz')
        for method in (desktop.minimize_window, desktop.maximize_window):
            with self.assertRaises(ValueError): method('0x0')
