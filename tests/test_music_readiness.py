import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('music_readiness',
    Path(__file__).resolve().parents[1] / 'system/music_readiness.py')
music = importlib.util.module_from_spec(spec)
spec.loader.exec_module(music)


class MusicReadinessTests(unittest.TestCase):
    def test_counts_memory_and_only_reports_display_devices(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'meminfo'
            contents = 'MemTotal: 16000 kB\nMemAvailable: 8000 kB\n'
            path.write_text(contents)
            calls = []
            def run(args):
                calls.append(args)
                if args[0] == 'lspci':
                    return '00:02 VGA compatible controller [0300]: Test GPU\n00:04 Network controller [0280]: Private\n'
                return 'Test GPU, 8192, 123.45\n'
            result = music.inventory(path, tmp, run)
            self.assertEqual(result['memory']['MemTotal_bytes'], 16384000)
            self.assertEqual(result['nvidia_gpus'][0]['vram_mib'], 8192)
            self.assertEqual(len(result['display_controllers']), 1)
            self.assertNotIn('Private', str(result))
            self.assertEqual(path.read_text(), contents)
            self.assertEqual(len(calls), 2)
            self.assertNotIn('uuid', str(calls))

    def test_missing_tools_and_unreadable_memory_are_unknown(self):
        result = music.inventory('/nonexistent-spider-meminfo', runner=lambda args:None)
        self.assertIsNone(result['memory']['MemTotal_bytes'])
        self.assertEqual(result['nvidia_gpus'], [])
        self.assertIn('not yet tested', result['assessment'])

    def test_malformed_vram_is_not_treated_as_capacity(self):
        result = music.inventory('/nonexistent-spider-meminfo',
                                 runner=lambda args:'GPU, N/A, unknown\n')
        self.assertEqual(result['nvidia_gpus'], [])

    def test_command_timeout_is_nonfatal(self):
        with patch.object(music.shutil, 'which', return_value='/usr/bin/lspci'), \
             patch.object(music.subprocess, 'run', side_effect=music.subprocess.TimeoutExpired('lspci', 5)) as run:
            self.assertIsNone(music.read_command(['lspci', '-nn']))
            self.assertEqual(run.call_args.kwargs['timeout'], 5)
            self.assertNotIn('shell', run.call_args.kwargs)
