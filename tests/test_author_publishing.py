"""Portable export smoke tests on a disposable book, never on user manuscripts."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'author'))
from PyQt5.QtWidgets import QApplication
from store import AuthorStore
from publishing import export_epub, export_pdf

APP = QApplication.instance() or QApplication([])


class PublishingTests(unittest.TestCase):
    def test_epub_three_is_valid_and_exclusive(self):
        with tempfile.TemporaryDirectory() as folder:
            store = AuthorStore(folder)
            book = store.create_book('Broken City & The River')
            chapter = store.create_chapter(book, 'Chapter <One>', 'The sign said 3:13.\n\nNobody remembered.')
            filename = Path(folder) / 'novel.epub'
            export_epub(store, book, filename)
            with zipfile.ZipFile(filename) as epub:
                self.assertEqual(epub.namelist()[0], 'mimetype')
                self.assertEqual(epub.read('mimetype'), b'application/epub+zip')
                ET.fromstring(epub.read('OEBPS/content.opf'))
                ET.fromstring(epub.read('OEBPS/nav.xhtml'))
                body = epub.read('OEBPS/c1.xhtml').decode()
                self.assertIn('Chapter &lt;One&gt;', body)
                self.assertIn('Nobody remembered.', body)
            with self.assertRaises(FileExistsError):
                export_epub(store, book, filename)
            self.assertEqual(store.chapter(chapter)['content'], 'The sign said 3:13.\n\nNobody remembered.')
            store.close()

    def test_pdf_is_local_selectable_document_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as folder:
            store = AuthorStore(folder)
            book = store.create_book('Broken City')
            store.create_chapter(book, 'Chapter One', 'The street remembers.')
            filename = Path(folder) / 'novel.pdf'
            export_pdf(store, book, filename)
            self.assertTrue(filename.read_bytes().startswith(b'%PDF-'))
            self.assertGreater(filename.stat().st_size, 500)
            before = filename.read_bytes()
            with self.assertRaises(FileExistsError):
                export_pdf(store, book, filename)
            self.assertEqual(filename.read_bytes(), before)
            store.close()


if __name__ == '__main__':
    unittest.main()
