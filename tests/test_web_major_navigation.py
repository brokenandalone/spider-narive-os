"""The Web launcher and desktop persistence regression suite. Headless."""
from dataclasses import dataclass
from pathlib import Path
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'the-web' / 'shell'))

from navigation_core import normalized, find_items, INTERNAL_ACTIONS
from navigation_state import (
    initial_state, load_navigation, record_recent, toggle_favorite,
    save_navigation, MAX_RECENT, MAX_FAVORITES)
from desktop_state import clean_state, read_desktop_state, write_desktop_state, MAX_OPEN_TABS


WORKSPACES = {
    'default': 'The Web', 'studio': 'Studio', 'author': 'Author',
    'study': 'School', 'webbie': 'Webbie', 'kali-bay': 'Kali Bay', 'forage': 'Forage',
}


@dataclass
class App:
    desktop_id: str
    name: str
    comment: str
    workspace: str


APPS = [
    App('org.kde.dolphin.desktop', 'Dolphin', 'Files manager', 'studio'),
    App('org.mozilla.Firefox.desktop', 'Firefox', 'Browse the internet', 'forage'),
    App('org.kde.kate.desktop', 'Kate', 'Editor for code and text', 'author'),
]


class QuickLaunchTests(unittest.TestCase):
    def test_search_normalization_and_scoring(self):
        self.assertEqual(normalized('Café'), 'cafe')
        result = find_items('dolphin', WORKSPACES, APPS)
        self.assertEqual((result[0].kind, result[0].ident), ('app', 'org.kde.dolphin.desktop'))
        self.assertTrue(any(x.ident == 'webbie' for x in find_items('webbie', WORKSPACES)))
        self.assertTrue(any(x.ident == 'quick-settings' for x in find_items('quick settings', WORKSPACES)))

    def test_only_live_hex_window_ids_can_be_suggested(self):
        from desktop import Task
        tasks = [
            Task("0x00000101", "Movie Player"),
            Task("0x00000102", "Editor"),
            Task("../../etc/passwd", "Movie Spoof"),
            Task("0x0", "Movie Zero"),
            Task("0xDEADBEEF;id", "Movie Injection"),
        ]
        rows = find_items("movie", WORKSPACES, APPS, windows=tasks)
        self.assertEqual([(x.kind, x.ident) for x in rows],
                         [("window", "0x00000101")])
        self.assertEqual(find_items("Movie", WORKSPACES, APPS, windows=()), [])

    def test_not_a_command_executor(self):
        for command in ('; sudo rm -rf', '$(touch file)', '|||'):
            results = find_items(command, WORKSPACES, APPS)
            self.assertEqual(results, [])
        self.assertTrue(all(kind in ('action',) for kind, _, _ in
                            [('action', key, label) for key, label, detail in INTERNAL_ACTIONS]))

    def test_favorite_and_recent_ranking(self):
        favored = [('workspace', 'study')]
        ranked = find_items('', WORKSPACES, APPS, favorites=favored)
        self.assertEqual(ranked[0].ident, 'study')
        ranked = find_items('', WORKSPACES, APPS, recents=[('app', 'org.mozilla.Firefox.desktop')])
        self.assertEqual(ranked[0].ident, 'org.mozilla.Firefox.desktop')

    def test_limit_and_invalid_injection(self):
        ranked = find_items('', WORKSPACES, APPS, limit=3)
        self.assertLessEqual(len(ranked), 3)
        self.assertEqual(find_items('xyznotfound', WORKSPACES, APPS), [])

    def test_navigation_persistence_and_order(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'navigation.json'
            state = initial_state(WORKSPACES)
            self.assertTrue(toggle_favorite(state, 'workspace', 'studio', WORKSPACES))
            self.assertNotIn(['workspace', 'studio'], state['favorites'])
            self.assertTrue(toggle_favorite(state, 'app', 'org.kde.kate.desktop', WORKSPACES))
            self.assertTrue(record_recent(state, 'app', 'org.kde.kate.desktop', WORKSPACES))
            self.assertTrue(record_recent(state, 'workspace', 'study', WORKSPACES))
            self.assertTrue(record_recent(state, 'app', 'org.kde.kate.desktop', WORKSPACES))
            self.assertEqual(state['recent'][0], ['app', 'org.kde.kate.desktop'])
            save_navigation(path, state, WORKSPACES)
            saved = load_navigation(path, WORKSPACES)
            self.assertEqual(saved, state)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_navigation_rejects_unsafe_ids_and_junk(self):
        state = initial_state(WORKSPACES)
        self.assertFalse(record_recent(state, 'app', 'evil.desktop; echo hacked', WORKSPACES))
        self.assertFalse(toggle_favorite(state, 'workspace', '../../etc', WORKSPACES))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'state.json'
            path.write_text('{"recent":[["app","../../x"],["workspace","study"]],'
                            '"favorites":[["app","bad/id"],["workspace","studio"]]}')
            read = load_navigation(path, WORKSPACES)
            self.assertEqual(read['recent'], [['workspace', 'study']])
            self.assertEqual(read['favorites'], [['workspace', 'studio']])

    def test_navigation_bounds_and_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'nav.json'
            original = Path(directory) / 'source.json'
            original.write_text('secret')
            path.symlink_to(original)
            with self.assertRaises(OSError):
                save_navigation(path, initial_state(WORKSPACES), WORKSPACES)
            self.assertEqual(original.read_text(), 'secret')
            self.assertEqual(load_navigation(path, WORKSPACES), initial_state(WORKSPACES))
            self.assertEqual(len(initial_state(WORKSPACES)['favorites']) <= MAX_FAVORITES, True)
            self.assertGreater(MAX_RECENT, 0)


class DesktopSessionTests(unittest.TestCase):
    def test_clean_invalid_and_duplicate_tabs(self):
        dirty = {'open': ['study', 'study', '../../secret', 'studio', 42, 'default'],
                 'active': 'nonexistent'}
        clean = clean_state(dirty, WORKSPACES)
        self.assertEqual(clean['open'], ['default', 'study', 'studio'])
        self.assertEqual(clean['active'], 'default')
        self.assertEqual(clean_state([], WORKSPACES)['open'], ['default'])

    def test_roundtrip_private_and_symlink_protection(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'desktop.json'
            expected = clean_state({'open': ['default', 'studio', 'study'],
                                    'active': 'study'}, WORKSPACES)
            write_desktop_state(path, expected, WORKSPACES)
            self.assertEqual(read_desktop_state(path, WORKSPACES), expected)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            alternate = Path(directory) / 'danger.txt'
            alternate.write_text('do not touch')
            path.unlink()
            path.symlink_to(alternate)
            with self.assertRaises(OSError):
                write_desktop_state(path, expected, WORKSPACES)
            self.assertEqual(alternate.read_text(), 'do not touch')

    def test_bounded_session_and_corruption_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'desktop.json'
            path.write_text('NOPE')
            self.assertEqual(read_desktop_state(path, WORKSPACES)['active'], 'default')
            path.write_text('x' * 50000)
            self.assertEqual(read_desktop_state(path, WORKSPACES)['open'], ['default'])
            self.assertLessEqual(len(clean_state({'open': ['study'] * 1000}, WORKSPACES)['open']),
                                 MAX_OPEN_TABS)


if __name__ == '__main__':
    unittest.main()
