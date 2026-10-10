import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    'stop_signal', ROOT/'webbie/agent/stop_signal.py')
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class StopSignalTests(unittest.TestCase):
    def test_signal_is_one_way_and_one_shot(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'private'
            self.assertFalse(m.consume_stop(folder))
            m.request_stop(folder)
            self.assertEqual((folder/'webbie-stop-request').read_bytes(), b'STOP\n')
            self.assertEqual((folder/'webbie-stop-request').stat().st_mode & 0o777, 0o600)
            self.assertTrue(m.consume_stop(folder))
            self.assertFalse(m.consume_stop(folder))

    def test_symlink_signal_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'private'
            folder.mkdir()
            target=Path(tmp)/'other'
            target.write_text('Do not touch')
            (folder/'webbie-stop-request').symlink_to(target)
            with self.assertRaises(PermissionError):
                m.request_stop(folder)
            self.assertFalse(m.consume_stop(folder))
            self.assertEqual(target.read_text(), 'Do not touch')


if __name__ == '__main__':
    unittest.main()
