"""Developer preview package safeguards; no installed-system access."""
import importlib.util
import tarfile
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("preview",ROOT/"tools/build_spider_audio_preview.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class PreviewPackagingTests(unittest.TestCase):
    def test_real_source_contains_standalone_entry_and_not_secrets(self):
        files=dict(mod.source_files(ROOT))
        self.assertIn("studio/main.py",files)
        self.assertIn("studio/bin/studio",files)
        self.assertIn("LICENSE",files)
        self.assertTrue(all(not mod.PRIVATE.search("/"+name) for name in files))
    def test_preview_contains_launch_and_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/"preview.tar.gz"
            result=mod.preview_build(ROOT,output)
            self.assertGreater(result["source_files"],10)
            with tarfile.open(output) as tar:
                names=tar.getnames()
                self.assertIn("spider-audio-studio-preview/RUN_PREVIEW.sh",names)
                self.assertIn("spider-audio-studio-preview/PREVIEW_NOTICE.txt",names)
                self.assertTrue(all(m.isfile() for m in tar.getmembers()))
            with self.assertRaises(FileExistsError):
                mod.preview_build(ROOT,output)
    def test_bad_output_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                mod.preview_build(ROOT,Path(tmp)/"bad.zip")

if __name__=="__main__":
    unittest.main()
