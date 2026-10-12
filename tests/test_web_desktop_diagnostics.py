"""No-leakage regression tests for owner-approved Spider OS diagnostics."""
from dataclasses import dataclass
from pathlib import Path
import json
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'the-web' / 'shell'))
from desktop_diagnostics import build_safe_report, report_text


@dataclass
class Health:
    ident: str
    status: str


WORKSPACES = {'default': 'The Web', 'author': 'Author',
              'studio': 'Studio', 'study': 'School'}


class SafeDiagnosticsTests(unittest.TestCase):
    def test_source_snapshot_contains_only_allowed_fields(self):
        report = build_safe_report(
            WORKSPACES, ['default','author','studio'], 'author',
            health=[Health('author','open'),Health('study','missing')],
            load_seconds={'author': 1.23456}, applications=34,
            open_windows=5, safe_mode=False)
        self.assertEqual(report['schema'], 'spider-web-safe-diagnostics-v1')
        self.assertEqual(report['open_workspaces'], ['default','author','studio'])
        self.assertEqual(report['active_workspace'], 'author')
        self.assertEqual(report['load_seconds']['author'], 1.235)
        self.assertEqual(report['workspace_health']['study'], 'missing')
        self.assertEqual(report['installed_app_count'], 34)
        self.assertNotIn('window_titles', report)
        self.assertNotIn('document_paths', report)
        self.assertNotIn('clipboard', report)

    def test_untrusted_names_are_not_exported(self):
        secrets = '/home/someone/Documents/PrivateDraft.docx'
        report = build_safe_report(
            WORKSPACES, ['default', secrets, 'author'], secrets,
            health=[Health(secrets,'missing'),Health('author','error transcript')],
            load_seconds={secrets:3, 'study': -1})
        encoded = report_text(report)
        self.assertNotIn('PrivateDraft',encoded)
        self.assertNotIn('error transcript',encoded)
        self.assertEqual(report['active_workspace'],'default')
        self.assertEqual(report['open_workspaces'],['default','author'])

    def test_restoration_details_bound_to_workspace_ids(self):
        report = build_safe_report(WORKSPACES, [], 'default', restore={
            'processed': 2, 'remaining': 7, 'paused': True,
            'skipped': ['author', '/home/someone/private', 'studio']})
        self.assertEqual(report['restoration']['skipped'],['author','studio'])
        self.assertTrue(report['restoration']['paused'])
        self.assertEqual(report['open_workspaces'], ['default'])

    def test_non_finite_load_seconds_do_not_leak(self):
        report = build_safe_report(WORKSPACES, ['studio'], 'studio',
            load_seconds={'studio':float('inf'), 'author':float('nan'), 'study':2.1})
        self.assertEqual(report['load_seconds'], {'study':2.1})

    def test_copy_ready_json_is_roundtrippable(self):
        report = build_safe_report(WORKSPACES,['default'], 'default', applications=2)
        text = report_text(report)
        self.assertEqual(json.loads(text),report)
        self.assertTrue(text.endswith('\n'))


if __name__ == '__main__':
    unittest.main()
