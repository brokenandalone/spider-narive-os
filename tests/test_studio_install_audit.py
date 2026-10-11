"""A read-only PC install audit must never change the owner installation."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'studio/package/inspect-studio-install.py'
spec = importlib.util.spec_from_file_location('studio_install_audit', SCRIPT)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class StudioInstallAuditTests(unittest.TestCase):
    def test_reports_missing_and_different_files_without_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'source'
            installed = Path(tmp) / 'installed'
            for root in (source, installed):
                (root / 'studio').mkdir(parents=True)
            (source / 'studio/main.py').write_text('new-source')
            (installed / 'studio/main.py').write_text('owner-install')
            before = (installed / 'studio/main.py').read_bytes()
            details = helper.source_status(source, installed)
            self.assertEqual(details['studio/main.py'], 'different_inspect_before_replacing')
            self.assertEqual(details['studio/band_projects.py'], 'source_not_present')
            self.assertEqual(before, (installed / 'studio/main.py').read_bytes())
            (installed / 'studio/main.py').write_text('new-source')
            self.assertEqual(helper.source_status(source, installed)['studio/main.py'], 'matches_source')
            (installed / 'studio/main.py').unlink()
            self.assertEqual(helper.source_status(source, installed)['studio/main.py'], 'not_installed')

    def test_symlink_paths_are_not_read_or_followed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b = root / 'source', root / 'installed'
            for folder in (a, b):
                (folder / 'studio').mkdir(parents=True)
            target = root / 'secret'
            target.write_text('private local audio credential')
            (a / 'studio/main.py').write_text('new')
            (b / 'studio/main.py').symlink_to(target)
            info = helper.source_status(a, b)
            self.assertEqual(info['studio/main.py'], 'symlink_review_required')
            self.assertEqual(target.read_text(), 'private local audio credential')

    def test_checks_exact_ffmpeg_filter_names_only(self):
        listing = (' .. amix A->A Mix audio\n'
                   ' .. alimiter A->A Limiter\n'
                   ' .. stereotools A->A Stereo\n'
                   ' .. adelay A->A Delay\n'
                   ' .. aformat A->A Format\n'
                   ' .. fakefilter A->A mentions amix\n')
        with (patch.object(helper.shutil, 'which', return_value='/usr/bin/ffmpeg'),
              patch.object(helper.subprocess, 'run', return_value=subprocess.CompletedProcess(
                  args=[], returncode=0, stdout=listing, stderr=''))):
            report = helper.ffmpeg_status()
        self.assertEqual(report['missing_filters'], [])
        self.assertIn('adelay', report['required_filters'])
        with patch.object(helper.shutil, 'which', return_value=None):
            self.assertFalse(helper.ffmpeg_status()['available'])


if __name__ == '__main__':
    unittest.main()
