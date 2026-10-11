"""Release Desk command, input validation, receipts and immutable export tests."""
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import wave

from studio import release_export as release
from studio.song_mix import MixError


def wav(path, *, rate=8000, width=2, channels=1):
    with wave.open(str(path), 'wb') as stream:
        stream.setnchannels(channels)
        stream.setsampwidth(width)
        stream.setframerate(rate)
        stream.writeframes(bytes(400 * channels * width))


class FakeEncoder:
    def __init__(self, args, **kwargs):
        self.returncode = 0
        target = Path(args[-1])
        if target.suffix == '.mp3':
            target.write_bytes(b'ID3' + bytes(320))
        elif 'studio-' in target.name:
            wav(target, rate=48000, width=3, channels=2)
        else:
            wav(target, rate=44100, width=2, channels=2)

    def poll(self):
        return self.returncode


class ReleaseExportTests(unittest.TestCase):
    def test_profiles_have_distinct_fixed_formats_and_no_overwrites(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            src = root / 'mix.wav'
            wav(src)
            for profile, fname in (
                ('studio_wav', 'studio-48k-24bit.wav'),
                ('cd_wav', 'cd-44k-16bit.wav'),
                ('mp3_320', 'preview-320k.mp3'),
            ):
                cmd = release.encode_command('ffmpeg', src, profile, root / fname)
                self.assertIn('-n', cmd)
                self.assertNotIn('-y', cmd)
                self.assertEqual(cmd[-1], str(root / fname))
                self.assertEqual(cmd.count('-i'), 1)
                self.assertIn('-map_metadata', cmd)
                self.assertNotIn('shell', cmd)
            with self.assertRaises(MixError):
                release.encode_command('ffmpeg', src, 'unknown', root / 'new.wav')
            (root / 'existing.mp3').touch()
            with self.assertRaises(MixError):
                release.encode_command('ffmpeg', src, 'mp3_320', root / 'existing.mp3')

    def test_private_bundle_receipt_all_formats_preserves_original(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            src = root / 'finished.wav'
            wav(src)
            unchanged = src.read_bytes()
            with (patch.object(release.shutil, 'which', return_value='/usr/bin/ffmpeg'),
                  patch.object(release.subprocess, 'Popen', side_effect=FakeEncoder) as process):
                out = release.export_release(src, release.ALL_PROFILES, output_root=root / 'out')
            self.assertEqual(process.call_count, 3)
            self.assertEqual(src.read_bytes(), unchanged)
            self.assertEqual(out.stat().st_mode & 0o777, 0o700)
            receipt = out / 'release.json'
            self.assertEqual(receipt.stat().st_mode & 0o777, 0o600)
            data = json.loads(receipt.read_text())
            self.assertTrue(data['source_preserved'])
            self.assertEqual(data['original_sha256'], hashlib.sha256(unchanged).hexdigest())
            self.assertEqual(set(e['profile'] for e in data['exports']), set(release.ALL_PROFILES))
            for row in data['exports']:
                self.assertEqual((out / row['filename']).stat().st_mode & 0o777, 0o600)
            past = release.list_releases(output_root=root / 'out')
            self.assertEqual(len(past), 1)
            self.assertEqual(len(past[0]['exports']), 3)

    def test_cancelled_and_invalid_input_dont_create_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            src = root / 'finished.wav'
            wav(src)
            halt = threading.Event()
            halt.set()
            with self.assertRaisesRegex(MixError, 'cancelled'):
                release.export_release(src, ('studio_wav',), output_root=root / 'out', stop=halt)
            self.assertFalse((root / 'out').exists())
            fake = root / 'false.wav'
            fake.write_bytes(bytes(500))
            with self.assertRaises(MixError):
                release.validate_source(fake)
            symlink = root / 'linked.wav'
            symlink.symlink_to(src)
            with self.assertRaises(MixError):
                release.validate_source(symlink)
            for names in ((), ('studio_wav', 'studio_wav'), ('unknown',), 'studio_wav'):
                with self.assertRaises(MixError):
                    release.choose_profiles(names)

    def test_failed_encode_discards_partial_outputs_and_never_touches_source(self):
        class EncoderFails:
            def __init__(self, args, **kwargs):
                self.returncode = 1
                Path(args[-1]).write_bytes(bytes(300))
            def poll(self):
                return self.returncode
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'mix.wav'
            wav(source)
            before = source.read_bytes()
            with (patch.object(release.shutil, 'which', return_value='/usr/bin/ffmpeg'),
                  patch.object(release.subprocess, 'Popen', side_effect=EncoderFails)):
                with self.assertRaisesRegex(MixError, 'FFmpeg export failed'):
                    release.export_release(source, ('studio_wav',), output_root=root / 'out')
            self.assertEqual(before, source.read_bytes())
            self.assertEqual(list((root / 'out').iterdir()), [])

    def test_release_history_ignores_symlinked_and_bad_receipts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'mix.wav'
            wav(source)
            with (patch.object(release.shutil, 'which', return_value='/usr/bin/ffmpeg'),
                  patch.object(release.subprocess, 'Popen', side_effect=FakeEncoder)):
                good = release.export_release(source, ('studio_wav',), output_root=root / 'out')
            evil = root / 'out' / 'release-malicious'
            evil.mkdir()
            (evil / 'release.json').symlink_to(good / 'release.json')
            self.assertEqual(len(release.list_releases(output_root=root / 'out')), 1)
            (good / 'release.json').write_text('invalid JSON')
            self.assertEqual(release.list_releases(output_root=root / 'out'), [])


if __name__ == '__main__':
    unittest.main()
