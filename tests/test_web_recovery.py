"""The Web recovery checks, safe mode and manual session checkpoints."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'the-web' / 'shell'))
from session_checkpoints import (
    checkpoint_path, read_checkpoint, save_checkpoint, LIMIT_BYTES)
from workspace_health import check_workspaces
from workspaces import NATIVE

WORKSPACES = {'default': 'The Web', 'author': 'Author',
              'studio': 'Studio', 'study': 'Study',
              'system': 'System', 'webbie': 'Webbie'}


class CheckpointTests(unittest.TestCase):
    def test_save_and_restore_session_layout(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'desktop-checkpoint.json'
            session = {'open': ['default', 'study', 'author'],
                       'active': 'author'}
            saved = save_checkpoint(path, session, WORKSPACES)
            self.assertEqual(saved['open'], ['default', 'study', 'author'])
            self.assertEqual(read_checkpoint(path, WORKSPACES), saved)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            value = json.loads(path.read_text())
            self.assertEqual(value['version'], 1)

    def test_untrusted_entries_filtered(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'cp.json'
            save_checkpoint(path, {'open': ['author', '../../etc', 'study', 'study'],
                                   'active': '../../etc'}, WORKSPACES)
            state = read_checkpoint(path, WORKSPACES)
            self.assertEqual(state['open'], ['default', 'author', 'study'])
            self.assertEqual(state['active'], 'default')

    def test_bad_checkpoint_is_not_restored(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'cp.json'
            self.assertIsNone(read_checkpoint(path, WORKSPACES))
            path.write_text('not json')
            self.assertIsNone(read_checkpoint(path, WORKSPACES))
            path.write_text('{' + '"data":' + '"x"' * LIMIT_BYTES + '}')
            self.assertIsNone(read_checkpoint(path, WORKSPACES))
            path.write_text('{"version": 999, "session": {"open": ["author"]}}')
            self.assertIsNone(read_checkpoint(path, WORKSPACES))

    def test_symlink_refused_and_does_not_follow(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            target = base / 'private'
            target.write_text('unchanged')
            path = base / 'cp.json'
            path.symlink_to(target)
            with self.assertRaises(OSError):
                save_checkpoint(path, {'open': ['author']}, WORKSPACES)
            self.assertIsNone(read_checkpoint(path, WORKSPACES))
            self.assertEqual(target.read_text(), 'unchanged')
            safe_parent = base / 'parent'
            safe_parent.mkdir()
            alias = base / 'alias'
            alias.symlink_to(safe_parent, target_is_directory=True)
            with self.assertRaises(OSError):
                save_checkpoint(alias / 'cp.json', {'open': ['author']}, WORKSPACES)

    def test_checkpoint_path_in_config_home(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(checkpoint_path(root), Path(root) / 'spider-os/desktop-checkpoint.json')


class HealthTests(unittest.TestCase):
    def test_missing_and_available_native_sources(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            author = base / 'author/main.py'
            author.parent.mkdir()
            author.write_text('not executed')
            entries = check_workspaces(
                base, WORKSPACES, NATIVE, loaded={'author'})
            status = {item.ident: item.status for item in entries}
            self.assertEqual(status['author'], 'open')
            self.assertEqual(status['studio'], 'missing')
            self.assertEqual(status['study'], 'missing')
            self.assertEqual(status['system'], 'available')
            self.assertNotIn('default', status)

    def test_failure_always_visible_even_if_source_exists(self):
        with tempfile.TemporaryDirectory() as root:
            rows = check_workspaces(root, WORKSPACES, NATIVE,
                                   failures={'author': 'ImportError'})
            found = next(row for row in rows if row.ident == 'author')
            self.assertEqual(found.status, 'needs-attention')
            self.assertNotIn('ImportError', found.detail)

    def test_symlink_escape_does_not_claim_installation(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as elsewhere:
            outside = Path(elsewhere) / 'main.py'
            outside.write_text('private')
            author_dir = Path(root) / 'author'
            author_dir.mkdir()
            (author_dir / 'main.py').symlink_to(outside)
            data = check_workspaces(root, WORKSPACES, NATIVE)
            found = next(row for row in data if row.ident == 'author')
            self.assertEqual(found.status, 'missing')


if __name__ == '__main__':
    unittest.main()
