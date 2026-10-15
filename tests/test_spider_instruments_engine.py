"""No-device tests for Spider Audio Studio's original prototype synthesizer."""
import io
import json
from pathlib import Path
import tempfile
import unittest
import wave
from studio.instruments_engine import Pattern, TRACKS, synthesize, render_loop, write_wav, note_name

class InstrumentEngineTests(unittest.TestCase):
    def test_all_seven_sounds_are_deterministic_and_nonzero(self):
        for track in TRACKS:
            with self.subTest(track=track):
                pitch = None if track in ("kick", "snare", "hat", "clap") else 52
                pcm = synthesize(track, pitch, .07, 8000)
                self.assertEqual(len(pcm), 1120)
                self.assertTrue(any(pcm))
                self.assertEqual(pcm, synthesize(track, pitch, .07, 8000))

    def test_presets_and_roundtrip(self):
        p = Pattern.preset("Rock")
        p.set("guitar", 3, 64)
        p.set("bass", 0, 40)
        p.set("keys", 9, 72)
        saved = json.loads(json.dumps(p.as_dict()))
        self.assertEqual(Pattern.from_dict(saved).as_dict(), saved)
        self.assertEqual(note_name(60), "C4")
        p.clear("guitar", 3)
        self.assertIsNone(p.events["guitar"][3])

    def test_reject_untrusted_or_malformed_patterns(self):
        good = Pattern().as_dict()
        for edit in [
            lambda v: v.update(format="unknown"),
            lambda v: v.update(bpm=True),
            lambda v: v["events"]["bass"].__setitem__(0, "rm -rf"),
            lambda v: v["events"]["snare"].__setitem__(0, 127),
            lambda v: v["events"]["hat"].pop(),
        ]:
            broken = json.loads(json.dumps(good))
            edit(broken)
            with self.assertRaises(ValueError):
                Pattern.from_dict(broken)

    def test_wav_export_is_real_pcm(self):
        p = Pattern.preset("Four on the floor")
        pcm = render_loop(p, rate=8000)
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "demo.wav"
            write_wav(target, pcm, 8000)
            with wave.open(str(target), "rb") as reader:
                self.assertEqual(reader.getnchannels(), 1)
                self.assertEqual(reader.getframerate(), 8000)
                self.assertEqual(reader.getnframes(), 8000 * 60 * 4 // p.bpm)
                self.assertTrue(any(reader.readframes(1000)))

if __name__ == "__main__":
    unittest.main()
