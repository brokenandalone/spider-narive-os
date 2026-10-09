import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('wallpapers', ROOT / 'the-web/shell/wallpapers.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class WallpapersTest(unittest.TestCase):
    def test_packaged_collection_and_new_workspaces(self):
        with tempfile.TemporaryDirectory() as config:
            catalog = module.WallpaperCatalog(ROOT, config)
            self.assertEqual(len(catalog.entries), 59)
            for entry in catalog.entries:
                self.assertEqual(hashlib.sha256((ROOT / entry['file']).read_bytes()).hexdigest(), entry['sha256'])
            for workspace in ['webbie', 'deep-forage', 'communications']:
                self.assertIn(catalog.selected_id(workspace), catalog.by_id)
                self.assertTrue(catalog.path(workspace).is_file())
            for workspace in ['default', 'studio', 'author', 'forage', 'recovery']:
                self.assertEqual(catalog.selected_id(workspace), 'original')

    def test_choices_survive_restart_and_remain_independent(self):
        with tempfile.TemporaryDirectory() as config:
            catalog = module.WallpaperCatalog(ROOT, config)
            ident = catalog.defaults['deep-forage']
            catalog.select('studio', ident)
            reopened = module.WallpaperCatalog(ROOT, config)
            self.assertEqual(reopened.selected_id('studio'), ident)
            self.assertEqual(reopened.selected_id('author'), 'original')
            reopened.select('studio', 'original')
            self.assertEqual(reopened.path('studio'), reopened.original('studio'))
            with self.assertRaises(ValueError):
                reopened.select('studio', '../invalid')

    def test_corrupt_settings_and_missing_selection_fall_back(self):
        with tempfile.TemporaryDirectory() as config:
            catalog = module.WallpaperCatalog(ROOT, config)
            catalog.config.parent.mkdir(parents=True)
            catalog.config.write_text('broken')
            self.assertEqual(module.WallpaperCatalog(ROOT, config).selected_id('studio'), 'original')
            catalog.config.write_text(json.dumps({'studio': 'missing'}))
            self.assertEqual(module.WallpaperCatalog(ROOT, config).selected_id('studio'), 'original')


if __name__ == '__main__':
    unittest.main()
