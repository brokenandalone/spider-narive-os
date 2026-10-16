"""Never regress the native WAV mixer source-pad / FFmpeg filter grammar."""
import tempfile
import unittest
from pathlib import Path
from studio.session_mix import mix_plan,ffmpeg_command

class TrackFilterGrammar(unittest.TestCase):
    def test_dry_guitar_and_affected_multiregion_guitar_are_valid_graphs(self):
        dry={
            "filename":"01-rhythm_guitar.wav","role":"rhythm_guitar",
            "path":"/recordings/rhythm.wav","sample_rate":48000,
            "frames":48000,"duration_seconds":1.0,"sha256":"0"*64}
        lead={**dry,"filename":"02-lead_guitar.wav",
              "role":"lead_guitar","path":"/recordings/lead.wav"}
        session={"verified":True,"tracks":[dry,lead]}
        controls={lead["filename"]:{
            "regions":[{"start_ms":0,"end_ms":500,"at_ms":0,
                        "fade_in_ms":0,"fade_out_ms":0}],
            "effects":{"bass_db":2,"compression":True}}}
        with tempfile.TemporaryDirectory() as folder:
            plan=mix_plan(session,controls)
            args=ffmpeg_command("ffmpeg",plan,Path(folder)/"new.wav")
        filters=args[args.index("-filter_complex")+1]
        self.assertIn("[source0]volume=",filters)
        self.assertIn("[piece1_0]equalizer=f=105:",filters)
        self.assertNotIn("[source0],volume=",filters)
        self.assertNotIn("[piece1_0],equalizer=",filters)
        self.assertEqual(args.count("-i"),2)
        self.assertEqual(filters.count("alimiter=limit=0.95"),1)

if __name__=="__main__":
    unittest.main()
