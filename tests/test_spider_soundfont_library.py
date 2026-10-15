"""Test SoundFont auto-discovery is read-only, bounded and never downloads files."""
from pathlib import Path
import tempfile
import unittest

from studio.soundfont_library import discover_soundfonts, auto_soundfont

def font(path, payload=52):
    path.write_bytes(b"RIFF" + b"\x38\x00\x00\x00" + b"sfbk" + b"\0"*payload)
    return path

class SoundbankLibraryTests(unittest.TestCase):
    def test_discovers_only_valid_local_banks_and_prefers_larger(self):
        with tempfile.TemporaryDirectory() as root:
            folder=Path(root)
            small=font(folder/"small.sf2")
            big=font(folder/"big.sf3",100)
            (folder/"fake.sf2").write_text("Not a soundbank")
            (folder/"stuff.txt").write_text("unrelated")
            self.assertEqual(discover_soundfonts(roots=[folder]),[big,small])
            self.assertEqual(auto_soundfont(roots=[folder]),big)
            self.assertEqual(big.stat().st_size,112)

    def test_limits_and_nonrecursive_discovery(self):
        with tempfile.TemporaryDirectory() as root:
            folder=Path(root)
            nested=folder/"sub"
            nested.mkdir()
            font(nested/"nested.sf2")
            self.assertEqual(discover_soundfonts([folder]),[])
            with self.assertRaises(ValueError):
                discover_soundfonts([folder],max_items=0)

if __name__=="__main__":
    unittest.main()
