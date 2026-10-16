"""Beta music-engine preflight tests that use real offline PCM rendering."""
import json
import shutil
import unittest
from unittest.mock import patch

from studio.package.audio_self_test import SelfTestError,run_self_test,main


class BetaAudioEngineSmoke(unittest.TestCase):
    def test_missing_ffmpeg_is_explained_without_opening_input_devices(self):
        with patch("studio.package.audio_self_test.shutil.which",return_value=None):
            with self.assertRaisesRegex(SelfTestError,"FFmpeg is missing"):
                run_self_test()

    @unittest.skipUnless(shutil.which("ffmpeg"),"FFmpeg not installed in runner")
    def test_actual_temporary_multitrack_sound_engine_passes(self):
        report=run_self_test()
        self.assertEqual(report["result"],"PASS")
        self.assertEqual(report["tracks_verified"],3)
        self.assertEqual(report["render_output_hz"],48000)
        self.assertEqual(report["render_output_bits"],24)
        self.assertEqual(report["multiregion_arrangement"],"PASS")
        self.assertEqual(report["original_wav_hashes"],"UNCHANGED")
        self.assertIn("no speakers",report["scope"])

if __name__=="__main__":
    unittest.main()
