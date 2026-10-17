"""Evidence queue contract tests: no invented citations, private storage."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "webbie/brain/research_agenda.py"
spec = importlib.util.spec_from_file_location("research_agenda", PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class ResearchAgendaTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.root = Path(self.dir.name)
        self.store = mod.ResearchAgenda(self.root / "private/queue.json")

    def test_queue_and_followup_are_not_claimed_as_research(self):
        entry = self.store.add("What makes voice recognition resistant to TV audio?")
        self.assertEqual(entry["status"], "queued")
        self.assertEqual(entry["sources"], [])
        self.assertEqual(self.store.next_question()["id"], entry["id"])
        self.store.add_followup(entry["id"], "How does it handle interruptions?")
        self.store.edit(entry["id"], status="needs-review",
                        finding="Preliminary hypothesis", uncertainty="No live test yet")
        saved = self.store.read()[0]
        self.assertEqual(saved["followups"], ["How does it handle interruptions?"])
        self.assertFalse(saved["sources"])
        self.assertIsNone(self.store.next_question())
        self.assertEqual(self.store.path.stat().st_mode & 0o777, 0o600)

    def test_research_url_requires_https_and_is_initially_unverified(self):
        entry = self.store.add("Evaluate ASR latency")
        for url in ("http://example.com", "file:///etc/passwd",
                    "https://user:secret@example.com", "javascript:alert(1)"):
            with self.assertRaises(ValueError):
                self.store.add_source(entry["id"], url)
        self.store.add_source(entry["id"], "https://example.org/study", "ASR paper")
        record = self.store.read()[0]
        self.assertEqual(record["sources"][0]["title"], "ASR paper")
        self.assertFalse(record["sources"][0]["reviewed"])
        self.store.add_source(entry["id"], "https://example.org/study", "Duplicate")
        self.assertEqual(len(self.store.read()[0]["sources"]), 1)

    def test_symlink_and_invalid_state_are_rejected(self):
        self.store.add("Paper review")
        symlink = self.root / "linked.json"
        symlink.symlink_to(self.store.path)
        with self.assertRaises(OSError):
            mod.ResearchAgenda(symlink).read()
        with self.assertRaises(ValueError):
            self.store.edit(self.store.read()[0]["id"], status="unverified")

    def test_question_text_is_local_only(self):
        data = self.store.add("My private research topic")
        self.assertFalse((ROOT / "webbie/brain/research-agenda.json").exists())
        self.assertIn("My private research topic", self.store.read()[0]["question"])


if __name__ == "__main__":
    unittest.main()
