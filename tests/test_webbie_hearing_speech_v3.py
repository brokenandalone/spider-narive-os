"""Tests for the staged Webbie hearing activity gate ONLY.

The original v3 branch's TTS/listener integration tests are deliberately held
because this combined release uses a DIFFERENT resident speech engine and
history API. Do not silently overwrite those components to satisfy a test.
"""
import math
from array import array
from pathlib import Path
import sys
import tempfile
import unittest
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "webbie/voice"))
from audio_gate import wav_has_activity, normalize_transcript, TranscriptDeduper


class StagedHearingTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.wav = Path(folder.name) / "input.wav"

    def wav_file(self, samples):
        with wave.open(str(self.wav), "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(16000)
            f.writeframes(array("h", samples).tobytes())
        return self.wav

    def test_silence_rejected(self):
        self.assertFalse(wav_has_activity(self.wav_file([0] * 64000)))

    def test_low_noise_rejected(self):
        self.assertFalse(wav_has_activity(self.wav_file([15, -15] * 32000)))

    def test_humanlike_audio_passes_filter_but_not_auth(self):
        values = [5] * 16000 + [int(6500 * math.sin(i * .11)) for i in range(16000)] + [5] * 32000
        self.assertTrue(wav_has_activity(self.wav_file(values)))

    def test_clipping_rejected(self):
        self.assertFalse(wav_has_activity(self.wav_file([32767] * 64000)))

    def test_corrupt_audio(self):
        self.wav.write_text("not wave")
        self.assertFalse(wav_has_activity(self.wav))

    def test_cleanup_and_transcript_dedupe(self):
        self.assertEqual(normalize_transcript("[silence]"), "")
        self.assertEqual(normalize_transcript("Thanks for watching."), "")
        clock = [10.]
        deduper = TranscriptDeduper(clock=lambda: clock[0])
        self.assertTrue(deduper.accept("Hey Webbie!"))
        self.assertFalse(deduper.accept("hey webbie"))
        clock[0] = 13.
        self.assertTrue(deduper.accept("hey webbie"))

    def test_legacy_speech_stack_not_replaced(self):
        agent = (ROOT / "webbie/agent/webbie.py").read_text()
        listener = (ROOT / "webbie/voice/whisper_listener.py").read_text()
        self.assertNotIn("from speaker_guard import SpeakerGuard", agent)
        self.assertNotIn("from audio_gate import wav_has_activity", listener)
        plan = (ROOT / "system/daily_release_plan_20261011.json").read_text()
        self.assertIn('"voice_pipeline_verified": false', plan)


if __name__ == "__main__":
    unittest.main()
