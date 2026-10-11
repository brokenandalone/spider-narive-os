"""The Web text contrast and persistence tests. No display server required."""
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'the-web' / 'shell'))
from readability import (DEFAULT_MENU_SIZE, MENU_SIZES, load_menu_size,
                         menu_size_file, readability_css, save_menu_size)


class ReadabilityTests(unittest.TestCase):
    def test_default_and_persisted_value(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'settings.json'
            self.assertEqual(load_menu_size(path), DEFAULT_MENU_SIZE)
            for name in MENU_SIZES:
                save_menu_size(name, path)
                self.assertEqual(load_menu_size(path), name)
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_bad_value_rejected_without_modifying_preference(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'settings.json'
            save_menu_size('large', path)
            with self.assertRaises(ValueError):
                save_menu_size('12px; background:red', path)
            self.assertEqual(load_menu_size(path), 'large')
            path.write_text('not json', encoding='utf-8')
            self.assertEqual(load_menu_size(path), DEFAULT_MENU_SIZE)

    def test_symlink_is_not_followed(self):
        with tempfile.TemporaryDirectory() as directory:
            actual = Path(directory) / 'real.json'
            actual.write_text('private', encoding='utf-8')
            link = Path(directory) / 'link.json'
            link.symlink_to(actual)
            with self.assertRaises(OSError):
                save_menu_size('large', link)
            self.assertEqual(actual.read_text(), 'private')
            self.assertEqual(load_menu_size(link), DEFAULT_MENU_SIZE)

    def test_contrasting_popups_both_themes_and_sizes(self):
        for theme in ('light', 'dark'):
            for name, pixels in MENU_SIZES.items():
                sheet = readability_css(theme, name)
                self.assertIn('QComboBox QAbstractItemView', sheet)
                self.assertIn('QMenu::item:selected', sheet)
                self.assertIn('QToolTip', sheet)
                self.assertIn(f'font-size: {pixels}px;', sheet)
                self.assertIn('#fffcff' if theme == 'light' else '#130d1b', sheet)
                self.assertIn('#241332' if theme == 'light' else '#fffaff', sheet)
        with self.assertRaises(ValueError):
            readability_css('invisible', 'large')
        with self.assertRaises(ValueError):
            readability_css('dark', 'broken')


if __name__ == '__main__':
    unittest.main()
