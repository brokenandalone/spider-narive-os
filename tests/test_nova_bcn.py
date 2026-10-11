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


class NativeHTTPTests(unittest.TestCase):
    """Exercise real HTTP requests, not just Python persona imports."""

    @classmethod
    def setUpClass(cls):
        import importlib
        import threading
        from http.server import ThreadingHTTPServer
        cls.service = importlib.import_module("service")
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), cls.service.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = "http://127.0.0.1:" + str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def request(self, path, method="GET", body=None):
        import urllib.error
        import urllib.request
        import json
        payload = None if body is None else json.dumps(body).encode("utf8")
        req = urllib.request.Request(self.base + path, data=payload, method=method)
        if payload is not None:
            req.add_header("Content-Type", "application/json")
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            response = opener.open(req, timeout=3)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            data = response.read()
            return response.status, dict(response.headers), (
                json.loads(data) if data else None
            )

    def test_health_endpoint_returns_json_and_nova_identity(self):
        status, headers, body = self.request("/health")
        self.assertEqual(status, 200)
        self.assertIn("application/json", headers["Content-Type"])
        self.assertEqual(body["ok"], True)
        self.assertEqual(body["host"], "Nova")
        self.assertEqual(body["service"], "Spider AI DJ")
        self.assertEqual(body["port"], self.service.PORT)

    def test_options_and_unknown_get_have_valid_headers(self):
        status, headers, body = self.request("/health", "OPTIONS")
        self.assertEqual(status, 204)
        self.assertIsNone(body)
        self.assertIn("POST", headers["Access-Control-Allow-Methods"])
        status, _, body = self.request("/not-found")
        self.assertEqual(status, 404)
        self.assertEqual(body["error"], "not found")

    def test_prepare_route_handles_valid_requests_and_unknown_post(self):
        from pathlib import Path
        from contextlib import ExitStack
        unknown, _, missing = self.request("/other", "POST", {"type":"transition"})
        self.assertEqual(unknown, 404)
        self.assertEqual(missing["error"], "not found")
        with ExitStack() as stack:
            stack.enter_context(patch.object(self.service, "ollama_script", return_value="Nova for BCN"))
            stack.enter_context(patch.object(self.service, "make_audio", return_value=Path("/tmp/nova-test.wav")))
            stack.enter_context(patch.object(self.service, "cleanup"))
            success, headers, message = self.request(
                "/dj/prepare", "POST",
                {"type":"station_id","secondsRemaining":7}
            )
        self.assertEqual(success, 200)
        self.assertEqual(message["host"], "Nova")
        self.assertEqual(message["script"], "Nova for BCN")
        self.assertEqual(message["type"], "station_id")
        self.assertEqual(message["talkOver"]["crossfadeSeconds"], 3.0)
        self.assertIn("application/json", headers["Content-Type"])

    def test_prepare_error_stays_json_not_broken_pipe(self):
        with patch.object(self.service, "ollama_script", side_effect=RuntimeError("tts unavailable")):
            status, _, body = self.request("/dj/prepare", "POST", {"type":"transition"})
        self.assertEqual(status, 500)
        self.assertIn("tts unavailable", body["error"])

if __name__ == "__main__":
    unittest.main()
