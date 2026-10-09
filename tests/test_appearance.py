"""Persistent appearance and explicit, rollback-safe user interface selection."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import sys
import tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'the-web/shell'))
from PyQt5.QtWidgets import QApplication
from appearance import load_theme, save_theme, appearance_file, LIGHT_STYLE
from quick_settings import QuickSettingsPanel

APP = QApplication.instance() or QApplication([])


class AppearanceTests(unittest.TestCase):
    def test_missing_malformed_or_unsupported_settings_keep_default_dark(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'spider-os/appearance.json'
            self.assertEqual(load_theme(path), 'dark')
            path.parent.mkdir()
            for content in ('this is not JSON', '[]', '{"theme":"neon"}', '{}'):
                path.write_text(content, encoding='utf-8')
                self.assertEqual(load_theme(path), 'dark')

    def test_atomic_appearance_is_private_and_restored_across_reads(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'spider-os/appearance.json'
            save_theme('light', path)
            self.assertEqual(load_theme(path), 'light')
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)
            save_theme('dark', path)
            self.assertEqual(load_theme(path), 'dark')
            self.assertFalse(list(path.parent.glob('.appearance-*')))

    def test_invalid_and_symlinked_preferences_do_not_change_private_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / 'private'
            target.write_text('secret')
            alias = root / 'appearance.json'
            alias.symlink_to(target)
            self.assertEqual(load_theme(alias), 'dark')
            for value in ('neon', '', None):
                with self.assertRaises(ValueError):
                    save_theme(value, root / 'settings.json')
            with self.assertRaises(OSError):
                save_theme('light', alias)
            self.assertEqual(target.read_text(), 'secret')

    def test_user_config_path_is_under_spider_os(self):
        with tempfile.TemporaryDirectory() as temporary:
            self.assertEqual(appearance_file(temporary),
                             Path(temporary) / 'spider-os/appearance.json')

    def test_light_style_has_explicit_contrasting_text(self):
        self.assertIn('QWidget { color:#241332;', LIGHT_STYLE)
        self.assertIn('QLineEdit, QComboBox, QListWidget', LIGHT_STYLE)
        self.assertIn('selection-color:#241332', LIGHT_STYLE)

    def test_quick_settings_saves_only_explicit_choice(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'appearance.json'
            save_theme('dark', path)
            calls = []
            def update(value):
                calls.append(value)
                save_theme(value, path)
            panel = QuickSettingsPanel(appearance_reader=lambda:load_theme(path),
                                       appearance_writer=update)
            self.assertTrue(panel.worker.wait(4000))
            APP.processEvents()
            self.assertEqual(calls, [])
            panel.appearance_selector.setCurrentIndex(
                panel.appearance_selector.findData('light'))
            self.assertEqual(calls, ['light'])
            self.assertEqual(load_theme(path), 'light')
            panel.close()
            reopened = QuickSettingsPanel(appearance_reader=lambda:load_theme(path),
                                          appearance_writer=update)
            self.assertTrue(reopened.worker.wait(4000))
            APP.processEvents()
            self.assertEqual(reopened.appearance_selector.currentData(), 'light')
            self.assertEqual(calls, ['light'])
            reopened.close()

    def test_failed_theme_write_restores_selector(self):
        def reject(value):
            raise OSError('disk is read only')
        panel = QuickSettingsPanel(appearance_reader=lambda:'dark',
                                   appearance_writer=reject)
        self.assertTrue(panel.worker.wait(4000))
        APP.processEvents()
        panel.appearance_selector.setCurrentIndex(
            panel.appearance_selector.findData('light'))
        self.assertEqual(panel.appearance_selector.currentData(), 'dark')
        self.assertIn('not changed', panel.help.text())
        panel.close()

    def test_readonly_quick_settings_disables_theme_change(self):
        panel = QuickSettingsPanel()
        self.assertTrue(panel.worker.wait(4000))
        APP.processEvents()
        self.assertFalse(panel.appearance_selector.isEnabled())
        panel.close()


if __name__ == '__main__':
    unittest.main()
