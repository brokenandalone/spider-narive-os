"""Read-only CLI reports component states, never private source values."""
import contextlib
import io
import json
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
sys.path.insert(0,str(ROOT/"webbie/agent"))
import webbie_readiness_cli as cli
from runtime_readiness import Observation

class ReadinessCLITests(unittest.TestCase):
    def test_never_contacts_ollama_without_explicit_flag(self):
        voice={
            "whisper_available":True,"whisper_model_available":True,
            "arecord_available":True,"voiceprint_opted_in":False,
            "voiceprint_source_pinned":False,
        }
        with patch.object(cli,"inspect_readiness",
                          return_value=(Observation("agent","unknown",
                          "No recent confirmed heartbeat"),)),patch.object(
                          cli,"inspect_voice_lab",return_value=voice),patch.object(
                          cli,"inspect_local_models") as models:
            result=cli.collect(models=False)
            models.assert_not_called()
            self.assertNotIn("local_ollama",result)
            self.assertFalse(result["voice"]["speaker_identity_verified"])

    def test_json_only_contains_redacted_categories(self):
        voice={
            "whisper_available":False,"whisper_model_available":False,
            "arecord_available":False,"voiceprint_opted_in":False,
            "voiceprint_source_pinned":False,
            "intake":{"heard_transcript":5,"last_heard":"super secret"}
        }
        with patch.object(cli,"inspect_readiness",
                          return_value=(Observation("agent","unknown",
                          "No recent confirmed heartbeat"),)),patch.object(
                          cli,"inspect_voice_lab",return_value=voice),patch.object(
                          cli,"inspect_local_models") as models:
            output=io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(cli.main(["--json"]),0)
            result=json.loads(output.getvalue())
            self.assertEqual(result["report_format"],"webbie-safe-readiness-v1")
            self.assertNotIn("super secret",output.getvalue())
            self.assertNotIn("last_heard",output.getvalue())
            models.assert_not_called()

    def test_explicit_local_ollama_checks_tags_only(self):
        voice={
            "whisper_available":False,"whisper_model_available":False,
            "arecord_available":False,"voiceprint_opted_in":False,
            "voiceprint_source_pinned":False,
        }
        with patch.object(cli,"inspect_readiness",return_value=()),patch.object(
                cli,"inspect_voice_lab",return_value=voice),patch.object(
                cli,"inspect_local_models",return_value={
                    "online":True,"installed":["qwen3:4b","gemma3:4b"],
                    "running":["qwen3:4b"],
                }):
            result=cli.collect(models=True)
            self.assertEqual(result["local_ollama"]["installed_model_count"],2)
            self.assertNotIn("qwen3:4b",json.dumps(result))

if __name__=="__main__":unittest.main()
