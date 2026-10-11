"""DOCX import regressions use disposable files and a fresh Author database."""
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'author'))
from manuscript_import import parse_docx
from store import AuthorStore

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'


def paragraph(text, heading=False):
    style = '<w:pPr><w:pStyle w:val="Heading1"/></w:pPr>' if heading else ''
    return f'<w:p>{style}<w:r><w:t>{escape(text)}</w:t></w:r></w:p>'


def write_docx(path, paragraphs, table_text=None):
    blocks = [paragraph(text, heading) for text, heading in paragraphs]
    if table_text is not None:
        blocks.append(
            '<w:tbl><w:tr><w:tc>' + paragraph(table_text) +
            '</w:tc></w:tr></w:tbl>'
        )
    xml = (
        '<?xml version="1.0" encoding="utf-8"?>'
        f'<w:document xmlns:w="{W}"><w:body>' +
        ''.join(blocks) + '</w:body></w:document>'
    )
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr('[Content_Types].xml', '<Types/>')
        archive.writestr('word/document.xml', xml)


class DocxImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = AuthorStore(self.root / 'library')
        self.existing_book = self.store.create_book('Existing manuscript')
        self.existing_chapter = self.store.create_chapter(
            self.existing_book, 'Original', 'Keep my original writing.'
        )
        self.store.save_canon(self.existing_book, 'Established canon')

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_preview_split_front_matter_and_table_without_changing_source(self):
        path = self.root / 'Broken City.docx'
        write_docx(path, [
            ('Dedication', False),
            ('Chapter One', True),
            ('Meet me at Mercer & Ninth.', False),
            ('Chapter Two', True),
        ], table_text='Evidence: 3:13')
        before = path.read_bytes()
        preview = parse_docx(path)
        self.assertEqual(preview.title, 'Broken City')
        self.assertEqual(preview.chapters, (
            ('Front Matter', 'Dedication'),
            ('Chapter One', 'Meet me at Mercer & Ninth.'),
            ('Chapter Two', 'Evidence: 3:13')
        ))
        self.assertEqual(path.read_bytes(), before)

        new_book = self.store.import_docx(path, preview.fingerprint)
        chapters = self.store.chapters(new_book)
        self.assertEqual([row['title'] for row in chapters],
                         ['Front Matter', 'Chapter One', 'Chapter Two'])
        self.assertEqual(chapters[-1]['content'], 'Evidence: 3:13')
        self.assertEqual(self.store.chapter(self.existing_chapter)['content'],
                         'Keep my original writing.')
        self.assertEqual(self.store.canon(self.existing_book), 'Established canon')
        self.assertEqual(path.read_bytes(), before)

    def test_unstyled_docx_imported_as_single_complete_chapter(self):
        path = self.root / 'Draft.docx'
        write_docx(path, [('First paragraph.', False),
                          ('Second paragraph.', False)])
        preview = parse_docx(path)
        self.assertEqual(preview.chapters,
                         (('Manuscript', 'First paragraph.\nSecond paragraph.'),))
        new_book = self.store.import_docx(path, preview.fingerprint)
        self.assertEqual(len(self.store.chapters(new_book)), 1)

    def test_duplicate_is_rejected_without_creating_books(self):
        path = self.root / 'Draft.docx'
        write_docx(path, [('Keep.', False)])
        first = self.store.import_docx(path)
        count = len(self.store.books())
        with self.assertRaisesRegex(ValueError, 'already imported'):
            self.store.import_docx(path)
        self.assertEqual(len(self.store.books()), count)
        self.assertEqual(self.store.chapters(first)[0]['content'], 'Keep.')

    def test_changed_file_after_preview_is_refused(self):
        path = self.root / 'Draft.docx'
        write_docx(path, [('Version One', False)])
        preview = parse_docx(path)
        write_docx(path, [('Version Two', False)])
        with self.assertRaisesRegex(ValueError, 'changed since preview'):
            self.store.import_docx(path, preview.fingerprint)
        self.assertEqual(len(self.store.books()), 1)

    def test_invalid_word_document_rejected_without_database_changes(self):
        path = self.root / 'Bad.docx'
        path.write_text('Not a Word document')
        with self.assertRaises(ValueError):
            self.store.import_docx(path)
        self.assertEqual(len(self.store.books()), 1)


if __name__ == '__main__':
    unittest.main()
