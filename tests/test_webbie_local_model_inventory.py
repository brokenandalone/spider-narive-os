"""Read-only local AI model inspector regressions. Never access network."""
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"webbie/brain"))
import local_model_inventory as m


class FakeResponse:
    def __init__(self,url,payload):
        self.url=url
        self.bytes=io.BytesIO(json.dumps(payload).encode("utf-8"))
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def geturl(self):return self.url
    def read(self,size=-1):return self.bytes.read(size)

class ModelsTests(unittest.TestCase):
    def test_offline_does_not_guess_installed(self):
        def fail(url,timeout=0):
            raise OSError("not running")
        info=m.inspect_local_models(opener=fail,
                                    brain_preference="qwen3:8b")
        self.assertFalse(info["online"])
        self.assertFalse(info["brain"]["ready"])
        self.assertEqual(info["installed"],[])

    def test_installed_running_and_requested(self):
        seen=[]
        def opener(url,timeout=0):
            seen.append((url,timeout))
            if url==m.TAGS:
                return FakeResponse(url,{"models":[
                    {"name":"qwen3:8b"},{"name":"gemma3:4b"},
                    {"name":"qwen3:8b"},{"name":"bad command\n"}]})
            if url==m.RUNNING:
                return FakeResponse(url,{"models":[{"name":"qwen3:8b"}]})
            raise AssertionError("Unexpected endpoint")
        item=m.inspect_local_models(
            opener=opener,brain_preference="qwen3:8b",
            vision_preference="qwen3-vl:2b-instruct")
        self.assertTrue(item["online"])
        self.assertEqual(item["installed"],["gemma3:4b","qwen3:8b"])
        self.assertEqual(item["running"],["qwen3:8b"])
        self.assertTrue(item["brain"]["ready"])
        self.assertFalse(item["vision"]["ready"])
        self.assertEqual(seen,[(m.TAGS,2),(m.RUNNING,2)])
        text=m.report_lines(item)
        self.assertIn("MISSING",text)
        self.assertIn("No models",text) if False else self.assertIn("does not verify response quality",text)

    def test_running_endpoint_failure_does_not_fake_offline(self):
        def opener(url,timeout=0):
            if url==m.TAGS:
                return FakeResponse(url,{"models":[{"name":"qwen3:8b"}]})
            raise TimeoutError()
        info=m.inspect_local_models(opener=opener)
        self.assertTrue(info["online"])
        self.assertEqual(info["running"],[])

    def test_redirect_does_not_send_to_other_endpoint(self):
        class Redirect(FakeResponse):
            def geturl(self):
                return "https://unknown.example"
        def opener(url,timeout=0):
            return Redirect(url,{"models":[]})
        self.assertFalse(m.inspect_local_models(opener=opener)["online"])

    def test_malformed_response_is_rejected(self):
        def opener(url,timeout=0):
            return FakeResponse(url,["wrong"])
        self.assertFalse(m.inspect_local_models(opener=opener)["online"])

    def test_no_unsafe_timeout(self):
        for timeout in (0,-1,20):
            with self.assertRaises(ValueError):
                m.inspect_local_models(timeout=timeout)

if __name__=="__main__":
    unittest.main()
