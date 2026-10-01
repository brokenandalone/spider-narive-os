import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]

def module_at(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

catalog = module_at('verify_catalog', ROOT / 'distro/verify-install-catalog.py')
seed = module_at('make_seed', ROOT / 'tests/make-install-seed.py')

class InstallationValidationTests(unittest.TestCase):
    def make_casper(self, directory):
        path = Path(directory)
        (path / 'standard.squashfs').write_bytes(b'image')
        (path / 'standard.size').write_text('100')
        self.sources = [{'id': 'studio', 'path': 'standard.squashfs', 'size': 100, 'default': True}]
        self.write_sources(path)
        return path

    def write_sources(self, path):
        (path / 'install-sources.yaml').write_text(yaml.safe_dump(self.sources))

    def test_source_requires_real_image_and_current_size(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_casper(directory)
            self.assertEqual(catalog.verify(path), 'studio')
            self.sources[0]['size'] = 1
            self.write_sources(path)
            with self.assertRaisesRegex(ValueError, 'stale'):
                catalog.verify(path)
            self.sources[0]['size'] = 100
            self.write_sources(path)
            (path / 'standard.squashfs').unlink()
            with self.assertRaisesRegex(ValueError, 'Missing'):
                catalog.verify(path)

    def test_unmodified_default_cannot_bypass_spider_image(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_casper(directory)
            (path / 'minimal.squashfs').write_bytes(b'old image')
            self.sources[0]['default'] = False
            self.sources.append({'id': 'minimal', 'path': 'minimal.squashfs', 'size': 5, 'default': True})
            self.write_sources(path)
            with self.assertRaisesRegex(ValueError, 'Default install'):
                catalog.verify(path)

    def test_test_seed_uses_only_virtual_disk_and_correct_source(self):
        config = seed.make_config('upstream-studio-id')['autoinstall']
        self.assertEqual(config['source']['id'], 'upstream-studio-id')
        self.assertEqual(config['storage']['layout']['match'], {'path': '/dev/vda'})
        self.assertEqual(config['shutdown'], 'poweroff')
        self.assertFalse(config['refresh-installer']['update'])

    def test_cleanup_does_not_disable_failure_handling(self):
        text = (ROOT / 'distro/build-iso.sh').read_text()
        cleanup = text[text.index('cleanup() ('):text.index('\nunmount_chroot()')]
        script = 'set -e\nROOTFS=/nonexistent\nISO_MOUNT=/nonexistent\n' + cleanup + '\ncleanup\nfalse\necho MISSED_ERROR\n'
        result = subprocess.run(['bash', '-c', script], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('MISSED_ERROR', result.stdout)

if __name__ == '__main__':
    unittest.main()
