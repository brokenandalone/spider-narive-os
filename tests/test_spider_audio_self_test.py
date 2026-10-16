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

    def test_channel_graph_joins_output_pads_directly_to_dsp_filters(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from studio.session_mix import mix_plan,ffmpeg_command
        first={
            "filename":"01-rhythm_guitar.wav","role":"rhythm_guitar",
            "path":"/synthetic/rhythm.wav",
            "sample_rate":48000,"frames":48000,
            "duration_seconds":1.0,"sha256":"0"*64,
        }
        second={**first,"filename":"02-lead_guitar.wav",
                "role":"lead_guitar","path":"/synthetic/lead.wav"}
        session={"verified":True,"tracks":[first,second]}
        controls={second["filename"]:{
            "regions":[{"start_ms":0,"end_ms":500,"at_ms":0,
                        "fade_in_ms":0,"fade_out_ms":0}],
            "effects":{"bass_db":2,"compression":True},
        }}
        plan=mix_plan(session,controls)
        with TemporaryDirectory() as folder:
            command=ffmpeg_command("ffmpeg",plan,Path(folder)/"never-exists.wav")
        graph=command[command.index("-filter_complex")+1]
        self.assertIn("[source0]volume=",graph)
        self.assertIn("[piece1_0]equalizer=f=105:",graph)
        self.assertNotIn("[source0],volume=",graph)
        self.assertNotIn("[piece1_0],equalizer=",graph)

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
