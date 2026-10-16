#!/usr/bin/env python3
"""Regression tests for reconciling owner-tested Webbie AI V2 with newer GitHub features.

No microphone, model, root access, network or desktop session is required.
"""
import importlib.util
import json
from pathlib import Path
from unittest import TestCase, mock
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WebbieAIV2SourceTests(TestCase):
    def test_integrated_agent_keeps_voice_gate_and_workspace_context(self):
        content = (ROOT / "webbie/agent/webbie.py").read_text()
        self.assertIn("from webbie_ai_isolation import respond", content)
        self.assertIn("voice_permission(", content)
        self.assertIn("speaker_verified=speaker_verified", content)
        self.assertIn("voice_turns.current(expected_turn)", content)
        self.assertIn("advisory_context=extra_context", content)
        self.assertIn("request_approved_website", content)

    def test_model_config_preserves_owner_voice_and_safety(self):
        config = json.loads((ROOT / "webbie/config/default.json").read_text())
        self.assertEqual(config["voice"]["online"], "en-AU-NatashaNeural")
        self.assertEqual(config["voice"]["offline"], "en-au+f3")
        self.assertEqual(config["context_names"]["author"], "Writer")
        self.assertEqual(config["ollama"]["model"], "qwen3:8b")
        self.assertFalse(config["speaker_verification"]["enabled"])
        self.assertIn("provider_sha256", config["speaker_verification"])
        self.assertIn("proactive", config)
        brain = (ROOT / "webbie/brain/brain.py").read_text()
        self.assertIn('DEFAULT_MODEL = "qwen3:8b"', brain)

    def test_release_copies_every_ai_worker_module(self):
        batch = (ROOT / "system/release_batch.py").read_text()
        for filename in ("webbie_ai_isolation.py", "webbie_ai_worker.py",
                         "webbie_brain_primary.py"):
            path = ROOT / "webbie/agent" / filename
            self.assertTrue(path.is_file())
            self.assertIn("'webbie/agent/" + filename + "'", batch)

    def test_primary_worker_forwards_original_workspace_advisory(self):
        worker = load_module("webbie_test_worker", "webbie/agent/webbie_ai_worker.py")
        seen = {}
        def reply(ident, message, context, advisory, seconds):
            seen.update(id=ident, message=message, context=context,
                        advisory=advisory, seconds=seconds)
            return "Real Webbie answer"
        with mock.patch.object(worker, "_primary_reply", side_effect=reply):
            result = worker._answer({
                "id": "request-1",
                "message": "Explain this Studio session",
                "context_name": "Justin",
                "advisory_context": "Owner-selected Studio timeline context",
            })
        self.assertTrue(result["ok"])
        self.assertEqual(result["reply"], "Real Webbie answer")
        self.assertEqual(seen["context"], "Justin")
        self.assertEqual(seen["advisory"], "Owner-selected Studio timeline context")
        self.assertEqual(seen["seconds"], 14.0)

    def test_primary_timeout_recovers_only_through_local_fallback(self):
        worker = load_module("webbie_test_worker_fallback", "webbie/agent/webbie_ai_worker.py")
        with (mock.patch.object(worker, "_primary_reply", side_effect=TimeoutError("stalled")),
              mock.patch.object(worker, "_stop_primary") as stop,
              mock.patch.object(worker, "_fallback_reply", return_value="Recovered") as fallback):
            result = worker._answer({"id": "reply-2", "message": "hello",
                                     "context_name": "Spider"})
        self.assertEqual(result["reply"], "Recovered")
        stop.assert_called_once()
        fallback.assert_called_once_with("hello", "Spider")

    def test_fallback_never_opens_nonlocal_model_endpoints(self):
        worker = load_module("webbie_test_worker_url", "webbie/agent/webbie_ai_worker.py")
        with (mock.patch.dict("os.environ",
                              {"WEBBIE_LOCAL_OLLAMA_CHAT_URL": "https://example.com/api/chat"}),
              mock.patch.object(worker.urllib.request, "urlopen") as remote):
            with self.assertRaises(ValueError):
                worker._fallback_reply("hello", "Spider")
            remote.assert_not_called()

    def test_fallback_rejects_other_loopback_ports_and_forgets_past_messages(self):
        worker = load_module("webbie_test_worker_port", "webbie/agent/webbie_ai_worker.py")
        self.assertFalse(hasattr(worker, "_HISTORY"),
                         "the emergency model must not retain prior private conversations")
        with (mock.patch.dict("os.environ",
                              {"WEBBIE_LOCAL_OLLAMA_CHAT_URL": "http://127.0.0.1:9999/api/chat"}),
              mock.patch.object(worker.urllib.request, "urlopen") as unauthorized):
            with self.assertRaises(ValueError):
                worker._fallback_reply("private question", "Spider")
            unauthorized.assert_not_called()

    def test_primary_child_preserves_full_brain_import(self):
        source = (ROOT / "webbie/agent/webbie_brain_primary.py").read_text()
        self.assertIn("from brain import respond", source)
        self.assertIn('advisory_context=str(data.get("advisory_context")', source)
        self.assertNotIn("subprocess.run", source)

    def test_ipc_accepts_advisory_without_new_desktop_permissions(self):
        source = (ROOT / "webbie/agent/webbie_ai_isolation.py").read_text()
        self.assertIn('def respond(message, context_name="Spider", advisory_context=None)', source)
        self.assertIn('"advisory_context": str(advisory_context or "")[:3500]', source)
        self.assertNotIn("sudo ", source)
        self.assertNotIn("podman ", source)


if __name__ == "__main__":
    unittest.main()
