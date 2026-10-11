"""Story Atlas tests run offline with synthetic books, never private manuscripts."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'author'))

from PyQt5.QtWidgets import QApplication
from atlas_widget import AtlasWidget
from store import AuthorStore

APP = QApplication.instance() or QApplication([])


class AtlasStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = AuthorStore(self.tmp.name)
        self.a = self.store.create_book('Book One')
        self.b = self.store.create_book('Book Two')
        self.ch1 = self.store.create_chapter(
            self.a, 'Opening', 'Mira arrived on Tuesday. She found the receipt.'
        )
        self.ch2 = self.store.create_chapter(
            self.b, 'Opening', 'Mira arrived on Friday. The clock stopped.'
        )

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_events_preserve_manuscript_and_exact_evidence(self):
        before = self.store.chapter(self.ch1)['content']
        event = self.store.atlas.upsert_event(
            self.a, 'Mira arrives', chapter_id=self.ch1, story_order=1,
            event_key='mira arrival', when_label='Tuesday',
            evidence_quote='Mira arrived on Tuesday.'
        )
        row = self.store.atlas.events(self.a)[0]
        self.assertEqual(row['id'], event)
        self.assertEqual(self.store.atlas.evidence_status(row), 'verified')
        self.assertEqual(self.store.chapter(self.ch1)['content'], before)
        self.assertEqual(self.store.atlas.continuity_audit(self.a)['verified'], 1)

        self.store.save(self.ch1, before + '\nExtra notes.')
        self.assertEqual(
            self.store.atlas.evidence_status(self.store.atlas.events(self.a)[0]),
            'changed-but-quote-present'
        )
        self.store.save(self.ch1, 'The book was rewritten.')
        self.assertEqual(
            self.store.atlas.evidence_status(self.store.atlas.events(self.a)[0]),
            'outdated'
        )
        self.assertEqual(len(self.store.atlas.continuity_audit(self.a)['alerts']), 1)

    def test_invalid_quotes_and_cross_book_sources_refused_transactionally(self):
        with self.assertRaisesRegex(ValueError, 'exactly'):
            self.store.atlas.upsert_event(
                self.a, 'Invalid quote', chapter_id=self.ch1,
                evidence_quote='I made this quote up.'
            )
        with self.assertRaisesRegex(ValueError, 'selected book'):
            self.store.atlas.upsert_event(
                self.a, 'Wrong book', chapter_id=self.ch2,
                evidence_quote='Mira arrived on Friday.'
            )
        with self.assertRaisesRegex(ValueError, 'requires a source'):
            self.store.atlas.upsert_event(
                self.a, 'No source', evidence_quote='Something'
            )
        self.assertEqual(self.store.atlas.events(), [])
        self.assertEqual(self.store.chapter(self.ch1)['content'],
                         'Mira arrived on Tuesday. She found the receipt.')

    def test_manual_cross_book_fact_mismatch_flagged_as_possible(self):
        first = self.store.atlas.upsert_event(
            self.a, 'Mira arrives', chapter_id=self.ch1,
            event_key='Mira arrival', when_label='Tuesday',
            evidence_quote='Mira arrived on Tuesday.'
        )
        second = self.store.atlas.upsert_event(
            self.b, 'Mira arrives', chapter_id=self.ch2,
            event_key='MIRA  ARRIVAL', when_label='Friday',
            evidence_quote='Mira arrived on Friday.'
        )
        scoped = self.store.atlas.continuity_audit(self.a)
        self.assertEqual(len(scoped['alerts']), 0)
        cross = self.store.atlas.continuity_audit()
        self.assertEqual(cross['events'], 2)
        self.assertEqual(cross['verified'], 2)
        self.assertEqual(len(cross['alerts']), 1)
        self.assertEqual(cross['alerts'][0]['type'], 'timeline')
        self.assertEqual(set(cross['alerts'][0]['event_ids']), {first, second})
        self.assertIn('Possible timeline disagreement', cross['alerts'][0]['message'])
        self.assertEqual(self.store.chapter(self.ch2)['content'],
                         'Mira arrived on Friday. The clock stopped.')

    def test_same_key_same_time_is_not_flagged(self):
        for book, chapter in ((self.a, self.ch1), (self.b, self.ch2)):
            self.store.atlas.upsert_event(
                book, 'Mira visit', chapter_id=chapter,
                event_key='visit', when_label='Night 1'
            )
        report = self.store.atlas.continuity_audit()
        self.assertEqual(report['unanchored'], 2)
        self.assertEqual(report['alerts'], [])

    def test_updating_event_does_not_rewrite_chapter(self):
        event = self.store.atlas.upsert_event(self.a, 'First')
        self.store.atlas.upsert_event(
            self.a, 'Edited', event_id=event, story_order=-2,
            details='This may be a flashback.'
        )
        self.assertEqual(self.store.atlas.events(self.a)[0]['title'], 'Edited')
        with self.assertRaises(ValueError):
            self.store.atlas.upsert_event(self.b, 'Wrong book', event_id=event)
        self.assertEqual(self.store.atlas.events(self.a)[0]['details'],
                         'This may be a flashback.')
        self.assertEqual(self.store.chapter(self.ch1)['content'],
                         'Mira arrived on Tuesday. She found the receipt.')

    def test_relationships_and_atlas_data_survive_reopening(self):
        mira = self.store.atlas.add_entity('Mira', 'Character')
        with self.assertRaisesRegex(ValueError, 'already exists'):
            self.store.atlas.add_entity('mira', 'Character')
        clock = self.store.atlas.add_entity('The Clock', 'Object')
        self.store.atlas.add_relationship(
            self.a, mira, clock, 'protects', notes='A mysterious object.'
        )
        with self.assertRaises(ValueError):
            self.store.atlas.add_relationship(self.a, mira, mira, 'self-link')
        self.assertEqual(len(self.store.atlas.relationships(self.a)), 1)
        self.assertEqual(len(self.store.atlas.relationships(self.b)), 0)
        self.store.close()
        self.store = AuthorStore(self.tmp.name)
        self.assertEqual(len(self.store.atlas.relationships(self.a)), 1)
        self.assertEqual(len(self.store.atlas.entities()), 2)
        self.assertEqual(len(self.store.atlas.events()), 0)


class AtlasWidgetTests(unittest.TestCase):
    def test_native_atlas_tabs_and_chapter_navigation_are_read_only(self):
        with tempfile.TemporaryDirectory() as folder:
            store = AuthorStore(folder)
            book = store.create_book('Novel')
            chapter = store.create_chapter(book, 'Arrival', 'A stranger arrived.')
            entity_a = store.atlas.add_entity('Traveler')
            entity_b = store.atlas.add_entity('Guide')
            store.atlas.add_relationship(book, entity_a, entity_b, 'knows')
            store.atlas.upsert_event(
                book, 'Arrival', story_order=4, chapter_id=chapter,
                evidence_quote='A stranger arrived.'
            )
            widget = AtlasWidget(store)
            try:
                widget.set_book(book)
                self.assertEqual(widget.tabs.count(), 3)
                self.assertEqual(widget.event_table.rowCount(), 1)
                self.assertIn('verified', widget.event_table.item(0, 5).text())
                self.assertEqual(widget.link_list.count(), 1)
                self.assertGreater(len(widget.graph_scene.items()), 0)
                hits = []
                widget.chapterRequested.connect(hits.append)
                widget.event_table.selectRow(0)
                widget.open_source()
                self.assertEqual(hits, [chapter])
                widget.audit()
                self.assertIn('Exact source quotes verified: 1',
                              widget.audit_result.toPlainText())
                self.assertEqual(store.chapter(chapter)['content'],
                                 'A stranger arrived.')
            finally:
                widget.close()
                store.close()


if __name__ == '__main__':
    unittest.main()
