"""Offline speaker gate safety tests. No audio, embeddings or camera data needed."""
from pathlib import Path
import importlib.util
import sys
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
AGENT=str(ROOT/"webbie"/"agent")
if AGENT not in sys.path:
    sys.path.insert(0,AGENT)
from voice_trust import verify_speaker_evidence

spec=importlib.util.spec_from_file_location(
    "spider_safe_speaker_provider",ROOT/"webbie"/"voice"/"speaker_voice_provider.py")
provider=importlib.util.module_from_spec(spec)
spec.loader.exec_module(provider)


class VoiceprintSafetyTests(unittest.TestCase):
    def setUp(self):
        self.cory=(1.0,)+ (0.0,)*63
        self.shayna=(0.0,1.0)+ (0.0,)*62

    def test_missing_enrollment_always_fails_closed(self):
        self.assertIsNone(provider._select_identity(self.cory, {}))
        with (mock.patch.object(provider,"_profiles",return_value={}),
              mock.patch.object(provider,"recording_fingerprint",return_value="abcdef")):
            self.assertIsNone(provider.verify_audio_segment("synthetic.wav"))

    def test_owner_and_partner_are_only_allowed_speakers(self):
        profiles={"cory":self.cory,"shayna":self.shayna}
        self.assertEqual(provider._select_identity(self.cory,profiles)[1],"cory")
        self.assertEqual(provider._select_identity(self.shayna,profiles)[1],"shayna")
        outsider=(0.0,0.0,1.0)+(0.0,)*61
        self.assertIsNone(provider._select_identity(outsider,profiles))

    def test_refuses_ambiguous_voice_or_low_score(self):
        self.assertIsNone(provider._select_identity(
            self.cory, {"cory":self.cory,"shayna":self.cory}))
        nearly=(0.75,0.66)+(0.0,)*62
        self.assertIsNone(provider._select_identity(nearly,{"cory":self.cory}))

    def test_approved_voice_binds_to_one_audio_digest(self):
        with (mock.patch.object(provider,"_profiles",return_value={"cory":self.cory}),
              mock.patch.object(provider,"_embedding",return_value=self.cory),
              mock.patch.object(provider,"recording_fingerprint",return_value="a"*64)):
            result=provider.verify_audio_segment("synthetic.wav")
        self.assertIsNotNone(result)
        self.assertEqual(result.name,"cory")
        self.assertEqual(result.audio_digest,"a"*64)
        self.assertTrue(verify_speaker_evidence(result))

    def test_mutated_audio_is_rejected_even_with_matched_embedding(self):
        with (mock.patch.object(provider,"_profiles",return_value={"cory":self.cory}),
              mock.patch.object(provider,"_embedding",return_value=self.cory),
              mock.patch.object(provider,"recording_fingerprint",
                                side_effect=["a"*64,"b"*64])):
            self.assertIsNone(provider.verify_audio_segment("synthetic.wav"))

    def test_existing_pin_loader_keeps_adapter_off_without_approval(self):
        from speaker_provider_loader import speaker_gate_from_config
        gate=speaker_gate_from_config({"speaker_verification":{
            "enabled":False,"provider_sha256":""}})
        self.assertFalse(gate.configured)
        self.assertIsNone(gate.verify_file("no.wav"))


if __name__=="__main__":
    unittest.main()
