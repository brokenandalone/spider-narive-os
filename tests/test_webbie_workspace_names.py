"""Webbie calls the user Writer in Author and Student in School."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    'workspace_names', ROOT / 'webbie/agent/workspace_names.py')
names = importlib.util.module_from_spec(spec)
spec.loader.exec_module(names)


class WorkspaceNameTests(unittest.TestCase):
    def test_author_uses_writer_and_existing_names(self):
        self.assertEqual(names.context_name('author', {}), 'Writer')
        self.assertEqual(names.context_name('studio', {}), 'Justin')
        self.assertEqual(names.context_name('kali-bay', {}), 'Spider')
        self.assertEqual(names.context_name('study', {}), 'Student')
        self.assertEqual(names.context_name('school', {}), 'Student')

    def test_owner_preferences_take_priority(self):
        config = {'default_user_name': 'Owner',
                  'context_names': {'author': 'Novelist', 'studio': 'J'}}
        self.assertEqual(names.context_name('author', config), 'Novelist')
        self.assertEqual(names.context_name('studio', config), 'J')
        self.assertEqual(names.context_name('forage', config), 'Owner')
        self.assertEqual(names.context_name('study', config), 'Student')

    def test_invalid_overrides_do_not_confuse_agent(self):
        self.assertEqual(names.context_name('author', {'context_names': {'author': '   '}}),
                         'Writer')
        self.assertEqual(names.context_name('default', {'default_user_name': ''}), 'Cory')
        self.assertEqual(names.context_name('author', {'context_names': 5}), 'Writer')

    def test_default_config_contains_writer(self):
        data = json.loads((ROOT / 'webbie/config/default.json').read_text())
        self.assertEqual(data['context_names']['author'], 'Writer')
        self.assertEqual(data['context_names']['study'], 'Student')
        self.assertEqual(data['context_names']['school'], 'Student')


if __name__ == '__main__':
    unittest.main()
