"""Offline, no-device tests for individual SoundFont banks and score mix engine."""
from array import array
from fractions import Fraction
from pathlib import Path
import sys
import tempfile
import unittest
import wave

from studio.score_performer import Note, Part, Performance
from studio.studio_score_mix import MixChannel, render_score_mix

def make_bank(path):
    # RIFF SoundFont header is enough for a safety fixture. No bundled sample.
    path.write_bytes(b"RIFF" + b"\x38\x00\x00\x00" + b"sfbk" + b"\0" * 52)
    return path

def make_score():
    return Performance("Spider Sample Band", 120,
                       [Part("Guitar", 25, 0), Part("Bass", 33, 1)],
                       [Note(0, 64, Fraction(0), Fraction(1), 90),
                        Note(1, 40, Fraction(1), Fraction(1), 95)],
                       Fraction(4)).validated()

def read_audio(path):
    pcm = array("h")
    with wave.open(str(path), "rb") as stream:
        params = (stream.getnchannels(), stream.getsampwidth(),
                  stream.getframerate(), stream.getnframes())
        pcm.frombytes(stream.readframes(stream.getnframes()))
    if sys.byteorder != "little":
        pcm.byteswap()
    return params, pcm

class StudioScoreMixTests(unittest.TestCase):
    def test_independent_banks_and_stereo_bounce(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            guitar = make_bank(root / "guitar.sf2")
            bass = make_bank(root / "bass.sf3")
            calls = []
            def fake_renderer(score, bank, output, rate):
                self.assertEqual(len(score.parts), 1)
                self.assertEqual(len(score.notes), 1)
                calls.append((score.parts[0].name, Path(bank).name))
                value = 8000 if "Guitar" in score.parts[0].name else -4000
                samples = array("h", [value] * 2 * 300)
                if sys.byteorder != "little":
                    samples.byteswap()
                with wave.open(str(output), "wb") as f:
                    f.setnchannels(2)
                    f.setsampwidth(2)
                    f.setframerate(rate)
                    f.writeframes(samples.tobytes())
            result = root / "Spider-Studio-Mix.wav"
            output = render_score_mix(
                make_score(), guitar, result, {1: bass},
                [MixChannel(80, -100), MixChannel(80, 100)],
                rate=48000, part_renderer=fake_renderer)
            self.assertEqual(result, output)
            self.assertEqual(calls, [("Guitar", "guitar.sf2"),
                                    ("Bass", "bass.sf3")])
            params, pcm = read_audio(result)
            self.assertEqual(params, (2, 2, 48000, 300))
            self.assertGreater(pcm[0], 0)
            self.assertLess(pcm[1], 0)

    def test_channel_mute_solo_and_source_protection(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            bank = make_bank(root / "gm.sf2")
            track_count = []
            def fake_renderer(score, bank, output, rate):
                track_count.append(score.parts[0].name)
                samples = array("h", [10000] * 400)
                if sys.byteorder != "little":
                    samples.byteswap()
                with wave.open(str(output), "wb") as f:
                    f.setnchannels(2); f.setsampwidth(2); f.setframerate(rate)
                    f.writeframes(samples.tobytes())
            path = root / "mix.wav"
            render_score_mix(make_score(), bank, path, channels=[
                MixChannel(90, 0, True, False),
                MixChannel(90, 0, False, True)],
                part_renderer=fake_renderer)
            _, audio = read_audio(path)
            self.assertTrue(any(audio))
            with self.assertRaises(ValueError):
                render_score_mix(make_score(), bank, bank, part_renderer=fake_renderer)
            with self.assertRaises(ValueError):
                render_score_mix(make_score(), bank, path,
                                 channels=[MixChannel()], part_renderer=fake_renderer)
            with self.assertRaises(ValueError):
                render_score_mix(make_score(), bank, path,
                                 part_banks={-1: bank}, part_renderer=fake_renderer)
            with self.assertRaises(ValueError):
                MixChannel(121).validate()

if __name__ == "__main__":
    unittest.main()
