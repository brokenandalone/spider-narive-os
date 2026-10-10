"""Regression tests for opt-in full manuscript review and Webbie narration."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "author"))
from review_engine import ReviewEngine, ReviewCancelled, split_exact, preferred_model
from voice_reader import speech_segments, WebbieReader
from store import AuthorStore

from PyQt5.QtWidgets import QApplication
APP = QApplication.instance() or QApplication([])


class AuthorExtendedReviewTests(unittest.TestCase):
    def test_every_character_reaches_a_segment(self):
        sample = ("The Hollow Man arrived at 3:13.\n" * 700) + "THE END"
        for limit in (64, 300, 3100, 6100):
            segments = split_exact(sample, limit)
            self.assertEqual("".join(segments), sample)
            self.assertTrue(all(0 < len(part) <= limit for part in segments))

    def test_quick_book_review_covers_every_chapter_without_database_write(self):
        with tempfile.TemporaryDirectory() as folder:
            store = AuthorStore(folder)
            book = store.create_book("Broken City")
            one = store.create_chapter(book, "Mercer & Ninth", "S" * 9500)
            two = store.create_chapter(book, "Platform Six", "T" * 7000)
            original = [(row["id"], row["content"]) for row in store.chapters(book)]
            calls = []
            def fake_model(prompt, tokens):
                calls.append((prompt, tokens))
                return "Potential issue: chapter and segment should be checked."
            engine = ReviewEngine(ask=fake_model)
            report = engine.review(
                [dict(c) for c in store.chapters(book)], "Broken City",
                scope="book", depth="quick", canon=store.canon(book))
            self.assertIn("Mercer & Ninth", report)
            self.assertIn("Platform Six", report)
            self.assertIn("4 source segments", report)
            self.assertTrue(any("S" * 1000 in prompt for prompt, _ in calls))
            self.assertTrue(any("T" * 1000 in prompt for prompt, _ in calls))
            self.assertEqual(original, [(c["id"], c["content"]) for c in store.chapters(book)])
            self.assertEqual(store.snapshots(one), [])
            self.assertEqual(store.snapshots(two), [])
            store.close()

    def test_deep_chapter_review_does_not_include_other_chapters(self):
        calls = []
        def fake_model(prompt, tokens):
            calls.append(prompt)
            return "No confirmed issue."
        result = ReviewEngine(ask=fake_model).review(
            [{"title": "Chapter 7", "content": "X" * 7200}],
            "Book", scope="chapter", depth="deep")
        self.assertIn("Deep Chapter Review", result)
        self.assertIn("3 source segments", result)
        self.assertEqual(sum("[MANUSCRIPT BEGINS]" in call for call in calls), 3)

    def test_cancel_before_review_makes_zero_model_calls(self):
        cancelled = threading.Event()
        cancelled.set()
        def forbidden(*args):
            self.fail("No model call expected")
        with self.assertRaises(ReviewCancelled):
            ReviewEngine(ask=forbidden).review(
                [{"title": "First", "content": "Hello"}], "Book",
                cancelled=cancelled)

    def test_empty_manuscripts_are_rejected_without_model_calls(self):
        with self.assertRaises(ValueError):
            ReviewEngine(ask=lambda *_: self.fail("No model call")).review(
                [{"title": "Empty", "content": ""}], "Book")

    def test_narrator_uses_same_webbie_voice_module(self):
        voice_script = ROOT / "webbie/voice/tts.py"
        self.assertTrue(voice_script.is_file())
        narrator = WebbieReader(voice_script=voice_script)
        self.assertTrue(narrator.available())
        self.assertFalse(narrator.isRunning())
        segments = speech_segments("First line.\n" + "A" * 1000)
        self.assertGreater(len(segments), 2)
        self.assertEqual("".join(s for s in segments if s.startswith("A")).count("A"), 1000)
        narrator.stop()

    def test_review_controls_do_not_start_automatically(self):
        from web_features import AuthorToolkit
        with tempfile.TemporaryDirectory() as folder:
            store = AuthorStore(folder)
            widget = AuthorToolkit(store, lambda: None)
            self.assertIsNone(widget.review_worker)
            self.assertFalse(widget.reader.isRunning())
            self.assertIn("entire chapter", widget.review_chapter_button.text())
            self.assertIn("entire book", widget.review_book_button.text())
            self.assertTrue(widget.shutdown())
            widget.close()
            store.close()


if __name__ == "__main__":
    unittest.main()
