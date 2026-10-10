"""Webby is a spelling alias, never a new identity or speaker authorization."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
NIGHT = ROOT / "webbie/agent/night_mode.py"
CONFIG = ROOT / "webbie/config/default.json"
AGENT = ROOT / "webbie/agent/webbie.py"

spec = importlib.util.spec_from_file_location("webbie_night_mode_alias_test", NIGHT)
night = importlib.util.module_from_spec(spec)
spec.loader.exec_module(night)


class WebbyAliasTests(unittest.TestCase):
    def test_config_preserves_original_name_and_accepts_transcription_alias(self):
        config = json.loads(CONFIG.read_text())
        self.assertEqual(config["name"], "Webbie")
        self.assertIn("hey webbie", config["wake_words"])
        self.assertIn("hey webby", config["wake_words"])
        self.assertIn("webby", config["wake_words"])
        self.assertNotIn("wavy", config["wake_words"])

    def test_explicit_sleep_and_wake_accept_webby(self):
        self.assertEqual(night.spoken_mode("Hey Webby go to sleep"), "sleep")
        self.assertEqual(night.spoken_mode("Webby wake up", sleeping=True), "wake")
        self.assertEqual(night.spoken_mode("Hey Webbie wake up", sleeping=True), "wake")
        self.assertIsNone(night.spoken_mode("Webby", sleeping=True))
        self.assertIsNone(night.spoken_mode("Wavy wake up", sleeping=True))

    def test_agent_normalizes_name_before_processing_voice(self):
        source = AGENT.read_text()
        normalized = 'phrase = re.sub(r"\\bwebby\\b", "webbie", phrase)'
        self.assertIn(normalized, source)
        self.assertLess(source.index(normalized), source.index('sleeping = quiet_asleep()', source.index('    def on_text(phrase):')))


if __name__ == "__main__":
    unittest.main()
