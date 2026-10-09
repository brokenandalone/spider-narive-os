"""Native port of Webbie Author Studio: regression tests with disposable libraries."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'author'))
sys.path.insert(0, str(ROOT / 'the-web/shell'))
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from store import AuthorStore
from web_features import AuthorToolkit
from webbie_panel import WebbiePanel

APP = QApplication.instance() or QApplication([])


class AuthorWebsitePortTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.store = AuthorStore(self.folder.name)
        self.book = self.store.create_book('BROKEN CITY')
        self.chapter = self.store.create_chapter(
            self.book, 'EVERYBODY ELSE’S CHILDREN', 'Shayna visited the city.'
        )
        self.store.save_canon(self.book, 'The City can only use what you bring.')

    def tearDown(self):
        self.store.close()
        self.folder.cleanup()

    def test_database_schema_is_additive_and_imports_still_work(self):
        identity = self.store.chapter(self.chapter)['id']
        canon = self.store.canon(self.book)
        entry = self.store.add_story_entry(self.book, 'Character', 'Shayna Kinser', 'Case manager')
        reference = self.store.add_reference(self.book, 'Master Timeline', 'Timeline', '3:13')
        self.assertEqual(self.store.story_entries(self.book)[0]['id'], entry)
        self.assertEqual(self.store.references(self.book)[0]['id'], reference)
        self.assertEqual(self.store.chapter(self.chapter)['id'], identity)
        self.assertEqual(self.store.canon(self.book), canon)
        self.store.close()
        self.store = AuthorStore(self.folder.name)
        self.assertEqual(self.store.story_entries(self.book)[0]['title'], 'Shayna Kinser')
        self.assertEqual(self.store.chapter(self.chapter)['content'], 'Shayna visited the city.')

    def test_cross_book_search_and_literal_wildcards(self):
        other = self.store.create_book('No Safe Distance')
        self.store.create_chapter(other, 'Opening', 'Unbroken saw Shayna.')
        self.store.add_story_entry(self.book, 'Rule', 'No new suffering', 'The City can only use what you bring.')
        self.store.add_reference(self.book, '3:13 Receipt', 'Clue', 'gas station')
        results = self.store.search_library('Shayna')
        self.assertEqual({x['kind'] for x in results}, {'chapter'})
        self.assertEqual(len(results), 2)
        self.assertEqual(len(self.store.search_library('Shayna', book_id=self.book)), 1)
        self.assertEqual(self.store.search_library('%'), [])
        self.assertIn('story', {hit['kind'] for hit in self.store.search_library('city')})
        self.assertEqual(self.store.word_count(self.book), 4)

    def test_story_and_references_edit_saved_without_touching_manuscript(self):
        story = self.store.add_story_entry(self.book, 'Rule', '3:13')
        self.store.save_story_entry(story, 'Timeline', '3:13 Clue', 'Original receipt')
        ref = self.store.add_reference(self.book, 'Book One Bible')
        self.store.save_reference(ref, 'Book One Bible', 'Reference', 'All houses', 'bible.docx')
        self.assertEqual(self.store.story_entries(self.book)[0]['category'], 'Timeline')
        self.assertEqual(self.store.references(self.book)[0]['source_name'], 'bible.docx')
        self.assertEqual(self.store.chapter(self.chapter)['content'], 'Shayna visited the city.')

    def test_native_author_widget_reads_existing_books(self):
        spec = importlib.util.spec_from_file_location('author_native_under_test', ROOT / 'author/main.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        window = module.AuthorWindow(self.folder.name)
        window.books.setCurrentRow(0)
        window.chapters.setCurrentRow(0)
        self.assertEqual(window.toolkit.book_id, self.book)
        self.assertIn('Shayna visited', window.editor.toPlainText())
        self.assertIn('BROKEN CITY', window.webbie_context())
        self.assertNotIn('Shayna visited', window.webbie_context())
        window.toolkit.search_input.setText('Shayna')
        window.toolkit.find()
        self.assertEqual(window.toolkit.search_results.count(), 1)
        self.assertTrue(window.close())

    def test_webbie_writer_title_is_confined_to_author_bay(self):
        panel = WebbiePanel(ROOT)
        panel.timer.stop()
        panel.set_workspace_context('Author', mode='Author Editor', summary='BROKEN CITY')
        self.assertIn('Address: Writer', panel.context.text())
        self.assertIn('Address the user as Writer', panel.prepare_request('Review chapter'))
        panel.set_workspace_context('School', mode='School Tutor', summary='SOC-112')
        self.assertNotIn('Address: Writer', panel.context.text())
        self.assertNotIn('Address the user as Writer', panel.prepare_request('Help me study'))
        panel.close()

    def test_global_webbie_modes_cover_all_web_workspaces(self):
        # Parse source to avoid launching a real desktop or changing user state.
        import ast
        shell = ast.parse((ROOT / 'the-web/shell/main.py').read_text())
        catalog = ast.parse((ROOT / 'the-web/shell/app_catalog.py').read_text())
        cls = next(node for node in shell.body if isinstance(node, ast.ClassDef) and node.name == 'TheWeb')
        mode_expr = next(node.value for node in cls.body if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'WEBBIE_MODES' for t in node.targets))
        mode_map = ast.literal_eval(mode_expr)
        workspaces = next(node.value for node in catalog.body if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'WORKSPACES' for t in node.targets))
        self.assertEqual(set(mode_map), set(ast.literal_eval(workspaces)))
        self.assertEqual(mode_map['author'], 'Author Editor')
        self.assertIn('toggle_webbie_assistant', (ROOT / 'the-web/shell/main.py').read_text())


if __name__ == '__main__':
    unittest.main()
