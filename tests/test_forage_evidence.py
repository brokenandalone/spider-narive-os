"""Research failures must never become plausible, source-free findings."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('forage_evidence', ROOT / 'forage/engine.py')
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)


class ResearchEvidenceTests(unittest.TestCase):
    def run_research(self, found, draft='A supported claim [1].', extracted='Evidence'):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(engine, 'ensure_storage'), \
                 patch.object(engine, 'REPORT_DIR', Path(tmp)), \
                 patch.object(engine, 'build_research_queries', return_value=['topic']), \
                 patch.object(engine, 'web_search', return_value=found), \
                 patch.object(engine, 'extract_url', return_value=extracted), \
                 patch.object(engine, 'ollama_chat', return_value=draft) as model:
                result = engine.deep_research('Resident AI')
                saved = Path(result['report_path']).read_text()
                return result, saved, model.call_count

    def test_empty_search_never_calls_synthesis(self):
        result, saved, calls = self.run_research([], draft='Invented findings [1].')
        self.assertEqual(calls, 0)
        self.assertEqual(result['evidence_status'], 'no_sources')
        self.assertNotIn('Invented findings', saved)
        self.assertIn('Research incomplete', saved)

    def test_invalid_urls_and_empty_evidence_do_not_count(self):
        for item in ({'url': 'file:///etc/passwd', 'title': 'Local'},
                     {'url': 'https://example.org', 'title': 'Empty', 'snippet': ''}):
            result, _, calls = self.run_research([item], extracted='')
            self.assertEqual(result['sources'], [])
            self.assertEqual(calls, 0)

    def test_failed_search_still_saves_honest_failure(self):
        with patch.object(engine, 'web_search', side_effect=RuntimeError('offline')):
            # Use the ordinary empty-result path to check persistence separately;
            # exercise the search exception path without the helper's search mock.
            with tempfile.TemporaryDirectory() as tmp, \
                 patch.object(engine, 'ensure_storage'), \
                 patch.object(engine, 'REPORT_DIR', Path(tmp)), \
                 patch.object(engine, 'build_research_queries', return_value=['topic']), \
                 patch.object(engine, 'ollama_chat') as model:
                result = engine.deep_research('topic')
                self.assertEqual(result['evidence_status'], 'no_sources')
                self.assertTrue(Path(result['report_path']).is_file())
                model.assert_not_called()

    def test_snippet_fallback_is_labeled_and_linked(self):
        source = {'url': 'https://example.org/paper', 'title': 'Paper', 'snippet': 'Snippet'}
        result, saved, calls = self.run_research([source, source], extracted='')
        self.assertEqual(len(result['sources']), 1)
        self.assertEqual(result['sources'][0]['evidence_kind'], 'search_snippet')
        self.assertIn('https://example.org/paper', saved)
        self.assertIn('search_snippet', saved)
        self.assertEqual(calls, 1)

    def test_fabricated_missing_or_placeholder_citations_are_withheld(self):
        source = {'url': 'https://example.org', 'title': 'Paper', 'snippet': 'Evidence'}
        for draft in ('Invented [7]', 'Invented [0]', 'Invented without citations',
                      'Invented [1]\n[1] Source Material: memory capabilities'):
            result, saved, _ = self.run_research([source], draft=draft)
            self.assertEqual(result['evidence_status'], 'citation_validation_failed')
            self.assertNotIn('Invented', saved)

    def test_model_outage_preserves_sources(self):
        result, saved, _ = self.run_research(
            [{'url': 'https://example.org', 'title': 'Paper'}], draft=None)
        self.assertEqual(result['evidence_status'], 'synthesis_unavailable')
        self.assertIn('https://example.org', saved)


if __name__ == '__main__':
    unittest.main()
