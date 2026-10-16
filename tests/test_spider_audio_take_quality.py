"""Offline read-only QC smoke test for actual Spider take WAVs."""
import hashlib
import tempfile
import unittest
import wave
from pathlib import Path

from studio.audio_capture_panel import _inspect_finished_take

class StudioTakeQualityTests(unittest.TestCase):
    def test_sampled_peak_and_clipping_warning_do_not_change_owner_wav(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            path=root/"recorded-input.wav"
            with wave.open(str(path),"wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(3)
                handle.setframerate(48000)
                handle.writeframes((32767*256).to_bytes(3,"little",signed=True)*320)
            original=path.read_bytes()
            result=_inspect_finished_take({"path":str(path),"role":"lead_vocal"})
            self.assertEqual(hashlib.sha256(path.read_bytes()).digest(),
                             hashlib.sha256(original).digest())
            self.assertEqual(result["sampled_qc"]["sample_rate"],48000)
            self.assertEqual(result["sampled_qc"]["channels"],1)
            self.assertGreater(result["sampled_qc"]["near_clip_samples"],0)
            self.assertTrue(result["sampled_qc"]["warnings"])

    def test_quality_analysis_failure_preserves_recorded_file(self):
        result=_inspect_finished_take({"path":"/not-a-real-studio-take.wav"})
        self.assertIn("quality_note",result)
        self.assertNotIn("sampled_qc",result)

if __name__=="__main__":
    unittest.main()
