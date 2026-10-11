"""Native Author Project Map tests use disposable SQLite databases only."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'author'))

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from project_map import ProjectMap
from store import AuthorStore

APP = QApplication.instance() or QApplication([])


class ChapterPlanStoreTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.store = AuthorStore(self.folder.name)
        self.book = self.store.create_book('Broken City')
        self.chapter = self.store.create_chapter(
            self.book, 'Mercer & Ninth', 'Shayna entered the city.'
        )

    def tearDown(self):
        self.store.close()
        self.folder.cleanup()

    def test_plan_is_additive_and_never_edits_manuscript(self):
        self.assertEqual(self.store.chapter_plan(self.chapter)['status'], 'draft')
        self.store.save_chapter_plan(
            self.chapter, status='revising', target_words=2500,
            notes='Check receipt timestamp 3:13'
        )
        self.assertEqual(self.store.chapter(self.chapter)['content'],
                         'Shayna entered the city.')
        self.store.close()
        self.store = AuthorStore(self.folder.name)
        self.assertEqual(self.store.chapter_plan(self.chapter)['notes'],
                         'Check receipt timestamp 3:13')
        outline = self.store.project_outline(self.book)
        self.assertEqual(outline[0]['words'], 4)
        self.assertEqual(outline[0]['status'], 'revising')
        self.assertEqual(outline[0]['target_words'], 2500)

    def test_validation_and_missing_chapter_are_safe(self):
        for changes in (
            {'status': 'deleted'},
            {'target_words': -1},
            {'target_words': 200001},
            {'target_words': True},
            {'notes': 'x' * 20001},
        ):
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    self.store.save_chapter_plan(self.chapter, **changes)
        with self.assertRaises(ValueError):
            self.store.save_chapter_plan(999999, status='ready')
        self.assertEqual(self.store.chapter_plan(self.chapter)['status'], 'draft')
        self.assertEqual(self.store.chapter(self.chapter)['content'],
                         'Shayna entered the city.')

    def test_outlines_are_separated_by_book(self):
        other_book = self.store.create_book('The Thirteen-Mile Road')
        other_chapter = self.store.create_chapter(
            other_book, 'Mile One', 'The first road sign.'
        )
        self.store.save_chapter_plan(other_chapter, status='ready')
        self.assertEqual(
            [r['title'] for r in self.store.project_outline(self.book)],
            ['Mercer & Ninth']
        )
        self.assertEqual(
            [r['title'] for r in self.store.project_outline(other_book)],
            ['Mile One']
        )
        with self.assertRaises(ValueError):
            self.store.project_outline(99999)


class ProjectMapUITests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.store = AuthorStore(self.folder.name)
        self.book = self.store.create_book('Broken City')
        self.first = self.store.create_chapter(self.book, 'Opening', 'One two three.')
        self.second = self.store.create_chapter(self.book, 'Clue', 'Receipt says 3:13.')
        self.widget = ProjectMap(self.store)
        self.assertTrue(self.widget.set_book(self.book))

    def tearDown(self):
        self.widget.close()
        self.store.close()
        self.folder.cleanup()

    def test_editorial_changes_persist_and_do_not_change_chapter_text(self):
        self.widget.stage.setCurrentIndex(self.widget.stage.findData('revising'))
        self.widget.target.setValue(1500)
        self.widget.notes.setPlainText('Keep the scene chronological.')
        self.assertTrue(self.widget.dirty)
        self.assertTrue(self.widget.save_pending())
        self.assertFalse(self.widget.dirty)
        self.assertEqual(self.store.chapter_plan(self.first)['status'], 'revising')
        self.assertEqual(self.store.chapter_plan(self.first)['target_words'], 1500)
        self.assertEqual(self.store.chapter(self.first)['content'], 'One two three.')
        self.assertIn('1,500 goal', self.widget._label(
            self.store.project_outline(self.book)[0], 1
        ))

    def test_switching_rows_saves_notes_and_double_click_opens_correct_chapter(self):
        self.widget.notes.setPlainText('First chapter notes.')
        self.widget.chapter_list.setCurrentRow(1)
        self.assertEqual(self.store.chapter_plan(self.first)['notes'],
                         'First chapter notes.')
        found = []
        self.widget.chapterRequested.connect(found.append)
        self.widget.open_chapter()
        self.assertEqual(found, [self.second])
        self.widget.query.setText('Opening')
        self.assertEqual(self.widget.chapter_list.count(), 1)
        self.assertEqual(
            self.widget.chapter_list.item(0).data(Qt.UserRole), self.first
        )

    def test_real_word_counts_refreshed_after_editor_save(self):
        self.store.save(self.first, 'One two three four five.')
        self.widget.refresh()
        self.assertIn('8 words', self.widget.summary.text())
        self.assertEqual(self.widget.rows[0]['words'], 5)

    def test_book_switch_does_not_mix_private_notes(self):
        other = self.store.create_book('No Safe Distance')
        second_book_chapter = self.store.create_chapter(other, 'First', 'Other text.')
        self.widget.notes.setPlainText('Broken City secret.')
        self.widget.set_book(other)
        self.assertEqual(self.store.chapter_plan(self.first)['notes'],
                         'Broken City secret.')
        self.assertEqual(self.store.chapter_plan(second_book_chapter)['notes'], '')
        self.assertNotIn('Broken City secret.', self.widget.notes.toPlainText())


class AuthorWindowProjectMapTests(unittest.TestCase):
    def test_tab_tracks_active_book_and_navigation(self):
        from main import AuthorWindow
        with tempfile.TemporaryDirectory() as folder:
            initial = AuthorStore(folder)
            book = initial.create_book('Broken City')
            chapter = initial.create_chapter(book, 'Opening', 'Old content.')
            initial.close()
            window = AuthorWindow(folder)
            try:
                window.timer.stop()
                window.books.setCurrentRow(0)
                window.chapters.setCurrentRow(0)
                window.editor.setPlainText('New text is saved.')
                window.editor_tabs.setCurrentWidget(window.project_map)
                self.assertEqual(window.project_map.book_id, book)
                self.assertEqual(window.project_map.rows[0]['words'], 4)
                window.project_map.chapterRequested.emit(chapter)
                self.assertIs(window.editor_tabs.currentWidget(), window.editor)
                self.assertEqual(window.chapter_id, chapter)
                self.assertEqual(window.store.chapter(chapter)['content'],
                                 'New text is saved.')
            finally:
                window.close()


if __name__ == '__main__':
    unittest.main()
