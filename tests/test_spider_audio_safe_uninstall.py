"""A single Spider beta can be removed without deleting music or other versions."""
import os
import tempfile
import tarfile
import unittest
from pathlib import Path

from studio.package.build_standalone import build,VERSION,PACKAGE
from studio.package.install_for_user import install
from studio.package.remove_beta import remove_version,installed_versions

class SafeRemovalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.archive=build(self.root)
        unpack=self.root/"unpacked"
        unpack.mkdir()
        with tarfile.open(self.archive,"r:gz") as tar:
            tar.extractall(unpack,filter="data")
        self.bundle=unpack/PACKAGE
        self.home=self.root/"musician"
        self.home.mkdir()
        self.song=self.home/"Broken Sorrow - original.wav"
        self.song.write_bytes(b"NEVER REMOVE A CUSTOMER RECORDING")

    def test_remove_one_verified_version_and_keep_other_versions_and_music(self):
        location,desktop=install(self.bundle,home=self.home)
        earlier=location.parent/"0.13.0-dev"
        earlier.mkdir()
        (earlier/"owner-added.txt").write_text("OLDER VERSION PRESERVED")
        self.assertIn(VERSION,installed_versions(self.home))
        cache=location/"app"/"studio"/"__pycache__"
        cache.mkdir(exist_ok=True)
        (cache/"main.cpython-311.pyc").write_bytes(b"compiled bytecode")
        removed,shortcut=remove_version(VERSION,home=self.home)
        self.assertEqual((removed,shortcut),(location,desktop))
        self.assertFalse(location.exists())
        self.assertFalse(desktop.exists())
        self.assertTrue(earlier.is_dir())
        self.assertEqual((earlier/"owner-added.txt").read_text(),
                         "OLDER VERSION PRESERVED")
        self.assertEqual(self.song.read_bytes(),
                         b"NEVER REMOVE A CUSTOMER RECORDING")
        self.assertNotIn(VERSION,installed_versions(self.home))
        with self.assertRaises(ValueError):
            remove_version(VERSION,home=self.home)
        # An owner may reinstall exactly the same version after safe removal.
        fresh,menu=install(self.bundle,home=self.home)
        self.assertTrue(fresh.is_dir())
        self.assertTrue(menu.is_file())

    def test_unknown_owner_file_or_modified_source_blocks_removal(self):
        location,desktop=install(self.bundle,home=self.home)
        unexpected=location/"customer-private.txt"
        unexpected.write_text("a file the musician chose to save here")
        with self.assertRaisesRegex(ValueError,"Unexpected file"):
            remove_version(VERSION,home=self.home)
        self.assertTrue(location.is_dir())
        self.assertTrue(desktop.exists())
        self.assertEqual(unexpected.read_text(),
                         "a file the musician chose to save here")
        unexpected.unlink()
        core=location/"app"/"studio"/"main.py"
        with core.open("a") as writer:
            writer.write("\n# user-customized code")
        with self.assertRaises(ValueError):
            remove_version(VERSION,home=self.home)
        self.assertTrue(location.is_dir())
        self.assertTrue(desktop.exists())
        self.assertEqual(self.song.read_bytes(),
                         b"NEVER REMOVE A CUSTOMER RECORDING")

    def test_modified_desktop_entry_or_symlink_blocks_removal(self):
        location,desktop=install(self.bundle,home=self.home)
        entry=desktop.read_text()
        desktop.write_text(entry.replace(
            "X-SpiderStudio-PrivateBeta=true",
            "X-SpiderStudio-PrivateBeta=false"))
        with self.assertRaises(ValueError):
            remove_version(VERSION,home=self.home)
        self.assertTrue(location.is_dir())
        desktop.write_text(entry)
        folder=location/"app"/"studio"/"shortcut.wav"
        folder.symlink_to(self.song)
        with self.assertRaises(ValueError):
            remove_version(VERSION,home=self.home)
        self.assertTrue(self.song.is_file())
        self.assertTrue(location.is_dir())

if __name__=="__main__":
    unittest.main()
