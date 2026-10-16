"""No-device tests of Spider's DJ deck crossfade and streaming WAV writer."""
from array import array
from pathlib import Path
import sys
import tempfile
import unittest
import wave
from studio.waveform_edit_engine import import_wav
from studio.dj_deck_engine import render_deck_chunks, write_deck_wav

def make_wav(filename, value, rate=8000, channels=1, count=800):
    samples = array("h", [value] * (count * channels))
    if sys.byteorder != "little":
        samples.byteswap()
    with wave.open(str(filename), "wb") as f:
        f.setnchannels(channels)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes(samples.tobytes())
    return import_wav(filename)

def sample_values(chunks):
    pcm = array("h")
    for block in chunks:
        pcm.frombytes(block)
    if sys.byteorder != "little":
        pcm.byteswap()
    return list(pcm)

class DJDeckTests(unittest.TestCase):
    def test_crossfader_switches_between_decks(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            a = make_wav(path / "a.wav", 14000)
            b = make_wav(path / "b.wav", -14000)
            left = sample_values(render_deck_chunks(a, b, -100))
            right = sample_values(render_deck_chunks(a, b, 100))
            center = sample_values(render_deck_chunks(a, b, 0))
            self.assertEqual(len(left), 1600)
            self.assertGreater(left[10], 0)
            self.assertLess(right[10], 0)
            self.assertEqual(center[10], 0)
            self.assertEqual(sample_values(render_deck_chunks(a, b, -100, gain_a=0)), [0] * 1600)

    def test_stereo_export_and_no_original_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            a = make_wav(base / "a.wav", 12000, channels=2)
            b = make_wav(base / "b.wav", -8000, channels=1)
            original_a = a.original.read_bytes()
            mix = base / "mix.wav"
            write_deck_wav(a, b, mix, cross=-50)
            with wave.open(str(mix), "rb") as f:
                self.assertEqual(f.getnchannels(), 2)
                self.assertEqual(f.getframerate(), 8000)
                self.assertEqual(f.getnframes(), 800)
                self.assertTrue(any(f.readframes(100)))
            self.assertEqual(a.original.read_bytes(), original_a)
            with self.assertRaises(ValueError):
                write_deck_wav(a, b, a.original)

    def test_reject_mismatched_rate_and_invalid_inputs(self):
        with tempfile.TemporaryDirectory() as folder:
            a = make_wav(Path(folder) / "a.wav", 10000)
            b = make_wav(Path(folder) / "b.wav", 10000, rate=11025)
            with self.assertRaises(ValueError):
                b"".join(render_deck_chunks(a, b))
            with self.assertRaises(ValueError):
                b"".join(render_deck_chunks(a, None, cross=101))
            with self.assertRaises(ValueError):
                b"".join(render_deck_chunks(None, None))

if __name__ == "__main__":
    unittest.main()
