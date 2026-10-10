"""Native BCN Nova DJ regression tests, no network or audio hardware required."""
import importlib
import random
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SERVICE_DIR = Path(__file__).resolve().parents[1] / "media" / "ai-dj"
sys.path.insert(0, str(SERVICE_DIR))
from nova_host import NovaHost, normalize_request, trim_script, STATION, HOST  # noqa: E402

class PersonaTests(unittest.TestCase):
    def setUp(self):
        self.host = NovaHost(rng=random.Random(12))
        self.song = {
            "currentTrack": {"title": "The River Remembers", "artist": "Broken Sorrow"},
            "nextTrack": {"title": "Neon Graves", "artist": "Broken Sorrow"},
            "type": "transition"
        }

    def test_webbie_stays_webbie_elsewhere_but_calls_herself_nova_on_air(self):
        for mode in ("station_id", "liner", "show_intro", "show_outro", "transition"):
            message = self.host.compose({**self.song, "type": mode}, generate=lambda messages: "")
            self.assertTrue(message)
            self.assertNotIn("Webbie", message)
            self.assertTrue("Nova" in message or "BCN" in message)

    def test_station_id_and_liners_vary(self):
        ids = [self.host.compose({"type": "station_id"}) for _ in range(3)]
        self.assertEqual(len(set(ids)), 3)
        self.assertTrue(all("BCN" in text or "Broken City Network" in text for text in ids))

    def test_metadata_is_bounded(self):
        messages = self.host.prompt_messages({
            "currentTrack": {"title": "X" * 500, "artist": ["A", "B"]},
            "nextTrack": {"title": "Y"},
            "context": {"showName": "Nightwatch", "tone": "haunting"},
        })
        self.assertIn("Nightwatch", messages[1]["content"])
        self.assertIn("Nova", messages[0]["content"])
        self.assertNotIn("X" * 101, messages[1]["content"])

    def test_listener_message_needs_explicit_approval(self):
        payload = {"type": "request", "request": {"approvedRequest": "Neon Graves for Sam"}}
        self.assertEqual(normalize_request(payload)["approved_request"], "")
        self.assertNotIn("Sam", self.host.compose(payload, generate=lambda messages: ""))
        payload["request"]["approved"] = True
        self.assertIn("Sam", self.host.compose(payload, generate=lambda messages: ""))

    def test_recover_when_ollama_fails(self):
        def offline(_messages):
            raise TimeoutError("Ollama not responding")
        script = self.host.compose(self.song, generate=offline)
        self.assertIn("Neon Graves", script)
        self.assertTrue(len(script.split()) <= 48)

    def test_cleanup_and_word_limit(self):
        generated = "Webbie: [music sting] " + "word " * 100
        cleaned = trim_script(generated)
        self.assertNotIn("Webbie", cleaned)
        self.assertNotIn("[", cleaned)
        self.assertLessEqual(len(cleaned.split()), 48)

    def test_concurrent_calls_preserve_history(self):
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=6) as pool:
            list(pool.map(lambda _: self.host.compose(self.song), range(30)))
        self.assertEqual(len(self.host.recent()), 12)

    def test_service_uses_same_one_host(self):
        service = importlib.import_module("service")
        self.assertEqual(service.PERSONA.__class__.__name__, "NovaHost")
        self.assertEqual(service.ON_AIR_HOST, HOST)
        self.assertEqual(service.STATION_NAME, STATION)
        with patch.object(service.PERSONA, "compose", return_value="Nova here, BCN radio.") as compose:
            self.assertEqual(service.ollama_script(self.song), "Nova here, BCN radio.")
            compose.assert_called_once()

if __name__ == "__main__":
    unittest.main()
