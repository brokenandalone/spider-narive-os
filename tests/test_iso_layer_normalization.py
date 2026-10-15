import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    'normalize_layout', Path(__file__).resolve().parents[1] / 'distro/normalize-install-layout.py')
layout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(layout)


class LayerNormalizationTests(unittest.TestCase):
    def catalog(self):
        return {'version': 2, 'kernel': {'default': 'linux-generic'}, 'sources': [
            {'id': 'minimal', 'path': 'minimal.squashfs', 'default': False},
            {'id': 'studio', 'path': 'minimal.standard.squashfs', 'size': 100,
             'default': True, 'type': 'fsimage-layered',
             'variations': {'default': {'path': 'minimal.standard.squashfs', 'size': 100}}}]}

    def test_full_studio_source_preserves_identity_and_kernel(self):
        original = self.catalog()
        before = copy.deepcopy(original)
        result = layout.normalize(original)
        self.assertEqual(original, before)
        self.assertEqual(result['kernel'], before['kernel'])
        self.assertEqual(len(result['sources']), 1)
        source = result['sources'][0]
        self.assertEqual(source['id'], 'studio')
        self.assertEqual(source['path'], 'standard.squashfs')
        self.assertEqual(source['variations']['default']['path'], 'standard.squashfs')

    def test_new_variation_or_language_layers_fail_closed(self):
        for change in ('path', 'languages', 'default', 'type'):
            with self.subTest(change=change):
                catalog = self.catalog()
                source = catalog['sources'][1]
                if change == 'path':
                    source['variations']['gpu'] = {'path': 'minimal.standard.gpu.squashfs'}
                elif change == 'languages':
                    source['preinstalled_langs'] = ['en']
                elif change == 'default':
                    catalog['sources'][0]['default'] = True
                else:
                    source['type'] = 'unknown'
                with self.assertRaises(ValueError):
                    layout.normalize(catalog)
