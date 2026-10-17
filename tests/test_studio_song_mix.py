"""Safe vocal and backing assembly tests. No actual mixer service required."""
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import wave

from studio import song_mix as mix


def wav(path, rate=8000):
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(rate)
        stream.writeframes(b"\0\0" * 800)


class FakeProcess:
    def __init__(self, command, **kwargs):
        self.command = command
        self.returncode = 0
        wav(Path(command[-1]), 48000)
    def poll(self):
        return self.returncode


class MixerTests(unittest.TestCase):
    def test_command_has_no_shell_or_overwrite_and_validates_gain(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            bed, voice = root / "backing.wav", root / "converted.wav"
            wav(bed); wav(voice)
            cmd = mix.mix_command("/usr/bin/ffmpeg", bed, voice, root / "new.wav", .7, .8)
            self.assertIn("-n", cmd)
            self.assertNotIn("-y", cmd)
            self.assertIn("amix=inputs=2", cmd[cmd.index("-filter_complex") + 1])
            self.assertIn("volume=0.700", cmd[cmd.index("-filter_complex") + 1])
            self.assertEqual(cmd[-1], str(root / "new.wav"))
            for gain in (-1, 2.1, True, float("nan")):
                with self.assertRaises(mix.MixError):
                    mix.mix_command("ffmpeg", bed, voice, root / "new.wav", gain)
            with self.assertRaises(mix.MixError):
                mix.mix_command("ffmpeg", bed, bed, root / "new.wav")
            (root / "exists.wav").touch()
            with self.assertRaises(mix.MixError):
                mix.mix_command("ffmpeg", bed, voice, root / "exists.wav")

    def test_mix_creates_private_wav_and_preserves_two_inputs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            bed, vocal = root / "instrumental.wav", root / "voice.wav"
            wav(bed); wav(vocal)
            before = {p: p.read_bytes() for p in (bed, vocal)}
            with patch.object(mix.shutil, "which", return_value="/usr/bin/ffmpeg"), \
                 patch.object(mix.subprocess, "Popen", side_effect=FakeProcess) as launch:
                dest = mix.mix_vocals(bed, vocal, output_root=root / "results", vocal_gain=.8)
            self.assertEqual(dest.name, "final-mix.wav")
            self.assertEqual(dest.stat().st_mode & 0o777, 0o600)
            self.assertEqual(dest.parent.stat().st_mode & 0o777, 0o700)
            self.assertEqual((dest.parent / "mix.json").stat().st_mode & 0o777, 0o600)
            self.assertEqual((dest.parent / "mix.log").stat().st_mode & 0o777, 0o600)
            self.assertEqual({p: p.read_bytes() for p in (bed, vocal)}, before)
            self.assertEqual(launch.call_count, 1)
            self.assertNotIn("shell", launch.call_args.kwargs)

    def test_abort_before_launch_and_refuse_symlink_inputs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            bed, voice = root / "backing.wav", root / "vocal.wav"
            wav(bed); wav(voice)
            stop = threading.Event(); stop.set()
            with patch.object(mix.shutil, "which", return_value="/usr/bin/ffmpeg"):
                with self.assertRaises(mix.MixError):
                    mix.mix_vocals(bed, voice, output_root=root / "out", stop=stop)
                self.assertFalse((root / "out").exists())
                (root / "linked.wav").symlink_to(voice)
                with self.assertRaises(mix.MixError):
                    mix.mix_command("ffmpeg", bed, root / "linked.wav", root / "new.wav")

    def test_no_ffmpeg_fails_honestly(self):
        with patch.object(mix.shutil, "which", return_value=None):
            with self.assertRaisesRegex(mix.MixError, "FFmpeg"):
                mix.mix_vocals("/missing.wav", "/missing-vocal.wav")


if __name__ == "__main__":
    unittest.main()
