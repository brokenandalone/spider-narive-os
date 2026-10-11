"""Offline regression tests for Forage providers, private archives, cancellation."""
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "forage" / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


providers = module("search_backends")
archive = module("research_archive")
engine = module("engine")


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False
    def read(self, maximum):
        return self.payload[:maximum]


class SearchRouterTests(unittest.TestCase):
    def test_searxng_first_and_source_provenance(self):
        called = []
        def opener(request, timeout):
            called.append(request.full_url)
            self.assertEqual(timeout, 8)
            return FakeResponse({"results": [
                {"title": "A", "url": "https://example.org/study", "content": "Paper", "publishedDate": "2026-10-01"},
                {"title": "Bad", "url": "http://127.0.0.1/admin"},
                {"title": "Duplicate", "url": "https://example.org/study"},
            ]})
        result = providers.search_web("research", opener=opener,
                                      ddgs_factory=lambda: self.fail("DDGS should not start"))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["engine"], "searxng")
        self.assertEqual(result[0]["published"], "2026-10-01")
        self.assertIn("127.0.0.1:8888/search?", called[0])
        self.assertIn("format=json", called[0])

    def test_ddgs_fallback_and_normalized_results(self):
        class DDGS:
            def __init__(self, **kwargs):
                self.assertion = kwargs
            def text(self, *args, **kwargs):
                return [{"href": "https://example.com/topic", "title": "Topic", "body": "Read me"}]
        def broken(*args, **kwargs):
            raise OSError("searx offline")
        rows = providers.search_web("topic", opener=broken, ddgs_factory=lambda: DDGS)
        self.assertEqual(rows[0]["engine"], "ddgs")
        self.assertEqual(rows[0]["snippet"], "Read me")

    def test_reject_local_addresses_and_credentials(self):
        for url in ["file:///etc/passwd", "http://localhost", "http://127.0.0.1",
                    "https://192.168.1.1", "http://10.0.0.1", "http://[::1]",
                    "https://user:secret@example.com/file", "http://gateway.internal",
                    "javascript:alert(1)"]:
            self.assertFalse(providers.public_url(url), url)
        self.assertTrue(providers.public_url("https://example.com/research"))

    def test_no_provider_does_not_pretend_to_find_sources(self):
        with self.assertRaises(RuntimeError):
            providers.search_web("topic", opener=lambda *a, **k: (_ for _ in ()).throw(OSError()),
                                 ddgs_factory=lambda: None)
        self.assertEqual(providers.clean_results([{"url": "file:///etc/passwd"}], 10, "test"), [])


class ResearchArchiveTests(unittest.TestCase):
    def test_reports_are_unique_private_and_have_reopenable_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = [{"url": "https://example.org", "title": "Article", "content": "Evidence",
                         "snippet": "summary", "evidence_kind": "page_text"}]
            saved1, sources1 = archive.save_research("Spider OS", ["# Deep Forage: Spider OS",
                                         "", "Generated: now", "Evidence status: sources_available"], original, tmp)
            saved2, sources2 = archive.save_research("Spider OS", ["# Deep Forage: Spider OS",
                                         "", "Generated: now", "Evidence status: no_sources"], [], tmp)
            self.assertNotEqual(saved1, saved2)
            self.assertEqual(Path(saved1).stat().st_mode & 0o777, 0o600)
            self.assertEqual(Path(sources1).stat().st_mode & 0o777, 0o600)
            self.assertEqual(json.loads(Path(sources1).read_text())["sources"][0]["content"], "Evidence")
            self.assertEqual(len(archive.list_reports(tmp)), 2)
            self.assertEqual({r["evidence_status"] for r in archive.list_reports(tmp)},
                             {"sources_available", "no_sources"})
            self.assertTrue(Path(sources2).exists())

    def test_history_skips_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            another = Path(tmp).parent / "external-report.md"
            # The target does not need to exist for a symlink to be excluded.
            (Path(tmp) / "bad.md").symlink_to(another)
            self.assertEqual(archive.list_reports(tmp), [])


class ResearchCancellationTests(unittest.TestCase):
    def test_cancel_before_run_saves_nothing(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(engine, "REPORT_DIR", Path(tmp)), \
             patch.object(engine, "ensure_storage") as ensure:
            with self.assertRaises(engine.ResearchCancelled):
                engine.deep_research("topic", cancel=lambda: True)
            ensure.assert_not_called()
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_cancel_after_search_prevents_report_and_synthesis(self):
        stop = threading.Event()
        def web(*a, **k):
            stop.set()
            return [{"title": "Paper", "url": "https://example.org", "snippet": "Evidence"}]
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(engine, "REPORT_DIR", Path(tmp)), \
             patch.object(engine, "ensure_storage"), \
             patch.object(engine, "build_research_queries", return_value=["query"]), \
             patch.object(engine, "web_search", side_effect=web), \
             patch.object(engine, "ollama_chat") as model:
            with self.assertRaises(engine.ResearchCancelled):
                engine.deep_research("topic", cancel=stop.is_set)
            model.assert_not_called()
            self.assertEqual(list(Path(tmp).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
