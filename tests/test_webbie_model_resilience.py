"""Offline deterministic regression suite for Webbie's Ollama resiliency."""
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"webbie/brain"))
import model_resilience as m
import brain

class ModelResilienceTests(unittest.TestCase):
    def test_timeout_bounds_do_not_inherit_bad_environment(self):
        for value in ("x","0","9","181","100000000","",None):
            self.assertEqual(m.response_timeout({"WEBBIE_OLLAMA_TIMEOUT_SECONDS":value}),90)
        for value in ("10","30","90","180"):
            self.assertEqual(m.response_timeout({"WEBBIE_OLLAMA_TIMEOUT_SECONDS":value}),int(value))

    def test_consecutive_failures_pause_then_single_trial(self):
        now=[100.]
        breaker=m.ModelResilience(clock=lambda:now[0],failure_limit=3,cooldown=45)
        for _ in range(3):
            self.assertTrue(breaker.acquire())
            breaker.finish(succeeded=False)
        self.assertFalse(breaker.acquire())
        self.assertEqual(breaker.status()["status"],"temporarily_paused")
        self.assertGreaterEqual(breaker.status()["retry_after_seconds"],44)
        now[0]=145.
        self.assertTrue(breaker.acquire())
        self.assertFalse(breaker.acquire())
        breaker.finish(succeeded=True)
        self.assertTrue(breaker.acquire())
        self.assertEqual(breaker.status()["consecutive_failures"],0)

    def test_failed_half_open_trial_reopens(self):
        now=[0.]
        b=m.ModelResilience(clock=lambda:now[0],failure_limit=1,cooldown=20)
        self.assertTrue(b.acquire())
        b.finish(succeeded=False)
        self.assertFalse(b.acquire())
        now[0]=20.
        self.assertTrue(b.acquire())
        b.finish(succeeded=False)
        self.assertFalse(b.acquire())

    def test_invalid_outcomes_and_configs(self):
        with self.assertRaises(ValueError):m.ModelResilience(failure_limit=0)
        with self.assertRaises(ValueError):m.ModelResilience(cooldown=601)
        with self.assertRaises(ValueError):m.ModelResilience().finish(succeeded=1)

    def test_local_ollama_failure_never_retries_or_switches_models(self):
        def fail(req,timeout=None):
            raise OSError("test local offline")
        local=m.ModelResilience(failure_limit=2,cooldown=100)
        with patch.object(brain,"MODEL_GOVERNOR",local),patch(
                "brain.urllib.request.urlopen",side_effect=fail) as opener,patch(
                "brain.load_conversation",return_value=[]),patch(
                "brain.recall_memories",return_value=[]):
            self.assertIsNone(brain.ask_ollama("test one"))
            self.assertIsNone(brain.ask_ollama("test two"))
            self.assertIsNone(brain.ask_ollama("test three"))
            self.assertEqual(opener.call_count,2)
            self.assertEqual(local.status()["status"],"temporarily_paused")

    def test_valid_model_response_recovers_breaker(self):
        import io
        class Response:
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def read(self,count):return b'{"message":{"content":"Ready"}}'
        local=m.ModelResilience(failure_limit=1,cooldown=1)
        with patch.object(brain,"MODEL_GOVERNOR",local),patch(
                "brain.urllib.request.urlopen",return_value=Response()),patch(
                "brain.load_conversation",return_value=[]),patch(
                "brain.recall_memories",return_value=[]):
            self.assertEqual(brain.ask_ollama("Status"),"Ready")
            self.assertEqual(local.status()["last_outcome"],"responded")
            self.assertEqual(local.status()["consecutive_failures"],0)

    def test_oversize_answer_is_error(self):
        class Response:
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def read(self,n):return b"A"*(n)
        local=m.ModelResilience()
        with patch.object(brain,"MODEL_GOVERNOR",local),patch(
                "brain.urllib.request.urlopen",return_value=Response()),patch(
                "brain.load_conversation",return_value=[]),patch(
                "brain.recall_memories",return_value=[]):
            self.assertIsNone(brain.ask_ollama("Status"))
            self.assertEqual(local.status()["last_outcome"],"unavailable")

    def test_brain_failure_does_not_pollute_memory(self):
        broken=m.ModelResilience(failure_limit=1)
        broken.finish(succeeded=False)
        with patch.object(brain,"MODEL_GOVERNOR",broken),patch(
                "brain.long_term_memory_response",return_value=None),patch(
                "brain.research_response",return_value=None),patch(
                "brain.maybe_auto_remember",return_value=False),patch(
                "brain.remember_turn") as persist:
            answer=brain.respond("Are you there?")
            self.assertIn("repeated failures",answer)
            persist.assert_not_called()

if __name__=="__main__":unittest.main()
