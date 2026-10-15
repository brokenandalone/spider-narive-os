import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    'normalize_layout', Path(__file__).resolve().parents[1] / 'distro/normalize-install-layout.py')
layout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(layout)


class LayerNormalizationTests(unittest.TestCase):
    def test_final_iso_menus_get_explicit_leaf_before_separator(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'grub.cfg').write_text('linux /casper/vmlinuz --- quiet splash\n'
                                        'linux (loop)/casper/vmlinuz nomodeset --- quiet\n')
            layout.normalize_grub(root)
            text = (root/'grub.cfg').read_text()
            self.assertIn('/casper/vmlinuz layerfs-path=standard.live.squashfs ---', text)
            self.assertIn('(loop)/casper/vmlinuz layerfs-path=standard.live.squashfs nomodeset', text)

    def test_grub_updates_normal_and_loopback_menus(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('grub.cfg', 'loopback.cfg'):
                (root/name).write_text('linux /casper/vmlinuz layerfs-path=minimal.standard.live.squashfs quiet\n')
            layout.normalize_grub(root)
            for name in ('grub.cfg', 'loopback.cfg'):
                self.assertIn('layerfs-path=standard.live.squashfs quiet', (root/name).read_text())

    def test_unknown_boot_layer_fails_without_partial_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expected = 'layerfs-path=minimal.standard.live.squashfs\n'
            (root/'grub.cfg').write_text(expected)
            (root/'loopback.cfg').write_text('layerfs-path=minimal.gpu.live.squashfs\n')
            with self.assertRaises(ValueError):
                layout.normalize_grub(root)
            self.assertEqual((root/'grub.cfg').read_text(), expected)

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
