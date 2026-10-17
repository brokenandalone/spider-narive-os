"""Saved Author review history and chapter-navigation regressions.

Disposable library only. Never read or write the owner's actual manuscripts.
"""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "author"))
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from store import AuthorStore
from review_history import ReviewHistory
from web_features import AuthorToolkit

APP = QApplication.instance() or QApplication([])


class SavedReviewsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.store = AuthorStore(self.directory.name)
        self.book = self.store.create_book("Broken City")
        self.ch1 = self.store.create_chapter(
            self.book, "Mercer & Ninth", "The clock struck 3:13.")
        self.ch2 = self.store.create_chapter(
            self.book, "Platform Six", "There was no train.")
        self.history = ReviewHistory(self.store)
        self.canon = "The City uses what you bring."

    def tearDown(self):
        self.store.close()
        self.directory.cleanup()

    def test_saved_book_review_reopens_and_is_marked_outdated_after_edit(self):
        chapters = [dict(row) for row in self.store.chapters(self.book)]
        manifest = self.history.manifest(self.book, chapters, self.canon)
        self.store.save_canon(self.book, self.canon)
        # A completed review never changes chapter text or creates snapshots.
        saved = self.history.save(
            self.book, "book", "deep", "Whole book editorial report.", manifest)
        self.assertEqual(self.store.snapshots(self.ch1), [])
        self.assertEqual(self.store.snapshots(self.ch2), [])
        self.assertEqual(self.history.get(saved, self.book)["report"],
                         "Whole book editorial report.")
        self.assertTrue(self.history.is_current(self.history.get(saved, self.book)))
        self.store.close()
        self.store = AuthorStore(self.directory.name)
        self.history = ReviewHistory(self.store)
        self.assertEqual([row["id"] for row in self.history.list(self.book)], [saved])
        self.store.save(self.ch2, "The train really arrived.")
        self.assertFalse(self.history.is_current(self.history.get(saved, self.book)))
        self.assertEqual(self.history.get(saved, self.book)["report"],
                         "Whole book editorial report.")
        self.assertEqual(len(self.store.snapshots(self.ch2)), 1)

    def test_chapter_review_freshness_ignores_unrelated_chapter_edits(self):
        self.store.save_canon(self.book, self.canon)
        manifest = self.history.manifest(
            self.book, [dict(self.store.chapter(self.ch1))], self.canon)
        report_id = self.history.save(
            self.book, "chapter", "quick", "Chapter feedback.", manifest)
        self.store.save(self.ch2, "Changed unrelated chapter")
        self.assertTrue(self.history.is_current(self.history.get(report_id, self.book)))
        self.store.save_canon(self.book, "Canon changed")
        self.assertFalse(self.history.is_current(self.history.get(report_id, self.book)))

    def test_history_navigation_uses_chapter_ids_not_guessed_titles(self):
        self.store.save_canon(self.book, self.canon)
        manifest = self.history.manifest(
            self.book, [dict(row) for row in self.store.chapters(self.book)], self.canon)
        report_id = self.history.save(
            self.book, "book", "quick", "Report from the whole book.", manifest)
        widget = AuthorToolkit(self.store, lambda: None)
        hits = []
        widget.jumpRequested.connect(hits.append)
        try:
            widget.set_book(self.book)
            widget.refresh_review_history(select_id=report_id)
            self.assertEqual(widget.review_chapters.count(), 2)
            self.assertEqual(widget.review_result.toPlainText(),
                             "Report from the whole book.")
            self.assertIn("unchanged", widget.review_freshness.text())
            widget.jump_to_reviewed_chapter(widget.review_chapters.item(1))
            self.assertEqual(hits[0], {
                "book_id": self.book, "kind": "chapter", "item_id": self.ch2
            })
            self.store.save(self.ch2, "Chapter updated after review")
            widget.open_saved_review(widget.saved_reviews.currentIndex())
            self.assertIn("OUTDATED", widget.review_freshness.text())
            self.assertFalse(widget.reader.isRunning())
            self.assertIsNone(widget.review_worker)
        finally:
            widget.shutdown()
            widget.close()

    def test_history_rejects_cross_book_and_partial_chapter_report(self):
        other = self.store.create_book("No Safe Distance")
        target = self.store.create_chapter(other, "Opening", "Different manuscript")
        with self.assertRaises(ValueError):
            self.history.manifest(self.book, [dict(self.store.chapter(target))], "")
        manifest = self.history.manifest(
            self.book, [dict(row) for row in self.store.chapters(self.book)], "")
        with self.assertRaises(ValueError):
            self.history.save(self.book, "chapter", "quick", "Bad report", manifest)
        self.assertEqual(self.history.list(self.book), [])

    def test_manifest_contains_hashes_not_private_manuscript_text(self):
        manifest = self.history.manifest(
            self.book, [dict(self.store.chapter(self.ch1))], self.canon)
        from json import dumps
        self.assertNotIn("clock struck", dumps(manifest))
        self.assertEqual(len(manifest["chapters"][0]["sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
