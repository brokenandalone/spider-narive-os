"""Offline regression coverage for selective installed-PC native workspace reconciliation."""
import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / 'the-web/package/reconcile-native.py'
spec = importlib.util.spec_from_file_location('desktop_reconcile', MODULE_PATH)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class NativeReconciliationTests(unittest.TestCase):
    def test_known_author_launcher_adds_native_library_only(self):
        upstream = (ROOT / 'system/apps.py').read_text()
        self.assertEqual(upstream.count(helper.AUTHOR_BLOCK), 1)
        previous = upstream.replace(helper.AUTHOR_BLOCK, '', 1)
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'upstream.py'; source.write_text(upstream)
            dest = Path(folder) / 'installed.py'; dest.write_text(previous)
            self.assertEqual(helper.reconcile(source, dest, 'Author launcher'), 'reconciled')
            self.assertEqual(dest.read_text(), upstream)
            self.assertEqual(helper.reconcile(source, dest, 'Author launcher'), 'current')

    def test_unknown_author_changes_are_preserved(self):
        upstream = (ROOT / 'system/apps.py').read_text()
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'upstream.py'; source.write_text(upstream)
            dest = Path(folder) / 'installed.py'; dest.write_text('USER CUSTOMIZED')
            self.assertEqual(helper.reconcile(source, dest, 'Author launcher'), 'conflict')
            self.assertEqual(dest.read_text(), 'USER CUSTOMIZED')

    def test_known_old_studio_merges_tool_tabs_with_visual_preferences(self):
        upstream = (ROOT / 'studio/main.py').read_text()
        previous = helper.legacy_studio(upstream)
        self.assertNotIn('self.tool_tabs = QTabWidget()', previous)
        self.assertNotIn('StudioAIPanel', previous)
        self.assertIn("QFont('Sans Serif', 22, QFont.Bold)", previous)
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'upstream.py'; source.write_text(upstream)
            dest = Path(folder) / 'installed.py'; dest.write_text(previous)
            self.assertEqual(helper.reconcile(source, dest, 'Studio'), 'reconciled')
            updated = dest.read_text()
            self.assertIn('self.tool_tabs = QTabWidget()', updated)
            self.assertIn("QFont('Sans Serif', 22, QFont.Bold)", updated)
            self.assertIn('content.setContentsMargins(50, 48, 50, 48)', updated)
            self.assertIn('Refresh installed tools', updated)
            self.assertIn('self.ai_panel = StudioAIPanel()', updated)
            self.assertIn('Webbie remains the resident AI service', updated)
            self.assertEqual(helper.reconcile(source, dest, 'Studio'), 'current')

    def test_unknown_studio_changes_are_preserved(self):
        upstream = (ROOT / 'studio/main.py').read_text()
        previous = helper.legacy_studio(upstream).replace('CREATE. BUILD. PLAY.', 'PERSONAL STUDIO')
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'upstream.py'; source.write_text(upstream)
            dest = Path(folder) / 'installed.py'; dest.write_text(previous)
            self.assertEqual(helper.reconcile(source, dest, 'Studio'), 'conflict')
            self.assertEqual(dest.read_text(), previous)

    def test_installer_fills_missing_workspace_files_and_keeps_source_backups(self):
        installer = (ROOT / 'the-web/package/install-desktop.sh').read_text()
        self.assertIn('system/apps.py; do', installer)
        self.assertIn('find "$source_dir" -type f -print0', installer)
        self.assertIn('[[ ! -e "$target" && ! -L "$target" ]]', installer)
        self.assertIn('reconcile-native.py', installer)


if __name__ == '__main__':
    unittest.main()
