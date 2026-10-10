"""Contract tests for consent-bound local trained RVC inference, no real model."""
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock
import wave

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('rvc_bridge_test', ROOT / 'studio/voice_conversion.py')
voice = importlib.util.module_from_spec(spec); spec.loader.exec_module(voice)


def valid_wav(path):
    with wave.open(str(path), 'wb') as data:
        data.setnchannels(1)
        data.setsampwidth(2)
        data.setframerate(16000)
        data.writeframes(b'\0\0' * 1600)


class OfflineVoiceConversionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.rvc = self.root / 'rvc'
        (self.rvc / 'infer').mkdir(parents=True)
        (self.rvc / '.venv/bin').mkdir(parents=True)
        (self.rvc / 'infer/cli.py').write_text('# test placeholder, never executed')
        self.python = self.rvc / '.venv/bin/python'
        self.python.write_text('# test placeholder, never executed')
        self.model = self.root / 'my-voice.pth'
        self.model.write_bytes(b'test model placeholder, not trusted')
        self.index = self.root / 'voice.index'
        self.index.write_bytes(b'index')
        self.vocal = self.root / 'vocal.wav'
        valid_wav(self.vocal)
        self.output = self.root / 'converted.wav'

    def test_official_cli_arguments_and_quoted_paths(self):
        args = voice.conversion_command(self.rvc, self.python, self.model, self.vocal,
                                        self.output, index=self.index, pitch=0)
        self.assertEqual(args[:2], [str(self.python), str(self.rvc / 'infer/cli.py')])
        self.assertEqual(args[args.index('--model')+1], str(self.model))
        self.assertEqual(args[args.index('--input')+1], str(self.vocal))
        self.assertEqual(args[args.index('--output')+1], str(self.output))
        self.assertIn('rmvpe', args)
        self.assertIn('--index', args)

    def test_refuse_untrained_model_overwrite_or_invalid_pitch(self):
        cases = [{'model': self.root / 'absent.pth'}, {'pitch': 30}]
        for kwargs in cases:
            with self.assertRaises(voice.ConversionError):
                voice.conversion_command(self.rvc, self.python,
                    kwargs.get('model', self.model), self.vocal, self.output,
                    pitch=kwargs.get('pitch', 0))
        self.output.write_bytes(b'original')
        with self.assertRaises(voice.ConversionError):
            voice.conversion_command(self.rvc, self.python, self.model, self.vocal,
                                     self.output)
        self.assertEqual(self.output.read_bytes(), b'original')
        self.output.unlink()
        (self.root / 'linked.wav').symlink_to(self.vocal)
        with self.assertRaises(voice.ConversionError):
            voice.conversion_command(self.rvc, self.python, self.model, self.root / 'linked.wav',
                                     self.output)

    def test_successful_mock_conversion_is_private_and_separate_from_original(self):
        def fake_launch(args, **_):
            path = Path(args[args.index('--output')+1])
            valid_wav(path)
            proc = Mock()
            proc.poll.return_value = 0
            proc.returncode = 0
            return proc
        with patch.object(voice.subprocess, 'Popen', side_effect=fake_launch) as launched:
            output = voice.convert_vocal(self.model, self.vocal, index=self.index,
                rvc_dir=self.rvc, python_bin=self.python,
                output_root=self.root / 'out', timeout=5)
        self.assertTrue(output.is_file())
        self.assertNotEqual(output, self.vocal)
        self.assertEqual(output.stat().st_mode & 0o777, 0o600)
        self.assertTrue(self.vocal.exists())
        self.assertFalse(launched.call_args.kwargs.get('shell', False))

    def test_start_cancel_never_executes_model(self):
        import threading
        cancelled = threading.Event(); cancelled.set()
        with patch.object(voice.subprocess, 'Popen') as launch:
            with self.assertRaises(voice.ConversionError):
                voice.convert_vocal(self.model, self.vocal, rvc_dir=self.rvc,
                    python_bin=self.python, output_root=self.root / 'out',
                    stop=cancelled)
            launch.assert_not_called()


if __name__ == '__main__':
    unittest.main()
