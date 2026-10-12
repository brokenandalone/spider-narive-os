"""Additional desktop navigation tests requiring no GUI or display server."""
from dataclasses import dataclass
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'the-web' / 'shell'))

from navigation_core import find_items, valid_window_id
from workspace_navigation import (
    adjacent_index, canonical_tabs, other_tab_names, workspace_context_summary)


WORKSPACES = {
    'default': 'The Web', 'studio': 'Studio', 'author': 'Author',
    'study': 'School', 'webbie': 'Webbie', 'forage': 'Forage',
}


@dataclass(frozen=True)
class Window:
    ident: str
    title: str


class WorkspaceNavigationTests(unittest.TestCase):
    def test_home_first_and_duplicate_tab_removal(self):
        self.assertEqual(
            canonical_tabs(['study', 'default', 'studio', 'study', 'forage'], WORKSPACES),
            ['default', 'study', 'studio', 'forage'])
        self.assertEqual(canonical_tabs(['../../escape', 42], WORKSPACES), ['default'])

    def test_bounded_cycling(self):
        self.assertEqual(adjacent_index(4, 3, 1), 0)
        self.assertEqual(adjacent_index(4, 0, -1), 3)
        self.assertEqual(adjacent_index(4, 2, 1), 3)
        self.assertEqual(adjacent_index(0, 0, 1), -1)
        self.assertEqual(adjacent_index(4, -1, -1), 0)

    def test_close_others_preserves_home_and_selected(self):
        names = ['default', 'studio', 'study', 'author']
        self.assertEqual(other_tab_names(names, 'study', WORKSPACES),
                         ['studio', 'author'])
        self.assertEqual(other_tab_names(names, 'default', WORKSPACES),
                         ['studio', 'study', 'author'])

    def test_consent_bounded_advisory_context(self):
        value = workspace_context_summary(
            'School', ['The Web', 'Author', 'School'], detail='PSY 328 assignment')
        self.assertIn('Current workspace: School', value)
        self.assertIn('Open workspace tabs: The Web, Author, School', value)
        self.assertIn('PSY 328 assignment', value)
        self.assertNotIn('/home/', value)
        huge = workspace_context_summary('S' * 1000, ['X' * 1000] * 50,
                                         detail='D' * 1000)
        self.assertLessEqual(len(huge), 600)


class OpenWindowSearchTests(unittest.TestCase):
    def test_reject_untrusted_window_ids(self):
        for ident in ('', '0x0', '0x' + '1' * 17, '0x12; echo danger',
                      '/tmp/file', '0x-1', 15, None):
            self.assertFalse(valid_window_id(ident))
        self.assertTrue(valid_window_id('0x0000ABCD'))

    def test_rank_open_window_and_skip_invalid(self):
        windows = [Window('0x00000122', 'Firefox · Browser'),
                   Window('0x0', 'Fake Browser'),
                   Window('0x99999999999999999', 'Unsafe Browser')]
        choices = find_items('firefox', WORKSPACES, windows=windows)
        self.assertEqual(len([item for item in choices if item.kind == 'window']), 1)
        first = next(item for item in choices if item.kind == 'window')
        self.assertEqual(first.ident, '0x00000122')
        self.assertEqual(first.label, 'Firefox · Browser')
        self.assertFalse(any(item.ident == '0x0' for item in choices))

    def test_window_matches_do_not_launch_commands(self):
        for unsafe in ['$(touch /tmp/hello)', '; rm -rf /', '&& sudo']:
            self.assertFalse(find_items(unsafe, WORKSPACES,
                                        windows=[Window('0x0100', 'Terminal')]))


if __name__ == '__main__':
    unittest.main()
