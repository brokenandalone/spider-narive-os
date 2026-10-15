"""Studio remains a package even when a reconciled PC retains studio/studio.py."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class StudioPackageIsolationTests(unittest.TestCase):
    def test_legacy_local_studio_py_cannot_shadow_package(self):
        # Disposable layout mimics the PC review; nothing is imported from
        # the owner's real files or audio/video devices.
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            pkg = root / 'studio'
            pkg.mkdir()
            (pkg / '__init__.py').write_text('"""Studio package"""\n')
            (pkg / 'studio.py').write_text('LEGACY_STUDIO = True\n')
            (pkg / 'owner_voice_model.py').write_text('MODEL_PRESENT = True\n')
            check = subprocess.run(
                [sys.executable, '-B', '-c',
                 'from studio import owner_voice_model; '
                 'assert owner_voice_model.MODEL_PRESENT; '
                 'assert hasattr(__import__("studio"), "__path__")'],
                cwd=root,
                env={**os.environ, 'PYTHONPATH': str(root)},
                text=True, capture_output=True, timeout=12,
            )
            self.assertEqual(check.returncode, 0, check.stderr)


if __name__ == '__main__':
    unittest.main()
