"""Webbie Voice Lab redacted counters and reject/stop policy regressions."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"webbie/agent"))
import voice_metrics as m
import voice_lab
import runtime_readiness

class VoiceMetricsTests(unittest.TestCase):
    def test_no_recordings_names_or_transcripts_in_metrics(self):
        meter=m.VoiceIntakeMeter()
        meter.count("heard_transcript")
        meter.count("rejected_unverified")
        meter.count("emergency_stop")
        data=meter.snapshot()
        self.assertEqual(data["heard_transcript"],1)
        self.assertEqual(data["rejected_unverified"],1)
        text=m.display_meter(data)
        self.assertIn("Commands ignored",text)
        self.assertIn("Emergency STOP requests",text)
        for forbidden in ("Cory","Shayna","audio_digest","transcript:","webbie.wav"):
            self.assertNotIn(forbidden,text)
            self.assertNotIn(forbidden,json.dumps(data))
        meter.clear()
        self.assertEqual(meter.snapshot()["heard_transcript"],0)

    def test_only_allowlisted_counters(self):
        meter=m.VoiceIntakeMeter()
        for value in ("the words he said","open browser","/home/user/file",None):
            with self.subTest(value=value),self.assertRaises(ValueError):
                meter.count(value)
        self.assertIn("No valid",m.display_meter({"rejected_unverified":"100"}))
        self.assertIn("No readable",m.display_meter(None))

    def test_saturates_without_wraparound(self):
        meter=m.VoiceIntakeMeter()
        meter.values["heard_transcript"]=1_000_000
        meter.count("heard_transcript")
        self.assertEqual(meter.snapshot()["heard_transcript"],1_000_000)

    def test_voice_lab_reads_only_private_counters(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d)
            agent=home/"agent.json"
            agent.write_text(json.dumps({"voice_intake":{
                "heard_transcript":7,"rejected_unverified":5,
                "verified_input":2,"emergency_stop":1,
                "queued_command":0,"ignored_sleeping":0},
                "last_heard":"hidden utterance"}))
            os.chmod(agent,0o600)
            report=voice_lab.inspect_voice_lab(
                config_path=home/"nothing",model_path=home/"none",
                voice_path=home,executable="",which=lambda _:None,
                agent_path=agent)
            text=voice_lab.voice_lab_report(report)
            self.assertIn("Commands ignored without speaker proof: 5",text)
            self.assertNotIn("hidden utterance",text)
            os.chmod(agent,0o644)
            report=voice_lab.inspect_voice_lab(
                config_path=home/"nothing",model_path=home/"none",
                voice_path=home,executable="",which=lambda _:None,
                agent_path=agent)
            self.assertIn("No readable",voice_lab.voice_lab_report(report))

if __name__=="__main__":unittest.main()
