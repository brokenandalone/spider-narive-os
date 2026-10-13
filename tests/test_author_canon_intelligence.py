"""Canon Intelligence tests: fake model, fake books, zero external requests."""
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'author'))

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMessageBox
from store import AuthorStore
from canon_intelligence import CanonIntelligence, choose_claims, current_source
from canon_intelligence_widget import CanonIntelligenceWidget
from review_engine import ReviewCancelled

APP = QApplication.instance() or QApplication([])


class GroundingTests(unittest.TestCase):
    def setUp(self):
        self.source = {
            'id': 11, 'book_id': 4, 'title': 'The Bridge',
            'content': (
                'At 3:13, the clock rang three times. '
                'Mira did not remember the river.'
            )
        }
        self.claims = [
            {
                'id': 7, 'book_id': None, 'category': 'Rule',
                'title': 'The bell', 'statement': 'The clock never rings at night.',
                'status': 'established', 'fact_key': 'bell'
            },
            {
                'id': 8, 'book_id': 4, 'category': 'Plot',
                'title': 'A proposed thought', 'statement': 'The river speaks.',
                'status': 'proposed', 'fact_key': 'river'
            }
        ]

    def _review(self, model_reply, **options):
        def ask(prompt, tokens):
            self.assertIn('UNTRUSTED MANUSCRIPT DATA', prompt)
            self.assertIn('"id": 7', prompt)
            self.assertNotIn('"id": 8', prompt)
            return json.dumps(model_reply)
        return CanonIntelligence(ask=ask).review(
            [self.source], self.claims, scope='chapter', **options
        )

    def test_only_real_quotes_and_approved_claim_ids_survive(self):
        report = self._review({
            'issues': [
                {'claim_id':7, 'quote':'the clock rang three times.',
                 'reason':'A bell rings after dark, but the rule says otherwise.'},
                {'claim_id':99, 'quote':'the clock rang three times.',
                 'reason':'Invented claim should never survive validation.'},
                {'claim_id':7, 'quote':'Someone invented a phantom line.',
                 'reason':'Invented quotes must be dropped every time.'}
            ],
            'proposals':[
                {'title':'The clock chime', 'category':'Object',
                 'statement':'The bridge clock sounds after dark.',
                 'quote':'At 3:13, the clock rang three times.'},
                {'title':'Ghost line', 'category':'Rule',
                 'statement':'Nothing in the manuscript supports it.',
                 'quote':'Fake text not found in the manuscript.'}
            ]
        })
        self.assertEqual(len(report['findings']), 2)
        self.assertEqual(report['discarded_unverifiable'], 3)
        self.assertEqual(report['established_claims_considered'], 1)
        self.assertEqual(report['chapters_examined'], 1)
        first = report['findings'][0]
        self.assertEqual(first['claim_id'], 7)
        self.assertEqual(self.source['content'][first['start']:first['end']],
                         first['quote'])
        self.assertEqual(report['findings'][1]['kind'], 'proposed_idea')

    def test_bounded_review_covers_entire_book(self):
        original = {'id':12,'book_id':4,'title':'Long chapter',
                    'content':'Tick! ' * 1400}
        invocations = []
        def ask(prompt, tokens):
            invocations.append(prompt)
            return json.dumps({'issues':[], 'proposals':[]})
        output = CanonIntelligence(ask=ask).review(
            [original, self.source], self.claims
        )
        self.assertEqual(output['sections_examined'], len(invocations))
        self.assertGreater(output['sections_examined'], 2)
        self.assertEqual(output['chapters_examined'], 2)
        self.assertIn('capped', output['limitations'])

    def test_invalid_json_is_not_promoted_to_facts(self):
        report = CanonIntelligence(ask=lambda *_:'I made up a claim').review(
            [self.source], self.claims
        )
        self.assertEqual(report['findings'], [])

    def test_cancellation_blocks_queued_work(self):
        token = threading.Event()
        token.set()
        with self.assertRaises(ReviewCancelled):
            CanonIntelligence(ask=lambda *_: self.fail('should not call')).review(
                [self.source], self.claims, cancelled=token
            )

    def test_unapproved_and_superseded_claims_never_enter_reference_list(self):
        claims = list(self.claims) + [{
            'id':9,'book_id':4,'category':'Rule','title':'Old rule',
            'statement':'Superseded', 'status':'superseded'
        }]
        chosen = choose_claims(self.source['content'], claims, 4)
        self.assertEqual([x['id'] for x in chosen], [7])

    def test_not_a_single_source_byte_is_changed(self):
        saved = self.source['content']
        self._review({'issues':[], 'proposals':[]})
        self.assertEqual(self.source['content'], saved)


class ApprovalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = AuthorStore(self.tmp.name)
        self.book = self.store.create_book('Broken World Test')
        self.chapter = self.store.create_chapter(
            self.book, 'Old Street', 'The clock struck exactly 3:13.'
        )
        self.official = self.store.master_canon.add(
            'City rule', 'Time is distorted around the clock.',
            status='established'
        )
        self.widget = CanonIntelligenceWidget(
            self.store, lambda:self.store.chapter(self.chapter),
            lambda:True
        )
        self.widget.set_book(self.book)
        self.finding = {
            'kind':'proposed_idea', 'category':'Timeline',
            'title':'Clock clue', 'statement':'The city clock chimes at 3:13.',
            'quote':'The clock struck exactly 3:13.',
            'book_id':self.book,'chapter_id':self.chapter,
            'chapter_title':'Old Street',
            'chapter_digest':__import__('hashlib').sha256(
                'The clock struck exactly 3:13.'.encode()).hexdigest(),
            'start':0,'end':len('The clock struck exactly 3:13.')
        }

    def tearDown(self):
        self.widget.close()
        self.store.close()
        self.tmp.cleanup()

    def _select(self, finding=None):
        self.widget.display_report({
            'scope':'chapter','chapters_examined':1,'sections_examined':1,
            'established_claims_available':1,'established_claims_considered':1,
            'findings':[dict(finding or self.finding)],
            'limitations':'Only the quotation was checked.'
        })
        self.widget.results.setCurrentRow(0)

    def test_explicit_approval_only_creates_proposed_not_established(self):
        self.widget.session_book = self.book
        self._select()
        initial = self.store.master_canon.audit()['total']
        with patch.object(QMessageBox,'question',return_value=QMessageBox.No):
            self.widget.save_proposal()
        self.assertEqual(self.store.master_canon.audit()['total'], initial)
        with patch.object(QMessageBox,'question',return_value=QMessageBox.Yes):
            self.widget.save_proposal()
        self.assertEqual(self.store.master_canon.audit()['total'], initial + 1)
        newest = next(x for x in self.store.master_canon.claims(include_all=True)
                      if x['title'] == 'Clock clue')
        self.assertEqual(newest['status'], 'proposed')
        self.assertEqual(
            self.store.master_canon.proposed_duplicate(
                book_id=self.book, chapter_id=self.chapter,
                title=self.finding['title'],
                statement=self.finding['statement'],
                source_quote=self.finding['quote']
            ), newest['id']
        )
        self.widget.save_proposal()
        self.assertEqual(self.store.master_canon.audit()['total'], initial + 1)
        self.assertEqual(self.store.chapter(self.chapter)['content'],
                         'The clock struck exactly 3:13.')

    def test_stale_evidence_cannot_create_claim(self):
        self.widget.session_book = self.book
        self._select()
        self.store.save(self.chapter, 'It is now 4:13.')
        self.assertFalse(current_source(self.store, self.finding))
        with patch.object(QMessageBox,'warning') as warning:
            self.widget.save_proposal()
        self.assertTrue(warning.called)
        self.assertEqual(self.store.master_canon.audit()['total'], 1)

    def test_source_link_is_precise_and_no_auto_navigation(self):
        self.widget.session_book = self.book
        self._select()
        opened = []
        self.widget.sourceRequested.connect(lambda *data:opened.append(data))
        self.widget.open_source()
        self.assertEqual(opened[0][0], self.chapter)
        self.assertEqual(opened[0][1], self.finding['quote'])
        self.assertEqual(self.store.master_canon.audit()['total'], 1)

    def test_book_switch_discards_stale_report(self):
        self.widget.session_book = self.book
        other = self.store.create_book('The Road')
        self.widget.set_book(other)
        self._select()
        self.assertIsNone(self.widget.report)
        self.assertEqual(self.widget.results.count(), 0)


if __name__ == '__main__':
    unittest.main()
