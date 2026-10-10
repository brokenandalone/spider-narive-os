"""Offline safe-stem extraction tests; simulated PyMSS CLI only."""
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import wave
from studio import stem_separation as stems


def wav(path):
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(8000)
        f.writeframes(b"\x00\x00" * 500)


class FakeProcess:
    def __init__(self, argv, **kwargs):
        self.returncode = 0
        output = Path(argv[argv.index("--output") + 1])
        wav(output / "lead-vocal.wav")
        wav(output / "instrumental.wav")
    def poll(self):
        return self.returncode


class StemTests(unittest.TestCase):
    def test_exact_cli_and_reject_invalid_device(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "tools/pymss").mkdir(parents=True)
            (root / "tools/pymss/cli.py").touch()
            python = root / "python"; python.touch()
            song = root / "song.wav"; wav(song)
            output = root / "out"; output.mkdir()
            argv = stems.command(root, python, song, output)
            self.assertIn("tools.pymss.cli", argv)
            self.assertIn("model_mel_band_roformer_karaoke_aufr33_viperx_sdr_10.1956.ckpt", argv)
            self.assertEqual(argv[-1], "wav")
            with self.assertRaises(stems.SeparationError):
                stems.command(root, python, song, output, device="shell;rm -rf")

    def test_python_venv_symlink_is_not_mistaken_for_unsafe_audio_input(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'tools/pymss').mkdir(parents=True)
            (root / 'tools/pymss/cli.py').touch()
            executable = root / 'python-base'
            executable.touch()
            interpreter = root / 'python-venv'
            interpreter.symlink_to(executable)
            input_file = root / 'song.wav'
            wav(input_file)
            output = root / 'outputs'
            output.mkdir()
            args = stems.command(root, interpreter, input_file, output)
            self.assertEqual(args[0], str(interpreter))
            interpreter.unlink()
            with self.assertRaises(stems.SeparationError):
                stems.command(root, interpreter, input_file, output)

    def test_separation_returns_independent_audio_and_preserves_original(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            engine = root / "engine"
            (engine / "tools/pymss").mkdir(parents=True)
            (engine / "tools/pymss/cli.py").touch()
            (engine / ".venv/bin").mkdir(parents=True)
            (engine / ".venv/bin/python").touch()
            source = root / "song.wav"; wav(source)
            original = source.read_bytes()
            with patch.object(stems.subprocess, "Popen", side_effect=FakeProcess):
                output, candidates = stems.separate(source, rvc_root=engine, output_root=root / "stems")
            self.assertEqual(len(candidates), 2)
            self.assertEqual(source.read_bytes(), original)
            self.assertTrue(all(p.exists() for p in candidates))
            self.assertEqual(output.stat().st_mode & 0o777, 0o700)

    def test_aborts_before_start_and_rejects_symlinks(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); source = root / "song.wav"; wav(source)
            abort = threading.Event(); abort.set()
            with self.assertRaises(stems.SeparationError):
                stems.separate(source, output_root=root / "out", stop=abort)
            self.assertFalse((root / "out").exists())


if __name__ == "__main__":
    unittest.main()
