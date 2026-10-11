"""Master Canon regression tests; synthetic stories and disposable databases only."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'author'))

from store import AuthorStore
from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox
from master_canon_widget import ClaimDialog, MasterCanonWidget

APP = QApplication.instance() or QApplication([])


class MasterCanonStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = AuthorStore(self.tmp.name)
        self.first = self.store.create_book('The City')
        self.second = self.store.create_book('The Road')
        self.ch1 = self.store.create_chapter(
            self.first, 'Night One', 'The sign read 3:13. Mira returned.'
        )
        self.ch2 = self.store.create_chapter(
            self.second, 'Night Two', 'The sign read 4:13. Nobody knew why.'
        )
        self.mira = self.store.atlas.add_entity('Mira', 'Character')

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_new_claim_stays_proposed_and_never_modifies_prose(self):
        original = self.store.chapter(self.ch1)['content']
        cid = self.store.master_canon.add(
            'Clock clue', 'The clock is important.', book_id=self.first,
            chapter_id=self.ch1, entity_id=self.mira,
            fact_key='clock-clue', category='Object',
            source_quote='The sign read 3:13.'
        )
        claim = self.store.master_canon.get(cid)
        self.assertEqual(claim['status'], 'proposed')
        self.assertEqual(claim['source_digest'],
                         self.store.master_canon.claims(book_id=self.first)[0]['source_digest'])
        self.assertEqual(
            self.store.master_canon.evidence_status(claim), 'verified'
        )
        self.assertEqual(self.store.chapter(self.ch1)['content'], original)
        self.assertEqual(self.store.master_canon.audit()['statuses']['established'], 0)
        self.store.close()
        self.store = AuthorStore(self.tmp.name)
        self.assertEqual(self.store.master_canon.get(cid)['title'], 'Clock clue')
        self.assertEqual(self.store.atlas.entities()[0]['name'], 'Mira')

    def test_edits_create_immutable_previous_versions_and_support_supersession(self):
        cid = self.store.master_canon.add(
            'City law', 'First draft law.', category='Rule'
        )
        self.store.master_canon.edit(
            cid, title='City law', statement='Agreed official law.',
            fact_key='city-law', status='established'
        )
        self.store.master_canon.edit(
            cid, title='City law', statement='Agreed official law.',
            fact_key='city-law', status='superseded'
        )
        rows = self.store.master_canon.history(cid)
        self.assertEqual(len(rows), 2)
        self.assertEqual(json.loads(rows[-1]['previous_json'])['status'], 'proposed')
        self.assertEqual(json.loads(rows[0]['previous_json'])['status'], 'established')
        self.assertEqual(self.store.master_canon.get(cid)['status'], 'superseded')
        self.assertEqual(self.store.chapter(self.ch1)['content'],
                         'The sign read 3:13. Mira returned.')

    def test_cross_book_possible_disagreements_only_for_established_same_keys(self):
        for book, statement, status in (
            (self.first, 'Clue occurs at 3:13.', 'established'),
            (self.second, 'Clue occurs at 4:13.', 'established'),
            (self.second, 'A possible third explanation.', 'proposed'),
        ):
            self.store.master_canon.add(
                'Receipt', statement, book_id=book,
                fact_key=' RECEIPT   TIME ', status=status
            )
        report = self.store.master_canon.audit()
        self.assertEqual(report['total'], 3)
        self.assertEqual(report['statuses']['proposed'], 1)
        self.assertEqual(len(report['alerts']), 1)
        self.assertEqual(report['alerts'][0]['kind'], 'possible_disagreement')
        self.assertIn('Possible disagreement', report['alerts'][0]['message'])
        scoped = self.store.master_canon.audit(book_id=self.first, include_all=False)
        self.assertEqual(scoped['total'], 1)
        self.assertEqual(scoped['alerts'], [])

    def test_stale_quote_and_changed_chapter_are_reported(self):
        cid = self.store.master_canon.add(
            'Clue', 'Receipt found', book_id=self.first,
            chapter_id=self.ch1, source_quote='The sign read 3:13.'
        )
        self.store.save(self.ch1, 'Changed intro. The sign read 3:13. Mira returned.')
        self.assertEqual(
            self.store.master_canon.evidence_status(self.store.master_canon.get(cid)),
            'changed-but-quote-present'
        )
        self.assertEqual(len(self.store.master_canon.audit()['alerts']), 1)
        self.store.save(self.ch1, 'Clue was removed from the manuscript.')
        self.assertEqual(
            self.store.master_canon.evidence_status(self.store.master_canon.get(cid)),
            'outdated'
        )

    def test_reject_fabricated_quotes_cross_book_anchors_and_missing_links(self):
        before = len(self.store.master_canon.claims(include_all=True))
        with self.assertRaisesRegex(ValueError, 'exactly'):
            self.store.master_canon.add(
                'Invented', 'Invented', chapter_id=self.ch1,
                source_quote='No one ever said this.'
            )
        with self.assertRaisesRegex(ValueError, 'another book'):
            self.store.master_canon.add(
                'Wrong chapter', 'Nope', book_id=self.first,
                chapter_id=self.ch2
            )
        with self.assertRaisesRegex(ValueError, 'requires'):
            self.store.master_canon.add(
                'No anchor', 'A claim', source_quote='Not anchored'
            )
        with self.assertRaisesRegex(ValueError, 'does not exist'):
            self.store.master_canon.add(
                'Bad entity', 'Nope', entity_id=999999
            )
        with self.assertRaisesRegex(ValueError, 'required'):
            self.store.master_canon.add('', '')
        self.assertEqual(len(self.store.master_canon.claims(include_all=True)),
                         before)

    def test_character_dossiers_and_global_rules_across_books(self):
        global_id = self.store.master_canon.add(
            'World rule', 'An ancient rule.', category='Rule',
            fact_key='world-law'
        )
        self.store.master_canon.add(
            'Mira biography', 'Arrives Tuesday.', book_id=self.first,
            entity_id=self.mira, category='Character'
        )
        self.store.master_canon.add(
            'Mira later', 'Arrives Friday.', book_id=self.second,
            entity_id=self.mira, category='Character'
        )
        first_view = self.store.master_canon.claims(book_id=self.first)
        self.assertEqual({c['title'] for c in first_view},
                         {'World rule', 'Mira biography'})
        dossier = self.store.master_canon.claims(
            include_all=True, entity_id=self.mira
        )
        self.assertEqual(len(dossier), 2)
        self.assertEqual(len(self.store.master_canon.claims(
            query='biography', include_all=True)), 1)
        self.assertIsNone(self.store.master_canon.get(global_id)['book_id'])


class MasterCanonGuiTests(unittest.TestCase):
    def test_dialog_requires_confirmation_before_established_canon(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = AuthorStore(tmp)
            try:
                dialog = ClaimDialog(store)
                try:
                    dialog.title.setText('World rule')
                    dialog.statement.setPlainText('Only approved laws are canon.')
                    dialog.status.setCurrentIndex(
                        dialog.status.findData('established')
                    )
                    with patch.object(
                        QMessageBox, 'question', return_value=QMessageBox.No
                    ):
                        dialog.accept()
                        self.assertNotEqual(dialog.result(), QDialog.Accepted)
                    with patch.object(
                        QMessageBox, 'question', return_value=QMessageBox.Yes
                    ):
                        dialog.accept()
                        self.assertEqual(dialog.result(), QDialog.Accepted)
                finally:
                    dialog.close()
            finally:
                store.close()

    def test_widget_views_global_rule_and_source_navigation(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = AuthorStore(tmp)
            book = store.create_book('Broken City')
            ch = store.create_chapter(
                book, 'First', 'The clock struck 3:13.'
            )
            store.master_canon.add(
                'Official rule', 'A hand-written law.', status='established'
            )
            cid = store.master_canon.add(
                'Source clue', 'Clue text.', book_id=book,
                chapter_id=ch, source_quote='The clock struck 3:13.'
            )
            store.save_canon(book, 'Legacy city notebook text.')
            store.add_story_entry(book, 'Rule', 'Old 3:13 clue', 'Older story notes.')
            widget = MasterCanonWidget(store)
            try:
                widget.set_book(book)
                widget.show_legacy_notes()
                self.assertIn('UNREVIEWED', widget.details.toPlainText())
                self.assertIn('Legacy city notebook text.', widget.details.toPlainText())
                self.assertIn('Older story notes.', widget.details.toPlainText())
                self.assertEqual(store.master_canon.audit()['total'], 2)
                self.assertEqual(widget.table.rowCount(), 2)
                self.assertIn('1 established', widget.summary.text())
                row = next(i for i in range(widget.table.rowCount())
                           if widget.table.item(i, 0).data(0x100) == cid)
                widget.table.selectRow(row)
                received = []
                widget.chapterRequested.connect(lambda *args: received.append(args))
                widget.open_source()
                self.assertEqual(received[0][0], ch)
                self.assertEqual(received[0][1], 'The clock struck 3:13.')
                widget.audit()
                self.assertIn('Claims reviewed: 2',
                              widget.details.toPlainText())
                self.assertEqual(store.chapter(ch)['content'],
                                 'The clock struck 3:13.')
            finally:
                widget.close()
                store.close()


class AuthorWindowCanonTests(unittest.TestCase):
    def test_verified_quote_navigates_across_books_and_never_rewrites_text(self):
        from main import AuthorWindow
        with tempfile.TemporaryDirectory() as tmp:
            initial = AuthorStore(tmp)
            first = initial.create_book('First')
            initial.create_chapter(first, 'Opening', 'First words.')
            second = initial.create_book('Second')
            chapter = initial.create_chapter(
                second, 'Opening', 'The secret is 3:13.'
            )
            claim_id = initial.master_canon.add(
                'Clue', 'Clock law', book_id=second,
                chapter_id=chapter, source_quote='The secret is 3:13.'
            )
            source = initial.master_canon.get(claim_id)
            initial.close()
            window = AuthorWindow(tmp)
            try:
                window.timer.stop()
                window.books.setCurrentRow(0)
                window.chapters.setCurrentRow(0)
                window.jump_to_canon_source(
                    chapter, source['source_quote'], source['source_digest']
                )
                self.assertEqual(window.book_id, second)
                self.assertEqual(window.chapter_id, chapter)
                self.assertEqual(window.editor.textCursor().selectedText(),
                                 'The secret is 3:13.')
                self.assertEqual(window.store.chapter(chapter)['content'],
                                 'The secret is 3:13.')
                window.editor.setPlainText('New text.')
                self.assertTrue(window.flush())
                window.jump_to_canon_source(
                    chapter, source['source_quote'], source['source_digest']
                )
                self.assertIn('outdated', window.status.text())
            finally:
                window.close()


if __name__ == '__main__':
    unittest.main()
