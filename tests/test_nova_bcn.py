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


class ProductionStudioTests(unittest.TestCase):
    def test_production_drafts_have_no_audio(self):
        service = importlib.import_module("service")
        with patch.object(service, "ollama_script", return_value="Nova here on BCN"), patch.object(service, "make_audio") as audio:
            status, _, body = NativeHTTPTests.request(self, "/dj/draft", "POST", {"type": "show_id", "context":{"showName":"Nightwatch"}})
            self.assertEqual(status, 200)
            self.assertTrue(body["draft"])
            self.assertFalse(body["approved"])
            self.assertIsNone(body["audioFile"])
            audio.assert_not_called()

    def test_commercial_requires_known_sponsor_and_operator_approval(self):
        service = importlib.import_module("service")
        self.assertRaisesRegex(ValueError, "sponsor", service.production_context,
                               {"type":"commercial","context":{}})
        status, _, body = NativeHTTPTests.request(self, "/dj/prepare", "POST", {"type":"commercial",
            "context":{"productionMode":True,"sponsor":"Example Sponsor",
                       "approvedCopy":"Example Sponsor supports BCN today."}})
        self.assertEqual(status, 500)
        self.assertIn("Approve production copy",body["error"])

    def test_produced_voice_speaks_approved_copy_without_rewriting(self):
        service = importlib.import_module("service")
        script="This is Broken City Network. You are tuned into Nightwatch."
        with patch.object(service,"ollama_script") as model, patch.object(service,"make_audio",return_value=Path("/tmp/bcn.wav")) as voice, patch.object(service,"cleanup"):
            status, _, body = NativeHTTPTests.request(self, "/dj/prepare", "POST", {"type":"show_id",
                "context":{"productionMode":True,"copyApproved":True,"approvedCopy":script,
                           "voiceProfile":"matilda","showName":"Nightwatch"}})
            self.assertEqual(status,200)
            self.assertEqual(body["script"],script)
            voice.assert_called_once()
            model.assert_not_called()

    def test_production_categories_have_safe_fallback_copy(self):
        host=NovaHost(rng=random.Random(3))
        for kind in ("show_id","station_id","commercial","promo","sweeper","bumper"):
            message=host.compose({"type":kind,"context":{"showName":"Nightwatch","sponsor":"Example Sponsor"}},generate=lambda _: "")
            self.assertTrue(message)
        message=host.fallback_script({"type":"commercial","context":{"sponsor":"Example Sponsor"}})
        self.assertIn("Example Sponsor",message)
        self.assertNotIn("50 percent",message)


