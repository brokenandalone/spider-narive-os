"""Offline Whisper callback tests: audio fingerprint association and erasure."""
from pathlib import Path
import importlib.util
import os
import sys
import tempfile
import unittest
from unittest.mock import patch,Mock

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "webbie_whisper_segment_test",ROOT/"webbie/voice/whisper_listener.py")
m=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=m
spec.loader.exec_module(m)

class WhisperSegmentTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.tmp=Path(temp.name)

    def test_audio_bound_verifier_runs_before_callback_and_file_unlinked(self):
        seen=[]
        audio_seen=[]
        def record(path,seconds=None):
            Path(path).write_bytes(b"RIFF"+b"\x00"*100)
            audio_seen.append(path)
            return True
        def verify(path):
            self.assertTrue(Path(path).exists())
            seen.append("verified")
            return "verified-test-evidence"
        def text(phrase,evidence):
            self.assertEqual(phrase,"Webbie open Studio")
            self.assertEqual(evidence,"verified-test-evidence")
            self.assertEqual(seen,["verified"])
            seen.append("callback")
        with patch.object(m,"ready",return_value=True),patch.object(
                m,"RUNTIME_DIR",self.tmp),patch.object(
                m,"SPEAKING_MARKER",self.tmp/"webbie-speaking"),patch.object(
                m,"record_chunk",side_effect=record),patch.object(
                m,"transcribe",return_value="Webbie open Studio"):
            def should_continue(): return len(seen)<2
            m.listen_forever(text,should_continue,
                             verifier=verify)
        self.assertEqual(seen,["verified","callback"])
        self.assertTrue(audio_seen)
        self.assertFalse(Path(audio_seen[0]).exists())

    def test_missing_verifier_preserves_original_one_arg_callback(self):
        seen=[]
        def record(path,seconds=None):
            Path(path).write_bytes(b"RIFF"+b"\x00"*100)
            return True
        with patch.object(m,"ready",return_value=True),patch.object(
                m,"RUNTIME_DIR",self.tmp),patch.object(
                m,"SPEAKING_MARKER",self.tmp/"webbie-speaking"),patch.object(
                m,"record_chunk",side_effect=record),patch.object(
                m,"transcribe",return_value="hello"):
            m.listen_forever(seen.append,lambda:not seen)
        self.assertEqual(seen,["hello"])

    def test_tts_echo_only_interrupt_path_and_never_verifier(self):
        events=[]
        (self.tmp/"webbie-speaking").touch()
        def record(path,seconds=None):
            Path(path).write_bytes(b"RIFF"+b"\x00"*100)
            self.assertEqual(seconds,2)
            return True
        with patch.object(m,"ready",return_value=True),patch.object(
                m,"RUNTIME_DIR",self.tmp),patch.object(
                m,"SPEAKING_MARKER",self.tmp/"webbie-speaking"),patch.object(
                m,"record_chunk",side_effect=record),patch.object(
                m,"transcribe",return_value="Webbie stop"):
            m.listen_forever(
                on_text=lambda *args:events.append("normal"),
                should_continue=lambda:not events,
                on_interrupt=lambda phrase:events.append(phrase),
                verifier=lambda path:events.append("verified"))
        self.assertEqual(events,["Webbie stop"])

    def test_provider_failure_yields_unverified_not_crash(self):
        events=[]
        def record(path,seconds=None):
            Path(path).write_bytes(b"RIFF"+b"\x00"*100)
            return True
        with patch.object(m,"ready",return_value=True),patch.object(
                m,"RUNTIME_DIR",self.tmp),patch.object(
                m,"SPEAKING_MARKER",self.tmp/"webbie-speaking"),patch.object(
                m,"record_chunk",side_effect=record),patch.object(
                m,"transcribe",return_value="Webbie next tab"):
            m.listen_forever(
                lambda phrase,evidence:events.append((phrase,evidence)),
                lambda:not events,verifier=lambda path:1/0)
        self.assertEqual(events,[("Webbie next tab",None)])

if __name__=="__main__":
    unittest.main()
