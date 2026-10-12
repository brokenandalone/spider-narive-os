"""Staged workspace restoration is bounded and does not manipulate files."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'the-web' / 'shell'))
from restore_plan import RestorePlan, desired_tab_order

WORKSPACES = {'default': 'The Web', 'studio': 'Studio',
              'author': 'Author', 'study': 'Study', 'webbie': 'Webbie'}


class RestorePlanTests(unittest.TestCase):
    def test_default_and_ordered_steps(self):
        plan = RestorePlan({'open': ['default','studio','author','study'],
                            'active':'author'}, WORKSPACES)
        self.assertEqual(plan.progress(), (0,3))
        self.assertEqual(plan.pop(), 'studio')
        self.assertEqual(plan.progress(), (1,3))
        self.assertEqual(plan.pop(), 'author')
        self.assertEqual(plan.pop(), 'study')
        self.assertEqual(plan.pop(), None)
        self.assertTrue(plan.done())
        self.assertEqual(plan.active,'author')

    def test_invalid_saved_state_removed(self):
        plan=RestorePlan({'open':['author','/etc','author','study',123],
                          'active':'/etc'},WORKSPACES)
        self.assertEqual(plan.order,['default','author','study'])
        self.assertEqual(plan.active,'default')

    def test_cancel_aborts_pending_only(self):
        plan=RestorePlan({'open':['studio','author','study'],
                          'active':'studio'},WORKSPACES)
        self.assertEqual(plan.pop(),'studio')
        plan.cancel()
        self.assertTrue(plan.done())
        self.assertEqual(plan.pop(),None)
        self.assertEqual(plan.progress(),(1,3))

    def test_user_opened_tab_preserved_in_order(self):
        plan=RestorePlan({'open':['studio','author','study'],
                          'active':'study'},WORKSPACES)
        tabs=desired_tab_order(plan,['default','author','webbie','studio','study'])
        self.assertEqual(tabs,['default','studio','author','study','webbie'])

    def test_no_tabs_only_home(self):
        plan=RestorePlan({}, WORKSPACES)
        self.assertTrue(plan.done())
        self.assertEqual(plan.progress(),(0,0))
        self.assertEqual(desired_tab_order(plan,['default']),['default'])


    def test_pause_resume_preserves_queue_without_loss(self):
        plan=RestorePlan({'open':['default','studio','author','study'],
                          'active':'study'}, WORKSPACES)
        self.assertTrue(plan.pause())
        self.assertEqual(plan.pop(),None)
        self.assertEqual(plan.progress(),(0,3))
        self.assertTrue(plan.report()['paused'])
        self.assertTrue(plan.resume())
        self.assertEqual(plan.pop(),'studio')
        self.assertEqual(plan.report()['remaining'],2)

    def test_prioritize_keeps_saved_order_separate(self):
        plan=RestorePlan({'open':['default','studio','author','study'],
                          'active':'author'}, WORKSPACES)
        self.assertTrue(plan.prioritize('study'))
        self.assertEqual(plan.pending,['study','studio','author'])
        self.assertEqual(plan.order,['default','studio','author','study'])
        self.assertFalse(plan.prioritize('unknown'))
        self.assertEqual(plan.pop(),'study')

    def test_skip_tracks_intent_without_modifying_saved_session(self):
        plan=RestorePlan({'open':['default','studio','author','study'],
                          'active':'author'},WORKSPACES)
        self.assertTrue(plan.skip('author'))
        self.assertFalse(plan.skip('author'))
        self.assertEqual(plan.report()['skipped'],('author',))
        self.assertEqual(plan.progress(),(1,3))
        self.assertEqual(plan.order,['default','studio','author','study'])
        self.assertEqual(plan.pop(),'studio')
        self.assertEqual(plan.pop(),'study')
        self.assertTrue(plan.done())

    def test_manual_open_is_not_reloaded_later(self):
        plan=RestorePlan({'open':['default','studio','author'], 'active':'studio'},
                         WORKSPACES)
        self.assertTrue(plan.acknowledge('author'))
        self.assertFalse(plan.acknowledge('author'))
        self.assertEqual(plan.pop(),'studio')
        self.assertEqual(plan.pop(),None)
        self.assertEqual(plan.progress(),(2,2))

    def test_cancel_does_not_make_resume_possible(self):
        plan=RestorePlan({'open':['default','studio','study']},WORKSPACES)
        self.assertTrue(plan.pause())
        plan.cancel()
        self.assertFalse(plan.resume())
        self.assertFalse(plan.prioritize('study'))
        self.assertFalse(plan.skip('study'))
        self.assertEqual(plan.report()['remaining'],0)
        self.assertTrue(plan.done())


if __name__ == '__main__':
    unittest.main()
