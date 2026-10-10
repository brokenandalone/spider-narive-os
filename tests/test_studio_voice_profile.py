"""Offline My Voice tests: consent, private sample storage, capture and no fake model."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('voice_profile_test', ROOT / 'studio/voice_profile.py')
voice = importlib.util.module_from_spec(spec); spec.loader.exec_module(voice)


class VoiceProfileTests(unittest.TestCase):
    def test_import_opt_in_private_and_no_trained_claim(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'my voice'
            sample = Path(folder) / 'take.wav'
            sample.write_bytes(b'fixture')
            with self.assertRaises(voice.VoiceSampleError):
                voice.import_sample(sample, root)
            self.assertFalse(root.exists())
            result = voice.import_sample(sample, root, consent=True)
            self.assertNotEqual(result, sample)
            self.assertEqual(result.read_bytes(), b'fixture')
            self.assertEqual(root.stat().st_mode & 0o777, 0o700)
            self.assertEqual(result.stat().st_mode & 0o777, 0o600)
            self.assertEqual(voice.samples(root), [result])
            self.assertEqual(voice.training_status(root)['trained'], False)

    def test_refuse_symlinks_invalid_files_and_oversize(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            sample = root / 'take.wav'
            sample.write_bytes(b'ok')
            (root / 'link.wav').symlink_to(sample)
            for path in [root / 'link.wav', root / 'missing.wav']:
                with self.assertRaises(voice.VoiceSampleError):
                    voice.import_sample(path, root / 'dest', consent=True)
            with patch.object(voice, 'MAX_SIZE', 1):
                with self.assertRaises(voice.VoiceSampleError):
                    voice.import_sample(sample, root / 'dest', consent=True)

    def test_capture_explicit_alsa_command_only(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch('studio.voice_profile.shutil.which', return_value='/usr/bin/arecord') if False else patch.object(voice.shutil, 'which', return_value='/usr/bin/arecord'):
                with patch.object(voice.subprocess, 'Popen') as launch:
                    launch.return_value = Mock()
                    proc, file = voice.start_capture(folder, seconds=30)
                    self.assertEqual(proc, launch.return_value)
                    args = launch.call_args.args[0]
                    self.assertEqual(args[:2], ['arecord', '-q'])
                    self.assertIn('44100', args)
                    self.assertEqual(args[-1], str(file))
                    self.assertNotIn('sudo', args)
            with self.assertRaises(voice.VoiceSampleError):
                voice.start_capture(folder, seconds=300)

    def test_finished_and_invalid_recording(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'take.wav'
            path.write_bytes(b'test')
            proc = Mock(); proc.returncode = 0
            self.assertEqual(voice.finish_capture(proc, path), path)
            proc.returncode = 1
            with self.assertRaises(voice.VoiceSampleError):
                voice.finish_capture(proc, path)
            self.assertFalse(path.exists())


if __name__ == '__main__':
    unittest.main()
