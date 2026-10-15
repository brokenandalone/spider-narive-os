"""Offline, non-destructive waveform editor tests: no audio devices or GUI."""
from array import array
from pathlib import Path
import sys
import tempfile
import unittest
import wave

from studio.waveform_edit_engine import import_wav, render_clip, outline, export_clip

def samples(pcm):
    result = array("h")
    result.frombytes(pcm)
    if sys.byteorder != "little":
        result.byteswap()
    return list(result)

class WaveEditorTests(unittest.TestCase):
    def fixture(self, root, channels=2, rate=8000):
        path = Path(root) / "original.wav"
        values = array("h")
        for i in range(400):
            for c in range(channels):
                values.append(12000 if i < 200 else -12000)
        if sys.byteorder != "little":
            values.byteswap()
        with wave.open(str(path), "wb") as f:
            f.setnchannels(channels)
            f.setsampwidth(2)
            f.setframerate(rate)
            f.writeframes(values.tobytes())
        return path

    def test_load_and_gain_trim_fades_reverse(self):
        with tempfile.TemporaryDirectory() as folder:
            source = self.fixture(folder)
            before = source.read_bytes()
            clip = import_wav(source)
            self.assertEqual(clip.channels, 2)
            self.assertEqual(clip.rate, 8000)
            self.assertEqual(clip.total_frames, 400)
            self.assertEqual(len(outline(clip, 20)), 20)
            edited = clip.edited(start=80, end=320, reverse=True,
                                 fade_in_ms=5, fade_out_ms=5, gain_db=-6)
            result = samples(render_clip(edited))
            self.assertEqual(len(result), 240 * 2)
            self.assertEqual(result[0], 0)
            self.assertLess(abs(result[2 * 120]), 12000)
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual(clip.start, 0)  # source edit remains unchanged
            self.assertEqual(edited.duration, .03)

    def test_reject_inplace_and_export_stereo(self):
        with tempfile.TemporaryDirectory() as folder:
            src = self.fixture(folder)
            clip = import_wav(src).edited(start=40, end=200)
            with self.assertRaises(ValueError):
                export_clip(clip, src)
            dst = Path(folder) / "edited.wav"
            export_clip(clip, dst)
            with wave.open(str(dst), "rb") as f:
                self.assertEqual(f.getnchannels(), 2)
                self.assertEqual(f.getnframes(), 160)
                self.assertEqual(f.getframerate(), 8000)

    def test_invalid_clip_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            c = import_wav(self.fixture(folder, channels=1))
            for change in [
                {"start": 500}, {"end": 0}, {"gain_db": 20},
                {"gain_db": -37}, {"reverse": "True"},
                {"fade_in_ms": -1}, {"fade_out_ms": 10001},
            ]:
                with self.subTest(change=change), self.assertRaises(ValueError):
                    c.edited(**change)

    def test_reject_incompatible_wav(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.wav"
            with wave.open(str(path), "wb") as f:
                f.setnchannels(1)
                f.setsampwidth(1)
                f.setframerate(8000)
                f.writeframes(b"\x81" * 100)
            with self.assertRaises(ValueError):
                import_wav(path)

if __name__ == "__main__":
    unittest.main()
