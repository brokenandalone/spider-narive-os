"""Offline regression checks for the owner-PC audit: counts only, zero writes."""
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / 'the-web/package/audit-installed.py'
spec = importlib.util.spec_from_file_location('spider_installed_audit', SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class OwnerAuditTests(unittest.TestCase):
    def test_absent_files_never_created(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            home, system, installed, media = [base / name for name in ('home', 'system', 'installed', 'media')]
            report = audit.audit(home, installed, media, system, include_live=False)
            self.assertFalse(home.exists())
            self.assertFalse(system.exists())
            self.assertFalse(installed.exists())
            self.assertFalse(media.exists())
            self.assertEqual(report['content']['authorDatabase']['status'], 'not found')
            self.assertFalse(report['writesPerformed'])
            self.assertNotIn('kaliContainer', report)

    def test_counts_without_record_titles_and_without_sidecar_writes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            database = root / 'library.sqlite3'
            with sqlite3.connect(database) as con:
                con.executescript("""
                    CREATE TABLE books(id INTEGER PRIMARY KEY, title TEXT);
                    CREATE TABLE chapters(id INTEGER PRIMARY KEY, content TEXT);
                    CREATE TABLE snapshots(id INTEGER PRIMARY KEY);
                    INSERT INTO books(title) VALUES('VERY_PRIVATE_BOOK_TITLE');
                    INSERT INTO chapters(content) VALUES('VERY_PRIVATE_MANUSCRIPT_CONTENT');
                """)
            original_files = {f.name for f in root.iterdir()}
            result = audit.readonly_counts(database, ('books', 'chapters', 'snapshots', 'imported_sources'))
            self.assertEqual(result['status'], 'readable')
            self.assertEqual(result['counts'], {'books': 1, 'chapters': 1, 'snapshots': 0,
                                                'imported_sources': None})
            self.assertEqual({f.name for f in root.iterdir()}, original_files)
            serialized = json.dumps(result)
            self.assertNotIn('VERY_PRIVATE', serialized)

    def test_counts_of_docx_not_names(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'VERY_PRIVATE_CHAPTER.docx').write_bytes(b'PK')
            (root / 'notes.txt').write_text('never show this')
            self.assertEqual(audit.count_originals(root), 1)
            self.assertIsNone(audit.count_originals(root / 'not-there'))

    def test_runtime_stopped_kali_never_starts_distrobox(self):
        with patch.object(audit, 'bounded_command',
                          side_effect=[(0, ''), (0, 'exited')]) as command:
            self.assertEqual(audit.kali_snapshot(), 'exited')
            self.assertEqual(command.call_args_list[0].args[0], ['podman', 'container', 'exists', 'kali-bay'])
            self.assertEqual(command.call_args_list[1].args[0],
                             ['podman', 'inspect', '--format', '{{.State.Status}}', 'kali-bay'])

    def test_report_contains_only_known_fields(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            home = root / 'home'
            report = audit.audit(home, root / 'installed', root / 'media', root / 'sys', False)
            rendered = json.dumps(report)
            self.assertNotIn('PRIVATE_BOOK_TITLE', rendered)
            self.assertNotIn('PRIVATE_CHAPTER_CONTENT', rendered)
            self.assertTrue(report['manualTestingStillRequired'])
            self.assertIn('buildReceipt', report['desktop'])
            self.assertIn('authorDatabase', report['content'])


if __name__ == '__main__':
    unittest.main()
