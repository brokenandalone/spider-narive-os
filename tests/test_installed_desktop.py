import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('installed_desktop', ROOT / 'the-web/package/verify-installed.py')
qa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qa)


class InstalledDesktopChecks(unittest.TestCase):
    def catalog(self, root):
        (root / 'branding/wallpapers').mkdir(parents=True)
        (root / 'image.png').write_bytes(b'image')
        entry = {'id': 'test', 'file': 'image.png', 'sha256': hashlib.sha256(b'image').hexdigest(), 'workspace': 'study'}
        data = {'wallpapers': [entry], 'new_workspace_defaults': {'study': 'test'}}
        self.write(root, data)
        return data

    def write(self, root, data):
        (root / 'branding/wallpapers/collection.json').write_text(json.dumps(data))

    def test_rejects_corruption_and_escaped_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = self.catalog(root)
            self.assertEqual(qa.audit_wallpapers(root)[0], 1)
            (root / 'image.png').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                qa.audit_wallpapers(root)
            data['wallpapers'][0]['file'] = '../image.png'
            self.write(root, data)
            with self.assertRaisesRegex(ValueError, 'unsafe'):
                qa.audit_wallpapers(root)

    def test_rejects_wrong_workspace_defaults(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = self.catalog(root)
            data['new_workspace_defaults'] = {'author': 'test'}
            self.write(root, data)
            with self.assertRaisesRegex(ValueError, 'wrong workspace'):
                qa.audit_wallpapers(root)

    def test_missing_installation_never_reports_acceptance_complete(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            report = qa.verify(root, root, root, root / 'absent.json', live=False)
            self.assertFalse(report['installedAcceptanceComplete'])
            self.assertTrue(report['manualChecksPending'])
            self.assertTrue(any(c['status'] == 'FAIL' for c in report['checks']))
            self.assertTrue(any(c['check'] == 'Media Center playback build' and c['status'] == 'WARN' for c in report['checks']))

    def test_full_packaged_gallery_matches_release_assignments(self):
        count, groups = qa.audit_wallpapers(ROOT)
        self.assertEqual(count, 59)
        self.assertGreaterEqual(groups['study'], 4)


if __name__ == '__main__':
    unittest.main()
