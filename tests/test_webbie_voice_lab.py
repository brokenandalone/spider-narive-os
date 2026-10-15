"""Webbie Voice Lab presence diagnostics never sample microphones."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"webbie/agent"))
import voice_lab

class VoiceLabTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.config=self.root/"config.json"
        self.voice=self.root/"voice"
        self.voice.mkdir()
        self.binary=self.root/"whisper-cli"
        self.binary.write_text("dummy")
        self.model=self.root/"model.bin"
        self.model.write_bytes(b"dummy")
        self.recorder=self.root/"arecord"
        self.recorder.write_text("dummy")

    def inspect(self,config=None):
        self.config.write_text(json.dumps(config or {}))
        return voice_lab.inspect_voice_lab(
            config_path=self.config,model_path=self.model,
            voice_path=self.voice,executable=str(self.binary),
            which=lambda k:str(self.recorder) if k=="arecord" else None)

    def test_only_static_presence_not_live_audio(self):
        item=self.inspect()
        self.assertTrue(item["whisper_available"])
        self.assertTrue(item["arecord_available"])
        self.assertTrue(item["whisper_model_available"])
        self.assertFalse(item["voiceprint_opted_in"])
        self.assertFalse(item["voiceprint_verified"])
        output=voice_lab.voice_lab_report(item)
        self.assertIn("NOT VERIFIED BY THIS CHECK",output)
        self.assertIn("No microphone audio",output)
        self.assertNotIn(str(self.root),output)

    def test_opt_in_still_does_not_claim_authenticated_speaker(self):
        (self.voice/"speaker_voice_provider.py").write_text("# sample")
        item=self.inspect({"speaker_verification":{"enabled":True}})
        self.assertTrue(item["voiceprint_opted_in"])
        self.assertTrue(item["voiceprint_file_present"])
        self.assertFalse(item["voiceprint_verified"])

    def test_owner_pinned_provider_code_reports_hash_match_only(self):
        import hashlib
        provider=self.voice/"speaker_voice_provider.py"
        provider.write_text("# audited placeholder")
        digest=hashlib.sha256(provider.read_bytes()).hexdigest()
        item=self.inspect({"speaker_verification":{
            "enabled":True,"provider_sha256":digest}})
        self.assertTrue(item["voiceprint_source_pinned"])
        self.assertFalse(item["voiceprint_verified"])
        provider.write_text("# changed without approval")
        result=self.inspect({"speaker_verification":{
            "enabled":True,"provider_sha256":digest}})
        self.assertFalse(result["voiceprint_source_pinned"])

    def test_missing_files_report_unconfirmed(self):
        self.model.unlink()
        self.binary.unlink()
        self.recorder.unlink()
        item=self.inspect()
        text=voice_lab.voice_lab_report(item)
        self.assertIn("NOT CONFIRMED",text)

    def test_symlinked_model_and_provider_rejected(self):
        outside=self.root/"other.py"
        outside.write_text("ignore")
        (self.voice/"speaker_voice_provider.py").symlink_to(outside)
        self.model.unlink()
        self.model.symlink_to(outside)
        result=self.inspect({"speaker_verification":{"enabled":True}})
        self.assertFalse(result["voiceprint_file_present"])
        self.assertFalse(result["whisper_model_available"])

if __name__=="__main__":
    unittest.main()
