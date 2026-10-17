"""Speaker trust never derives identity from a transcript, voice alias, or face."""
import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
path=ROOT/"webbie/agent/voice_trust.py"
spec=importlib.util.spec_from_file_location("webbie_voice_trust_test",path)
import sys
module=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=module
spec.loader.exec_module(module)
e=module.SpeakerEvidence

class VoiceTrustTests(unittest.TestCase):
    def test_voice_without_real_evidence_cannot_act(self):
        for forged in (None,True,"Cory",{"name":"cory","verified":True}):
            with self.subTest(forged=forged):
                self.assertFalse(module.voice_permission(
                    voice=True,speaker_verified=True,evidence=forged,now=100))

    def test_both_approved_speakers_with_trusted_provenance(self):
        for name in ("cory","shayna","Cory","SHAYNA"):
            value=e(name,True,"trusted.local_speaker_verifier",90)
            self.assertTrue(module.voice_permission(
                voice=True,speaker_verified=True,evidence=value,now=100))

    def test_wake_phrase_or_familiar_face_never_unlocks(self):
        for source in ("whisper.transcription","camera.face_similarity",
                       "web.page", "local.ollama", "wake.word", "user.claim"):
            value=e("cory",True,source,99)
            self.assertFalse(module.voice_permission(
                voice=True,speaker_verified=True,evidence=value,now=100))

    def test_stale_or_future_evidence_rejected(self):
        for timestamp in (69,101,0,-100,1000):
            value=e("shayna",True,"trusted.local_speaker_verifier",timestamp)
            self.assertFalse(module.voice_permission(
                voice=True,speaker_verified=True,evidence=value,now=100))

    def test_unapproved_name_and_truthy_bool_rejected(self):
        for name in ("alex","",None):
            value=e(name,True,"trusted.local_speaker_verifier",99)
            self.assertFalse(module.voice_permission(
                voice=True,speaker_verified=True,evidence=value,now=100))
        value=e("cory",1,"trusted.local_speaker_verifier",99)
        self.assertFalse(module.voice_permission(
            voice=True,speaker_verified=True,evidence=value,now=100))

    def test_explicit_typed_gui_not_treated_as_speaker_verification(self):
        self.assertTrue(module.voice_permission(voice=False))
        self.assertFalse(module.voice_permission(voice=True))
        self.assertIn("not yet provide",module.trust_status())

    def test_resident_voice_gate_before_state_write(self):
        source=(ROOT/"webbie/agent/webbie.py").read_text()
        begin=source.index("def handle_command(")
        end=source.index("\ndef clean_phrase(",begin)
        segment=source[begin:end]
        self.assertLess(segment.index("if not voice_permission("),
                        segment.index("write_state(\n        last_heard="))
        self.assertLess(segment.index("if is_direct_stop("),
                        segment.index("if not voice_permission("))

if __name__=="__main__":
    unittest.main()
