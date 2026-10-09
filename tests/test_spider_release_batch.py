"""Non-destructive source tests for the owner-requested single batch installer."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('spider_release_batch', ROOT / 'system/release_batch.py')
batch = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = batch
spec.loader.exec_module(batch)


class BatchReleaseTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.base = Path(self.dir.name)
        self.source_root = self.base / 'sources'
        self.target_root = self.base / 'installed'
        self.backup_root = self.base / 'backups'
        self.source = self.source_root / 'example.py'
        self.target = self.target_root / 'example.py'
        self.source.parent.mkdir(parents=True)
        self.target.parent.mkdir(parents=True)
        self.source.write_text('VALUE = 2\n', encoding='utf-8')
        self.entry = batch.Item(self.source, self.target, uid=os.geteuid(), gid=os.getegid(),
                                mode=0o644, reference='example.py')
        self.false_baseline = lambda *args: False
        self.true_baseline = lambda *args: True

    def tearDown(self):
        self.dir.cleanup()

    def test_unknown_local_customization_blocks_entire_transaction(self):
        self.target.write_text('MY CUSTOM WEBBIE = 1\n')
        checks = batch.inspect([self.entry], self.source_root, (), self.false_baseline)
        self.assertEqual(checks[0][1], 'BLOCKED')
        with self.assertRaisesRegex(RuntimeError, 'No files were changed'):
            batch.apply([self.entry], self.backup_root, self.source_root, (), self.false_baseline)
        self.assertEqual(self.target.read_text(), 'MY CUSTOM WEBBIE = 1\n')
        self.assertFalse(self.backup_root.exists())

    def test_new_module_installs_and_rolls_back_with_one_manifest(self):
        receipt = batch.apply([self.entry], self.backup_root, self.source_root, (), self.false_baseline)
        self.assertIsNotNone(receipt)
        self.assertEqual(self.target.read_text(), 'VALUE = 2\n')
        self.assertEqual((receipt / 'manifest.json').stat().st_mode & 0o777, 0o600)
        batch.rollback([self.entry], receipt, self.backup_root, dry_run=True)
        self.assertTrue(self.target.exists())
        batch.rollback([self.entry], receipt, self.backup_root, dry_run=False)
        self.assertFalse(self.target.exists())

    def test_partial_copy_failure_restores_first_file_and_leaves_second_untouched(self):
        self.target.write_text('VALUE = 1\n')
        source2 = self.source_root / 'second.py'
        target2 = self.target_root / 'second.py'
        source2.write_text('VALUE = 200\n')
        target2.write_text('VALUE = 100\n')
        second = batch.Item(source2, target2, uid=os.geteuid(), gid=os.getegid(),
                            reference='second.py')
        original_copy = batch.atomic_copy
        count = 0
        def copy_with_failure(*args, **kwargs):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError('simulated failed second file write')
            return original_copy(*args, **kwargs)
        with patch.object(batch, 'atomic_copy', side_effect=copy_with_failure):
            with self.assertRaisesRegex(OSError, 'simulated'):
                batch.apply([self.entry, second], self.backup_root,
                            self.source_root, (), self.true_baseline)
        self.assertEqual(self.target.read_text(), 'VALUE = 1\n')
        self.assertEqual(target2.read_text(), 'VALUE = 100\n')

    def test_failure_after_committed_replace_still_rolls_back(self):
        self.target.write_text('VALUE = 1\n')
        original_copy = batch.atomic_copy
        calls = 0
        def fail_after_copy(*args, **kwargs):
            nonlocal calls
            calls += 1
            original_copy(*args, **kwargs)
            if calls == 1:
                raise OSError('simulated exception after replace')
        with patch.object(batch, 'atomic_copy', side_effect=fail_after_copy):
            with self.assertRaisesRegex(OSError, 'after replace'):
                batch.apply([self.entry], self.backup_root,
                            self.source_root, (), self.true_baseline)
        self.assertEqual(self.target.read_text(), 'VALUE = 1\n')

    def test_known_previous_version_is_backed_up_and_restorable(self):
        self.target.write_text('VALUE = 1\n')
        receipt = batch.apply([self.entry], self.backup_root, self.source_root, (), self.true_baseline)
        self.assertEqual(self.target.read_text(), 'VALUE = 2\n')
        batch.rollback([self.entry], receipt, self.backup_root, dry_run=False)
        self.assertEqual(self.target.read_text(), 'VALUE = 1\n')

    def test_modified_installed_file_cannot_be_rolled_back_blindly(self):
        receipt = batch.apply([self.entry], self.backup_root, self.source_root, (), self.false_baseline)
        self.target.write_text('UNRECOGNIZED = 5\n')
        with self.assertRaisesRegex(RuntimeError, 'customized after upgrade'):
            batch.rollback([self.entry], receipt, self.backup_root, dry_run=False)
        self.assertEqual(self.target.read_text(), 'UNRECOGNIZED = 5\n')

    def test_target_symlink_blocks_preflight(self):
        outside = self.base / 'private'
        outside.write_text('PRIVATE')
        self.target.symlink_to(outside)
        checks = batch.inspect([self.entry], self.source_root, (), self.false_baseline)
        self.assertEqual(checks[0][1], 'BLOCKED')
        self.assertEqual(outside.read_text(), 'PRIVATE')

    def test_bad_python_source_blocks_without_installation(self):
        self.source.write_text('class Broken(:\n')
        checks = batch.inspect([self.entry], self.source_root, (), self.false_baseline)
        self.assertEqual(checks[0][1], 'BLOCKED')
        self.assertFalse(self.target.exists())

    def test_user_ui_release_catalog_is_unique_and_scoped(self):
        items = batch.prepare_items(root=ROOT, install=self.base / 'install',
                                    units=self.base / 'unit',
                                    home=self.base / 'user', uid=os.geteuid(),
                                    gid=os.getegid())
        self.assertEqual(len(items), len({str(i.target) for i in items}))
        targets = '\n'.join(str(i.target) for i in items)
        self.assertIn('webbie-onedrive.timer', targets)
        self.assertIn('webbie-floating-face.desktop', targets)
        self.assertNotIn('library.sqlite3', targets)
        self.assertNotIn('grub.cfg', targets)
        self.assertNotIn('rclone.conf', targets)
        self.assertNotIn('kali-vg', targets)

    def test_realistic_multi_component_layout_roundtrip(self):
        """Author, desktop, Webbie agent, portrait, and OneDrive change together."""
        components = (
            'author/main.py',
            'the-web/shell/main.py',
            'the-web/shell/webbie_panel.py',
            'the-web/overlay/webbie_face.py',
            'webbie/agent/webbie.py',
            'webbie/agent/night_mode.py',
            'system/onedrive.py',
        )
        items = []
        for index, relative in enumerate(components):
            source = self.source_root / relative
            target = self.target_root / relative
            source.parent.mkdir(parents=True, exist_ok=True)
            target.parent.mkdir(parents=True, exist_ok=True)
            source.write_text('BUILD = 2\n', encoding='utf-8')
            if index % 2 == 0:
                target.write_text('BUILD = 1\n', encoding='utf-8')
            items.append(batch.Item(source, target, uid=os.geteuid(),
                                    gid=os.getegid(), reference=relative))
        custom_library = self.base / 'home/Author/library.sqlite'
        custom_original = self.base / 'home/Author/Originals/book.docx'
        custom_library.parent.mkdir(parents=True, exist_ok=True)
        custom_original.parent.mkdir(parents=True, exist_ok=True)
        custom_library.write_bytes(b'PRIVATE SQLITE DATA')
        custom_original.write_bytes(b'ORIGINAL WORD BYTES')
        receipt = batch.apply(items, self.backup_root, self.source_root, (),
                              self.true_baseline)
        self.assertEqual(len(batch.json.loads((receipt / 'manifest.json').read_text())['files']),
                         len(items))
        for item in items:
            self.assertEqual(item.target.read_text(), 'BUILD = 2\n')
        batch.rollback(items, receipt, self.backup_root, dry_run=True)
        batch.rollback(items, receipt, self.backup_root, dry_run=False)
        for index, item in enumerate(items):
            if index % 2 == 0:
                self.assertEqual(item.target.read_text(), 'BUILD = 1\n')
            else:
                self.assertFalse(item.target.exists())
        self.assertEqual(custom_library.read_bytes(), b'PRIVATE SQLITE DATA')
        self.assertEqual(custom_original.read_bytes(), b'ORIGINAL WORD BYTES')

    def test_cli_accepts_single_check_flag(self):
        with patch.object(batch, 'user_info', return_value=(self.base / 'user', 1000, 1000)):
            with patch.object(batch, 'prepare_items', return_value=[self.entry]):
                with patch.object(batch, 'inspect', return_value=[(self.entry, 'ADD', 'new')]):
                    self.assertEqual(batch.main(['--check']), 0)
                    self.assertEqual(batch.main(['check']), 0)


if __name__ == '__main__':
    unittest.main()
