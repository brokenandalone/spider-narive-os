"""Read-only WAV library audit regressions."""
import tempfile
import unittest
import wave
from pathlib import Path
from studio.audio_session_audit import audit_recordings, report_json

class RecordingAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
    def make_wav(self, name, rate=48000, width=2):
        p=self.root/name
        with wave.open(str(p),"wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(width)
            wav.setframerate(rate)
            wav.writeframes(b"\0"*(width*240))
        return p
    def test_ready_and_incompatible_and_invalid(self):
        valid=self.make_wav("valid.wav")
        before=valid.read_bytes()
        self.make_wav("other.wav",rate=22050)
        (self.root/"bad.wav").write_bytes(b"nonsense")
        report=audit_recordings(self.root)
        self.assertEqual(report["counts"],{"ready":1,"incompatible":1,"unreadable":1})
        self.assertTrue(report["read_only"])
        self.assertIn('"ready"',report_json(report))
        self.assertEqual(valid.read_bytes(),before)
    def test_no_follow_symlinks_and_limit(self):
        self.make_wav("one.wav")
        (self.root/"link.wav").symlink_to(self.root/"one.wav")
        report=audit_recordings(self.root,max_files=1)
        self.assertEqual(len(report["files"]),1)
        self.assertTrue(report["truncated"] or report["skipped_symlinks"]==1)
        self.assertRaises(ValueError,audit_recordings,self.root,max_files=0)
        self.assertRaises(ValueError,audit_recordings,self.root/"link.wav")
    def test_header_only_inspection(self):
        path=self.make_wav("track.wav")
        original=path.stat().st_mtime_ns
        result=audit_recordings(self.root)
        self.assertEqual(result["files"][0]["frames"],240)
        self.assertEqual(path.stat().st_mtime_ns,original)

if __name__=="__main__":
    unittest.main()
