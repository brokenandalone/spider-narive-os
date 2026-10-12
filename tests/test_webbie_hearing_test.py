"""No real microphone used: bounded local Webbie hearing test tests."""
from pathlib import Path
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"webbie/voice"))
import hearing_test as m

class HearingTests(unittest.TestCase):
    def setUp(self):
        d=tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.root=Path(d.name)
        os.chmod(self.root,0o700)
        self.model=self.root/"model.bin"
        self.model.write_bytes(b"dummy")
        self.exe=self.root/"whisper-cli"
        self.exe.write_text("#!/bin/sh")
        self.record=self.root/"arecord"
        self.record.write_text("#!/bin/sh")
    def run_test(self,runner=None,approved=True):
        return m.run_hearing_test(
            approved=approved,runtime=self.root,model=self.model,
            whisper_bin=str(self.exe),recorder=str(self.record),
            runner=runner)

    def test_needs_click_permission(self):
        with self.assertRaises(PermissionError):
            self.run_test(approved=False)

    def test_audio_and_transcript_removed_after_success(self):
        calls=[]
        def runner(argv,**kwargs):
            calls.append((argv,kwargs))
            if argv[0]==str(self.record):
                Path(argv[-1]).write_bytes(b"RIFF"+b"\x00"*500)
            else:
                prefix=argv[argv.index("-of")+1]
                Path(prefix+".txt").write_text("Hello Webbie\n")
            return SimpleNamespace(returncode=0)
        msg=self.run_test(runner=runner)
        self.assertIn("Webbie heard",msg)
        self.assertIn("Hello Webbie",msg)
        self.assertIn("not speaker verification",msg)
        self.assertEqual(len(calls),2)
        self.assertEqual(calls[0][1]["timeout"],m.CAPTURE_TIMEOUT)
        self.assertEqual(calls[1][1]["timeout"],m.WHISPER_TIMEOUT)
        self.assertEqual(list(self.root.glob(".webbie-hearing-*")),[])

    def test_busy_recorder_is_informative_and_cleans_up(self):
        def runner(argv,**kwargs):
            return SimpleNamespace(returncode=1)
        msg=self.run_test(runner=runner)
        self.assertIn("did not provide",msg)
        self.assertEqual(list(self.root.glob(".webbie-hearing-*")),[])

    def test_transcription_timeout_erases_wav(self):
        def runner(argv,**kwargs):
            if argv[0]==str(self.record):
                Path(argv[-1]).write_bytes(b"RIFF"+b"\x00"*100)
                return SimpleNamespace(returncode=0)
            raise subprocess.TimeoutExpired(cmd=argv,timeout=1)
        msg=self.run_test(runner=runner)
        self.assertIn("timed out",msg)
        self.assertEqual(list(self.root.glob(".webbie-hearing-*")),[])

    def test_unprivate_runtime_rejected_without_recording(self):
        os.chmod(self.root,0o755)
        msg=self.run_test(runner=lambda *args,**kwargs:self.fail("should not record"))
        self.assertIn("not private",msg)

    def test_missing_model_no_recording(self):
        self.model.unlink()
        msg=self.run_test(runner=lambda *args,**kwargs:self.fail("should not record"))
        self.assertIn("is missing",msg)

    def test_silence_reports_no_clear_words(self):
        def runner(argv,**kwargs):
            if argv[0]==str(self.record):
                Path(argv[-1]).write_bytes(b"RIFF"+b"\x00"*100)
            else:
                Path(argv[argv.index("-of")+1]+".txt").write_text("[silence]")
            return SimpleNamespace(returncode=0)
        self.assertIn("no clear words",self.run_test(runner=runner))

if __name__=="__main__":
    unittest.main()