class SharedAustralianVoiceTests(unittest.TestCase):
    def test_profiles_are_a_fixed_safe_allowlist(self):
        from nova_voice import SPEAKERS, VOICES, normalize_voice
        self.assertEqual(SPEAKERS["matilda"], 7)
        self.assertEqual(SPEAKERS["kirra"], 3)
        self.assertEqual(SPEAKERS["bindi"], 1)
        self.assertEqual(SPEAKERS["marlo"], 2)
        self.assertEqual(SPEAKERS["tully"], 8)
        self.assertEqual(SPEAKERS["willow"], 9)
        self.assertIn("natasha", VOICES)
        self.assertEqual(normalize_voice(" MaTiLdA "), "matilda")
        self.assertEqual(normalize_voice("../../bin/sh"), "auto")

    def test_matilda_offline_and_kirra_selection_share_webbie_model(self):
        import tempfile
        import wave
        from nova_voice import synthesize
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            root = home / ".local/share/spider-os/webbie-neural-preview"
            python = root / "venv/bin/python3"
            model = root / "models/en_AU-librivox-medium.onnx"
            python.parent.mkdir(parents=True)
            python.write_text("#!/usr/bin/python3\n")
            python.chmod(0o700)
            model.parent.mkdir(parents=True)
            model.write_bytes(b"example-model")
            Path(str(model) + ".json").write_text("{}")
            calls = []
            def fake_run(args, **kwargs):
                calls.append((args, kwargs))
                self.assertEqual(kwargs.get("input"), "Nova here on BCN.\n")
                out = Path(args[args.index("-f") + 1])
                with wave.open(str(out), "wb") as writer:
                    writer.setnchannels(1)
                    writer.setsampwidth(2)
                    writer.setframerate(22050)
                    writer.writeframes(b"\x00\x00" * 800)
            for name, index in (("matilda", "7"), ("kirra", "3")):
                audio = synthesize("Nova here on BCN.", "nova-test-" + name, profile=name,
                    home=home, cache=home / "cache", runner=fake_run, which=lambda _: None)
                self.assertTrue(audio.is_file())
                self.assertEqual(calls[-1][0][calls[-1][0].index("-s") + 1], index)
                self.assertIn(str(model), calls[-1][0])

    def test_auto_uses_matilda_when_online_natasha_unavailable(self):
        import tempfile
        import wave
        from nova_voice import synthesize
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            root = home / ".local/share/spider-os/webbie-neural-preview"
            python = root / "venv/bin/python3"
            model = root / "models/en_AU-librivox-medium.onnx"
            python.parent.mkdir(parents=True)
            python.write_text("python")
            python.chmod(0o700)
            model.parent.mkdir(parents=True)
            model.write_bytes(b"model")
            Path(str(model) + ".json").write_text("{}")
            calls = []
            def piper_only(args, **kwargs):
                calls.append(args)
                with wave.open(args[args.index("-f") + 1], "wb") as writer:
                    writer.setnchannels(1)
                    writer.setsampwidth(2)
                    writer.setframerate(22050)
                    writer.writeframes(b"\x00\x00" * 800)
            audio = synthesize("Nova announces music", "nova-auto", profile="auto",
                home=home, cache=home / "cache", runner=piper_only, which=lambda _: None)
            self.assertEqual(audio.suffix, ".wav")
            self.assertEqual(calls[0][calls[0].index("-s") + 1], "7")

    def test_native_service_reports_voice_profiles_and_routes_operator_choice(self):
        import importlib
        import json
        from unittest.mock import patch
        service = importlib.import_module("service")
        self.assertIn("matilda", service.available_profiles()["voices"])
        self.assertIn("kirra", service.available_profiles()["voices"])
        with patch.object(service, "ollama_script", return_value="Nova speaks"), \
             patch.object(service, "make_audio", return_value=Path("/tmp/nova-test.wav")) as audio, \
             patch.object(service, "cleanup"):
            from http.server import ThreadingHTTPServer
            import threading, urllib.request
            server = ThreadingHTTPServer(("127.0.0.1", 0), service.Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = "http://127.0.0.1:" + str(server.server_port)
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                with opener.open(url + "/dj/voices", timeout=3) as reply:
                    self.assertIn("matilda", json.load(reply)["voices"])
                body = json.dumps({"context": {"voiceProfile": "kirra"}, "type": "station_id"}).encode()
                with opener.open(urllib.request.Request(url + "/dj/prepare", data=body, method="POST"), timeout=3) as reply:
                    self.assertEqual(json.load(reply)["host"], "Nova")
                audio.assert_called_once()
                self.assertEqual(audio.call_args.kwargs["profile"], "kirra")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)



class NovaNeuralOnlyTests(unittest.TestCase):
    def test_on_air_refuses_robotic_espeak_even_if_it_is_installed(self):
        import tempfile
        from nova_voice import synthesize
        with tempfile.TemporaryDirectory() as tmp:
            attempted = []
            def fail_run(args, **kwargs):
                attempted.append(args[0])
                raise OSError("offline")
            with self.assertRaisesRegex(RuntimeError, "robotic eSpeak was not used"):
                synthesize("A short BCN liner", "nova-test-voice",
                           profile="auto", cache=Path(tmp), home=Path(tmp),
                           runner=fail_run, which=lambda name:"/usr/bin/"+name,
                           allow_espeak=False)
            self.assertNotIn("/usr/bin/espeak-ng", attempted)

    def test_auto_prefers_matilda_when_installed_and_reports_engine(self):
        import tempfile, wave
        from nova_voice import synthesize
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp)
            directory=home/".local/share/spider-os/webbie-neural-preview"
            python=directory/"venv/bin/python3"
            model=directory/"models/en_AU-librivox-medium.onnx"
            python.parent.mkdir(parents=True)
            model.parent.mkdir(parents=True)
            python.write_text("python")
            python.chmod(0o700)
            model.write_bytes(b"model")
            Path(str(model)+".json").write_text("{}")
            def fake_run(args, **kwargs):
                if args[0]!=str(python):
                    raise AssertionError("Matilda should be tried first")
                with wave.open(args[args.index("-f")+1], "wb") as writer:
                    writer.setnchannels(1)
                    writer.setsampwidth(2)
                    writer.setframerate(22050)
                    writer.writeframes(b"\\x00\\x00"*800)
            result={}
            audio=synthesize("BCN voice test", "matilda-test", profile="auto",
                             home=home, cache=home/"cache", runner=fake_run,
                             which=lambda _:None, allow_espeak=False,report=result)
            self.assertTrue(audio.is_file())
            self.assertEqual(result["engine"],"matilda")
            self.assertEqual(result["voiceProfileRequested"],"auto")
            self.assertFalse(result["usedFallback"])

    def test_native_service_explicitly_forbids_espeak_and_reports_status(self):
        import inspect, service
        self.assertIn("allow_espeak=False",inspect.getsource(service.make_audio))
        self.assertFalse(service.LAST_VOICE.get("usedFallback"))

if __name__ == "__main__":
    unittest.main()
