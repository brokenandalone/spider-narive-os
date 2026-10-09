import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'the-web/shell'))
spec = importlib.util.spec_from_file_location('system_status', ROOT / 'the-web/shell/system_status.py')
status = importlib.util.module_from_spec(spec); spec.loader.exec_module(status)


class SystemStatusTests(unittest.TestCase):
    def test_service_missing_is_not_confused_with_inactive(self):
        with patch.object(status, 'run', return_value=(0, 'LoadState=not-found\nActiveState=inactive\n')) as run:
            row = status.service_status(('Webbie', 'webbie.service', True))
        self.assertEqual(row[2], 'not installed')
        self.assertEqual(run.call_args.args[0], ['systemctl', '--user', 'show', 'webbie.service', '--property=LoadState,ActiveState,SubState,UnitFileState'])

    def test_probe_timeout_is_bounded_and_reported(self):
        with patch.object(status.subprocess, 'run', side_effect=subprocess.TimeoutExpired('systemctl', 2)) as run:
            self.assertEqual(status.run(['systemctl', 'show']), (None, ''))
        self.assertEqual(run.call_args.kwargs['timeout'], 2)

    def test_backup_listing_preserves_files_and_rejects_symlinks(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); backup = root / 'upgrade-backups'; backup.mkdir()
            original = backup / 'the-web-20261008-201419'; original.mkdir()
            (original / 'private.txt').write_text('must remain untouched')
            (backup / 'the-web-link').symlink_to(original, target_is_directory=True)
            rows = status.backup_rows(root, root / 'no-media')
            self.assertEqual(len(rows), 1)
            self.assertEqual((original / 'private.txt').read_text(), 'must remain untouched')
            self.assertNotIn('must remain untouched', str(rows))

    def test_audio_falls_back_when_wpctl_fails(self):
        with patch.object(status, 'service_states', return_value=[]), patch.object(status.shutil, 'which', return_value='/bin/tool'), patch.object(status, 'run', side_effect=[(1, ''), (0, 'Server Name: PulseAudio (on PipeWire)')]) as run:
            report = status.collect(ROOT)
        self.assertIn('PipeWire', report['audio'])
        self.assertEqual(run.call_args.args[0], ['pactl', 'info'])


if __name__ == '__main__': unittest.main()
