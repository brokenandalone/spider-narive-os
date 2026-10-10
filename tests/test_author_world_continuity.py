"""Private cross-book continuity engine and Author Bay GUI smoke tests."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "author"))
from continuity_engine import ContinuityEngine, ReviewCancelled, gather_sections
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from store import AuthorStore
from web_features import AuthorToolkit

APP = QApplication.instance() or QApplication([])


def two_books():
    return [
        {"id": 12, "title": "First Story", "canon": "",
         "story_bible": [],
         "chapters": [{"id": 101, "title": "Departure",
                       "content": "Mira arrived on Tuesday."}]},
        {"id": 18, "title": "Second Story", "canon": "",
         "story_bible": [],
         "chapters": [{"id": 204, "title": "The Other Account",
                       "content": "Mira arrived on Friday."}]},
    ]


class ContinuityEngineTests(unittest.TestCase):
    def test_all_segments_are_extracted_and_source_quotes_verified(self):
        books = two_books()
        sections = gather_sections(books)
        self.assertEqual(len(sections), 2)
        self.assertEqual([s["text"] for s in sections],
                         ["Mira arrived on Tuesday.", "Mira arrived on Friday."])
        calls = []
        def fake(prompt, tokens):
            calls.append(prompt)
            if "[PAIRS BEGIN]" in prompt:
                return ('{"issues":[{"a":"E1","b":"E2",'
                        '"reason":"These accounts could contradict the same arrival date."}]}')
            day = "Tuesday" if "Mira arrived on Tuesday." in prompt else "Friday"
            return ('{"facts":[{"category":"timeline","subject":"Mira arrival",'
                    '"claim":"Mira arrived on ' + day + '",'
                    '"quote":"Mira arrived on ' + day + '."},'
                    '{"category":"timeline","subject":"Mira arrival",'
                    '"claim":"UNVERIFIED","quote":"Not present in text"}]}')
        report = ContinuityEngine(ask=fake).review(books)
        self.assertIn("Source sections examined: 2", report)
        self.assertIn("Exact source facts accepted: 2", report)
        self.assertIn("Cross-book evidence pairs examined: 1", report)
        self.assertIn("Possible issue 1", report)
        self.assertIn("First Story / Departure", report)
        self.assertIn("Second Story / The Other Account", report)
        self.assertNotIn("UNVERIFIED", report)
        self.assertEqual(len(calls), 3)

    def test_empty_fact_extraction_is_not_claimed_consistent(self):
        result = ContinuityEngine(ask=lambda *_: '{"facts":[]}').review(two_books())
        self.assertIn("no verified extracted facts: 2", result)
        self.assertIn("does not prove consistency", result)

    def test_cancel_between_local_inference_calls(self):
        cancel = threading.Event()
        def fake(prompt, tokens):
            cancel.set()
            return '{"facts":[]}'
        with self.assertRaises(ReviewCancelled):
            ContinuityEngine(ask=fake).review(two_books(), cancelled=cancel)

    def test_source_is_never_missing_a_character_in_segmentation(self):
        books = two_books()
        books[0]["chapters"][0]["content"] = (
            "Mira met the City. " * 900) + "THE END"
        actual = books[0]["chapters"][0]["content"]
        pieces = [s for s in gather_sections(books) if s["book_id"] == 12]
        self.assertEqual("".join(x["text"] for x in pieces), actual)
        self.assertGreater(len(pieces), 2)
        self.assertTrue(all(len(x["text"]) <= 3000 for x in pieces))

    def test_cross_book_only_and_identical_subject_rule(self):
        books = two_books()
        books[1]["chapters"][0]["content"] = "Another person arrived."
        def fake(prompt, tokens):
            if "[PAIRS BEGIN]" in prompt:
                raise AssertionError("No pair should be formed")
            subject = "Mira arrival" if "Mira arrived" in prompt else "Other"
            quote = ("Mira arrived on Tuesday." if subject == "Mira arrival"
                     else "Another person arrived.")
            return ('{"facts":[{"category":"timeline","subject":"'+subject+
                    '","claim":"something","quote":"'+quote+'"}]}')
        report = ContinuityEngine(ask=fake).review(books)
        self.assertIn("Cross-book evidence pairs examined: 0", report)


class ContinuityGuiTests(unittest.TestCase):
    def test_manual_selection_only_and_no_automatic_inference(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = AuthorStore(tmp)
            a = store.create_book("Broken City")
            b = store.create_book("No Safe Distance")
            store.create_chapter(a, "Opening", "First chapter.")
            store.create_chapter(b, "Opening", "Second chapter.")
            with patch("web_features.ContinuityEngine") as model:
                toolkit = AuthorToolkit(store, lambda: None)
                try:
                    toolkit.set_book(a)
                    self.assertEqual(
                        [i.data(Qt.UserRole) for i in
                         toolkit.continuity_books.selectedItems()], [a])
                    toolkit.start_continuity()
                    self.assertIn("at least two books",
                                  toolkit.continuity_status.text())
                    self.assertFalse(model.called)
                    self.assertIsNone(toolkit.continuity_worker)
                    # The snapshot includes user-selected books and their
                    # local canon / chapter data, with no automatic upload.
                    toolkit.continuity_books.item(1).setSelected(True)
                    selection = [i.data(Qt.UserRole) for i in
                                 toolkit.continuity_books.selectedItems()]
                    self.assertEqual(set(selection), {a, b})
                finally:
                    toolkit.shutdown()
                    toolkit.close()
            store.close()


if __name__ == "__main__":
    unittest.main()
