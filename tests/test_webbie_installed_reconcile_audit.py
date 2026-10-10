"""Read-only preflight reports customized on-device Webbie as a hard HOLD."""
from pathlib import Path
import importlib.util
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'webbie/tools/installed_reconcile_audit.py'
spec = importlib.util.spec_from_file_location('webbie_installed_audit', SOURCE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class InstalledReconciliationTests(unittest.TestCase):
    def test_customized_pc_code_blocks_install_and_is_not_changed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'src'
            installed = Path(folder) / 'installed'
            files = list(mod.SOURCES)
            for relative in files:
                a, b = root/relative, installed/relative
                a.parent.mkdir(parents=True, exist_ok=True)
                b.parent.mkdir(parents=True, exist_ok=True)
                a.write_text('def pristine():\n    pass\n', encoding='utf-8')
                b.write_text('def owner_customized():\n    pass\n', encoding='utf-8')
            original = (installed/files[0]).read_bytes()
            result = mod.report(root, installed)
            self.assertFalse(result['install_allowed'])
            self.assertEqual(result['overall'], 'RECONCILIATION_HOLD')
            self.assertIn(files[0], result['changed_or_missing_modules'])
            self.assertIn('owner_customized', result['files'][files[0]]['pc_only_symbols'])
            self.assertIn('pristine', result['files'][files[0]]['github_only_symbols'])
            self.assertEqual((installed/files[0]).read_bytes(), original)

    def test_missing_and_symlink_are_not_followed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            link = root / 'bad.py'
            target = root / 'real.py'
            target.write_text('SECRET=1\n')
            link.symlink_to(target)
            self.assertEqual(mod.inventory(link, ())['state'], 'symlink-blocked')
            self.assertEqual(mod.inventory(root/'missing.py', ())['state'], 'absent')

    def test_matching_sources_still_require_review(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'src'
            installed = Path(folder) / 'installed'
            for relative in mod.SOURCES:
                for base in (root, installed):
                    target = base / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(
                        ''.join('def '+name+'():\n    pass\n' for name in mod.SOURCES[relative])
                        or 'def placeholder():\n    pass\n')
            result = mod.report(root, installed)
            self.assertEqual(result['overall'], 'REVIEW_REQUIRED')
            self.assertFalse(result['install_allowed'])
            self.assertFalse(result['changed_or_missing_modules'])

if __name__ == '__main__':
    unittest.main()
