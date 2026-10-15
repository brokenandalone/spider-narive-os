"""Native Spider Audio Studio's sample synthesis stays bounded and exports WAV."""
import importlib.util
import io
import math
from pathlib import Path
import wave
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "spider_instrument_engine", ROOT / "studio/instrument_engine.py")
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)


class InstrumentEngineTests(unittest.TestCase):
    def test_pitch_is_musical_and_accurate(self):
        self.assertAlmostEqual(engine.frequency("A", 4), 440.0, places=7)
        self.assertAlmostEqual(engine.frequency("A", 3), 220.0, places=7)
        self.assertAlmostEqual(engine.frequency("C", 4),
                               261.625565, delta=0.01)
        with self.assertRaises(ValueError):
            engine.frequency("H", 3)

    def test_all_three_instruments_generate_distinct_audio(self):
        wavs = []
        for name in engine.INSTRUMENTS:
            content = engine.export_wav(instrument=name, note="E", octave=3)
            self.assertTrue(content.startswith(b"RIFF"))
            with wave.open(io.BytesIO(content), "rb") as player:
                self.assertEqual(player.getnchannels(), 1)
                self.assertEqual(player.getframerate(), 22050)
                self.assertEqual(player.getsampwidth(), 2)
                self.assertGreater(player.getnframes(), 20000)
            wavs.append(content)
        self.assertEqual(len(set(wavs)), 3)

    def test_real_four_voice_drum_pattern_and_empty_track(self):
        normal = engine.export_wav("Drums", bpm=120, bars=2)
        self.assertTrue(normal.startswith(b"RIFF"))
        self.assertLess(len(normal), engine.RATE * 25 * 2 + 48)
        with wave.open(io.BytesIO(normal)) as audio:
            self.assertGreater(audio.getnframes(), 4 * engine.RATE)
        empty = {name: [False] * 16 for name in engine.DRUMS}
        silence = engine.export_wav("Drums", pattern=empty)
        self.assertNotEqual(normal, silence)
        with wave.open(io.BytesIO(silence)) as stream:
            pcm = stream.readframes(stream.getnframes())
        self.assertEqual(set(pcm), {0})

    def test_bounded_render_and_strict_pattern_validation(self):
        with self.assertRaises(ValueError):
            engine.export_wav("Drums", bpm=900)
        with self.assertRaises(ValueError):
            engine.export_wav("Drums", bars=9)
        with self.assertRaises(ValueError):
            engine.export_wav("Drums", pattern={"Kick": []})
        with self.assertRaises(ValueError):
            engine.export_wav("BadInstrument", note="C")
        with self.assertRaises(ValueError):
            engine.export_wav("Bass", note="C", octave=10)
        with self.assertRaises(ValueError):
            engine.note_sound("Guitar", seconds=100)

    def test_repeatability_and_no_file_or_network_io_in_engine(self):
        one = engine.export_wav("Drums", bpm=110, bars=1)
        two = engine.export_wav("Drums", bpm=110, bars=1)
        self.assertEqual(one, two)
        source = (ROOT / "studio/instrument_engine.py").read_text()
        for forbidden in ("subprocess", "socket", "requests", "urlopen",
                          "os.system(", "open(", "unlink("):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
