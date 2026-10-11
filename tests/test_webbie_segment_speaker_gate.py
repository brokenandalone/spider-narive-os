"""Offline, no-device tests of Webbie audio-bound voice identity gating."""
import hashlib
from pathlib import Path
import os
import sys
import tempfile
import unittest
from unittest.mock import Mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"webbie/agent"))
import segment_speaker_gate as m
from voice_trust import SpeakerEvidence as Evidence
from speaker_provider_loader import speaker_gate_from_config

class VoiceSegmentTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.audio=self.root/"sample.wav"
        self.audio.write_bytes(b"RIFF" + b"\x00"*60 + b"audio-segment-no-secret")
        self.digest=hashlib.sha256(self.audio.read_bytes()).hexdigest()
    def evidence(self,digest=None,when=99,name="cory",origin="trusted.local_speaker_verifier"):
        return Evidence(name,True,origin,when,self.digest if digest is None else digest)

    def test_valid_local_provider_bound_to_same_wav(self):
        now=lambda:100
        fn=Mock(return_value=self.evidence())
        gate=m.SegmentSpeakerGate(fn,clock=now)
        self.assertTrue(gate.configured)
        proof=gate.verify_file(self.audio)
        self.assertEqual(proof.name,"cory")
        fn.assert_called_once_with(str(self.audio))

    def test_missing_provider_fails_closed(self):
        gate=m.SegmentSpeakerGate(clock=lambda:100)
        self.assertIsNone(gate.verify_file(self.audio))
        self.assertFalse(gate.configured)
        self.assertIn("not connected",gate.status())

    def test_reject_wrong_audio_or_fake_identities(self):
        invalid=[
            Evidence("cory",True,"trusted.local_speaker_verifier",99,"wrong"),
            self.evidence(name="stranger"),
            self.evidence(when=40),
            self.evidence(origin="whisper.transcript"),
            True,"cory",{"name":"cory","verified":True},None
        ]
        for result in invalid:
            with self.subTest(value=result):
                gate=m.SegmentSpeakerGate(lambda path: result,clock=lambda:100)
                self.assertIsNone(gate.verify_file(self.audio))

    def test_symlink_or_large_wav_never_trusted(self):
        link=self.root/"audio-link.wav"
        link.symlink_to(self.audio)
        self.assertIsNone(m.recording_fingerprint(link))
        self.audio.write_bytes(b"a"*(m.MAX_AUDIO_BYTES+1))
        self.assertIsNone(m.recording_fingerprint(self.audio))

    def test_provider_errors_fail_closed(self):
        def fail(path):
            raise RuntimeError("private recording path")
        gate=m.SegmentSpeakerGate(fail,clock=lambda:100)
        self.assertIsNone(gate.verify_file(self.audio))

    def test_opt_in_provider_loader_never_imports_by_default(self):
        mod=Mock()
        gate=speaker_gate_from_config(
            {"speaker_verification":{"enabled":False}},
            voice_root=self.root,importer=mod)
        self.assertFalse(gate.configured)
        mod.assert_not_called()
        (self.root/"speaker_voice_provider.py").write_text("# trusted in isolated tests")
        gate=speaker_gate_from_config(
            {"speaker_verification":{"enabled":True}},
            voice_root=self.root,
            clock=lambda:100,
            importer=lambda name:type("Fake",(),{"verify_audio_segment":lambda path:self.evidence()})())
        self.assertTrue(gate.configured)
        self.assertEqual(gate.verify_file(self.audio).name,"cory")

    def test_verifier_not_enabled_from_truthy_config_string(self):
        (self.root/"speaker_voice_provider.py").write_text("# test")
        fn=Mock()
        gate=speaker_gate_from_config(
            {"speaker_verification":{"enabled":"true"}},
            voice_root=self.root,importer=fn)
        self.assertFalse(gate.configured)
        fn.assert_not_called()

if __name__=="__main__":
    unittest.main()
