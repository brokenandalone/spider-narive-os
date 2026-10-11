"""Research V3: genuine source transparency, voice gates, safe handoff."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


quality = load("forage_quality_v3", "forage/research_quality.py")
export = load("forage_export_v3", "forage/workspace_export.py")
bridge = load("forage_webbie_v3", "webbie/agent/forage_research_bridge.py")
engine = load("forage_engine_v3", "forage/engine.py")


class QualityTests(unittest.TestCase):
    def test_metadata_is_transparent_not_truth_scoring(self):
        sources = [
            {"url": "https://example.org/a", "content": "full evidence", "evidence_kind": "page_text", "engine": "searxng"},
            {"url": "https://example.org/b", "content": "brief", "evidence_kind": "search_snippet", "engine": "ddgs"},
        ]
        result = quality.source_summary(sources)
        self.assertEqual(result["source_count"], 2)
        self.assertEqual(result["page_text_count"], 1)
        self.assertEqual(result["snippet_count"], 1)
        self.assertEqual(result["unique_host_count"], 1)
        self.assertTrue(result["warnings"])
        self.assertNotIn("score", result)
        self.assertEqual(len(result["source_details"][0]["sha256"]), 64)
        self.assertEqual(quality.canonical_url("https://EXAMPLE.org/study/#page1"),
                         "https://example.org/study")

    def test_out_of_range_and_uncited_long_claims_flagged(self):
        self.assertTrue(quality.citation_audit("Supported idea [1].", 1)["valid"])
        self.assertFalse(quality.citation_audit("Fake reference [8].", 1)["valid"])
        result = quality.citation_audit("A substantive paragraph " * 9, 1)
        self.assertFalse(result["valid"])
        self.assertTrue(result["uncited_substantive_paragraphs"])

    def test_no_evidence_is_explicit(self):
        r = quality.source_summary([])
        self.assertEqual(r["page_text_count"], 0)
        self.assertIn("No retrievable evidence", r["warnings"][0])


class DeepResearchModeTests(unittest.TestCase):
    def test_intensive_mode_bounds_search_and_archives_audit(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(engine, "REPORT_DIR", Path(tmp)), \
             patch.object(engine, "ensure_storage"), \
             patch.object(engine, "build_research_queries", return_value=["one", "two", "three", "four"]) as plan, \
             patch.object(engine, "web_search", return_value=[
                 {"url": "https://example.org/paper", "title": "Paper", "snippet": "brief",
                  "engine": "searxng"}
             ]) as search, \
             patch.object(engine, "extract_url", return_value="Document full text"), \
             patch.object(engine, "ollama_chat", return_value="Supported result [1]."):
            result = engine.deep_research("Test finding", depth="intensive", focus="academic")
            self.assertEqual(result["depth"], "intensive")
            self.assertEqual(result["focus"], "academic")
            self.assertEqual(len(result["queries"]), 6)
            self.assertEqual(search.call_count, 6)
            self.assertEqual(result["quality_audit"]["page_text_count"], 1)
            self.assertTrue(result["citation_audit"]["valid"])
            self.assertIn("## Source transparency", Path(result["report_path"]).read_text())
            payload = json.loads(Path(result["sources_path"]).read_text())
            self.assertEqual(payload["research_lens"], "academic")
            self.assertEqual(payload["quality_audit"]["page_text_count"], 1)
            self.assertIn("citation_audit", payload)
            self.assertTrue(plan.called)

    def test_bad_depth_lens_and_overlong_topic_rejected_before_network(self):
        for opts in ({"depth": "infinite"}, {"focus": "filesystem"},
                     {"topic": "x" * 601}):
            args = {"topic": "testing"}
            args.update(opts)
            with self.assertRaises(ValueError):
                engine.deep_research(**args)

    def test_snippets_marked_provisional(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(engine, "REPORT_DIR", Path(tmp)), \
             patch.object(engine, "ensure_storage"), \
             patch.object(engine, "build_research_queries", return_value=["one"]), \
             patch.object(engine, "web_search", return_value=[
                 {"url": "https://example.org/paper", "title": "Paper", "snippet": "Only a search snippet"}
             ]), \
             patch.object(engine, "extract_url", return_value=""), \
             patch.object(engine, "ollama_chat", return_value="Provisional result [1]."):
            result = engine.deep_research("Question", depth="quick")
            self.assertEqual(result["sources"][0]["evidence_kind"], "search_snippet")
            self.assertTrue(result["quality_audit"]["warnings"])


class WebbieBridgeTests(unittest.TestCase):
    def test_explicit_phrase_and_speaker_proof_required(self):
        self.assertEqual(bridge.voice_research_request(
            "research community recovery with deep forage"), ("open", "community recovery"))
        self.assertIsNone(bridge.voice_research_request("just keep researching forever"))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            script = root / "forage/deep-forage/deep_forage.py"
            script.parent.mkdir(parents=True)
            script.write_text("pass\n")
            launch = Mock()
            for identity, sleeping in ((False, False), (True, True)):
                self.assertIsNone(bridge.handle_verified_research(
                    "start deep forage research about addiction",
                    speaker_verified=identity, asleep=sleeping,
                    root=root, launcher=launch))
            launch.assert_not_called()
            text = bridge.handle_verified_research(
                "start deep forage research about addiction",
                speaker_verified=True, root=root, launcher=launch)
            self.assertIn("Select Begin Research", text)
            args = launch.call_args.args[0]
            self.assertEqual(args[2], "addiction")
            self.assertNotIn("sh", args[0])

    def test_readonly_history_returns_no_data_when_unverified(self):
        self.assertIsNone(bridge.handle_verified_research(
            "show deep forage research history", speaker_verified=False))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertIn("unavailable", bridge.handle_verified_research(
                "show deep forage research history", speaker_verified=True, root=root))


class ManualExportTests(unittest.TestCase):
    def test_explicit_workspaces_no_overwrite_or_outside_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            research = base / "research"; research.mkdir()
            study = base / "Study"; study.mkdir()
            paper = research / "article.md"; paper.write_text("# Evidence\n[1] Source")
            result = export.export_report(paper, "study", study, research_root=research)
            self.assertEqual(Path(result).read_text(), paper.read_text())
            self.assertEqual(Path(result).stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                export.export_report(paper, "study", study, research_root=research)
            with self.assertRaises(ValueError):
                export.export_report(paper, "os", study, research_root=research)
            outside = base / "secret.md"; outside.write_text("Secret")
            with self.assertRaises(ValueError):
                export.export_report(outside, "author", study, research_root=research)
            symlink = research / "link.md"; symlink.symlink_to(outside)
            with self.assertRaises(ValueError):
                export.export_report(symlink, "study", study, research_root=research)


if __name__ == "__main__":
    unittest.main()
