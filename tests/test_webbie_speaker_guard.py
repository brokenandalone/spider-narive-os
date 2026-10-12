"""CPU-only Webbie speaker-gate tests. No microphone or model required."""
import importlib.util
import pathlib
import tempfile
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("speaker_guard",ROOT/"webbie/voice/speaker_guard.py")
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class SpeakerGateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=pathlib.Path(self.temp.name)/"voiceprints.json"
        vectors={"c1":[1,0,0],"c2":[0.99,0.1,0],"c3":[1,0.1,0],
                 "s1":[0,1,0],"s2":[0.1,1,0],"s3":[0,1,0.1],
                 "other":[0,0,1]}
        self.guard=module.SpeakerGuard({"profiles_file":str(self.path)},extractor=lambda p:vectors[p])
    def test_fail_closed_with_no_profiles(self):
        self.assertIsNone(self.guard.identify("c1"))
    def test_only_cory_and_shayna_allowed(self):
        with self.assertRaises(ValueError):
            self.guard.enroll_from_paths("Other",["c1","c2","c3"])
    def test_authorized_match_and_rejected_stranger(self):
        self.guard.enroll_from_paths("Cory",["c1","c2","c3"])
        self.guard.enroll_from_paths("Shayna",["s1","s2","s3"])
        self.assertEqual(self.guard.identify("c1"),"Cory")
        self.assertEqual(self.guard.identify("s1"),"Shayna")
        self.assertIsNone(self.guard.identify("other"))
        self.assertEqual(self.path.stat().st_mode & 0o777,0o600)
    def test_unverified_mode_must_be_explicit(self):
        guard=module.SpeakerGuard({"require_voiceprint":False})
        self.assertEqual(guard.identify("missing.wav"),"unverified")

if __name__=="__main__":
    unittest.main()
