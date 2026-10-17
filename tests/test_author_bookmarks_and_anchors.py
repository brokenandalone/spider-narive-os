"""Author audiobook bookmark and review evidence link regressions.

No audible voice, real user documents, or external language model is accessed.
"""
import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "author"))
from PyQt5.QtWidgets import QApplication
from store import AuthorStore
from narration_bookmarks import NarrationBookmarks, book_fingerprint
from voice_reader import book_reading_plan
from review_history import ReviewHistory
from web_features import AuthorToolkit

APP = QApplication.instance() or QApplication([])


class AudiobookBookmarkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = AuthorStore(self.tmp.name)
        self.book = self.store.create_book("Broken City")
        self.one = self.store.create_chapter(self.book, "First", "Some text.\nMore text.")
        self.two = self.store.create_chapter(self.book, "Second", "A later chapter.")
        self.bookmarks = NarrationBookmarks(self.store)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_bookmark_saved_and_reopened_without_changing_book(self):
        chapters = [dict(row) for row in self.store.chapters(self.book)]
        plan = book_reading_plan(chapters)
        self.assertEqual((plan[0][2], plan[0][3]), (self.one, 0))
        self.assertTrue(any((p[2], p[3]) == (self.two, 1) for p in plan))
        stamp = book_fingerprint(chapters)
        self.bookmarks.save(self.book, stamp, self.two, 1)
        mark = self.bookmarks.get(self.book)
        self.assertTrue(self.bookmarks.is_current(mark, chapters))
        self.assertEqual(mark["chapter_id"], self.two)
        self.assertEqual(mark["section_index"], 1)
        self.assertEqual(self.store.snapshots(self.one), [])
        self.assertEqual(self.store.snapshots(self.two), [])
        self.store.close()
        self.store = AuthorStore(self.tmp.name)
        self.bookmarks = NarrationBookmarks(self.store)
        self.assertEqual(self.bookmarks.get(self.book)["section_index"], 1)
        self.bookmarks.clear(self.book)
        self.assertIsNone(self.bookmarks.get(self.book))

    def test_edit_invalidates_bookmark_even_if_chapter_ids_unchanged(self):
        chapters = [dict(c) for c in self.store.chapters(self.book)]
        self.bookmarks.save(self.book, book_fingerprint(chapters), self.one, 1)
        self.store.save(self.two, "A changed chapter.")
        self.assertFalse(self.bookmarks.is_current(
            self.bookmarks.get(self.book), self.store.chapters(self.book)))

    def test_bookmark_rejects_foreign_chapter_and_bad_positions(self):
        other = self.store.create_book("Different Book")
        foreign = self.store.create_chapter(other, "Elsewhere", "Text")
        fingerprint = book_fingerprint(self.store.chapters(self.book))
        with self.assertRaises(ValueError):
            self.bookmarks.save(self.book, fingerprint, foreign, 1)
        with self.assertRaises(ValueError):
            self.bookmarks.save(self.book, fingerprint, self.one, -1)

    def test_user_requests_resume_not_automatic_and_stale_resume_is_refused(self):
        toolkit = AuthorToolkit(self.store, lambda: None)
        try:
            toolkit.set_book(self.book)
            self.assertFalse(toolkit.reader.isRunning())
            toolkit.resume_book()
            self.assertIn("No saved position", toolkit.bookmark_status.text())
            chapters = [dict(c) for c in self.store.chapters(self.book)]
            self.bookmarks.save(self.book, book_fingerprint(chapters), self.two, 1)
            with patch.object(toolkit.reader, "start_book") as start:
                toolkit.resume_book()
                start.assert_called_once()
                args, kwargs = start.call_args
                self.assertEqual(kwargs["resume"], (self.two, 1))
                self.assertEqual(kwargs["book_id"], self.book)
            self.store.save(self.one, "Changed content")
            with patch.object(toolkit.reader, "start_book") as start:
                toolkit.resume_book()
                start.assert_not_called()
                self.assertIn("outdated", toolkit.bookmark_status.text())
        finally:
            toolkit.shutdown()
            toolkit.close()


class ReviewedSegmentNavigationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        spec = importlib.util.spec_from_file_location(
            "author_main_bookmark_test", ROOT / "author/main.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.window = module.AuthorWindow(self.tmp.name)
        self.book = self.window.store.create_book("Broken City")
        self.text = ("Shayna entered the room. 😀\n" * 260) + "A final 3:13 clue."
        self.chapter = self.window.store.create_chapter(
            self.book, "Mercer & Ninth", self.text)
        self.window.load_books()
        self.window.books.setCurrentRow(0)
        self.window.chapters.setCurrentRow(0)
        self.window.show()
        APP.processEvents()

    def tearDown(self):
        self.window.close()
        APP.processEvents()
        self.tmp.cleanup()

    def test_second_review_segment_highlights_exact_text_with_emoji(self):
        history = ReviewHistory(self.window.store)
        chapters = [dict(c) for c in self.window.store.chapters(self.book)]
        report_id = history.save(
            self.book, "chapter", "quick", "Chapter and segment observations.",
            history.manifest(self.book, chapters, self.window.store.canon(self.book)))
        self.window.toolkit.refresh_review_history(select_id=report_id)
        sections = self.window.toolkit.review_sections
        self.assertGreater(sections.count(), 1)
        item = sections.item(1)
        segment = item.data(256)
        self.window.toolkit.jump_to_review_section(item)
        selected = self.window.editor.textCursor().selectedText().replace("\u2029", "\n")
        self.assertEqual(selected, self.text[segment["start"]:segment["end"]])
        self.assertIn("Selected exact section", self.window.status.text())
        self.assertEqual(self.window.store.snapshots(self.chapter), [])

    def test_stale_review_refuses_old_character_range(self):
        history = ReviewHistory(self.window.store)
        chapters = [dict(c) for c in self.window.store.chapters(self.book)]
        rid = history.save(
            self.book, "chapter", "quick", "Findings",
            history.manifest(self.book, chapters, self.window.store.canon(self.book)))
        section = history.sections_for_report(history.get(rid, self.book))[0]
        self.window.editor.setPlainText("Entirely different text")
        self.window.flush()
        self.window.jump_to_review_segment(section)
        self.assertIn("outdated", self.window.status.text().lower())
        self.assertFalse(self.window.editor.textCursor().hasSelection())


if __name__ == "__main__":
    unittest.main()
