"""Isolated Spider Audio Studio application package, never an OS installer."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

from studio.package.build_standalone import build,eligible,PACKAGE,VERSION


class StandaloneStudioTests(unittest.TestCase):
    def test_actual_native_studio_module_and_versioned_archive_are_present(self):
        root=Path(__file__).resolve().parents[1]
        chosen=eligible(root)
        self.assertGreaterEqual(len(chosen),40)
        for expected in (
            "studio/main.py",
            "studio/session_clip_edit.py",
            "studio/session_clip_dialog.py",
            "studio/session_waveform.py",
            "studio/session_mix.py",
            "studio/session_mix_dialog.py",
            "studio/instrument_workbench.py",
            "studio/audio_capture_panel.py",
            "studio/ai_panel.py",
            "system/apps.py",
            "the-web/shell/workspace_max_native.py",
            "spider_max_source/spider_monster/max_catalog.py",
            "branding/spider-apps/icons/spider-audio-studio.svg",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected,chosen)
        self.assertFalse(any(
            name.startswith(("tests/","webbie/","media/","author/"))
            for name in chosen))
        self.assertFalse(any(
            Path(name).suffix.lower() in {".wav",".mp3",".sf2",".sf3",".flac"}
            for name in chosen))

    def test_package_rechecks_source_integrity_and_refuses_overwrites(self):
        with tempfile.TemporaryDirectory() as scratch:
            root=Path(scratch)
            artifact=build(root)
            self.assertEqual(artifact.name,PACKAGE+".tar.gz")
            first=hashlib.sha256(artifact.read_bytes()).hexdigest()
            with self.assertRaises(FileExistsError):
                build(root)
            self.assertEqual(hashlib.sha256(artifact.read_bytes()).hexdigest(),first)
            extracted=root/"extracted"
            extracted.mkdir()
            with tarfile.open(artifact,"r:gz") as archive:
                members=archive.getmembers()
                self.assertGreaterEqual(len(members),43)
                self.assertTrue(all(
                    not Path(item.name).is_absolute() and
                    ".." not in Path(item.name).parts
                    for item in members))
                archive.extractall(extracted,filter="data")
            app=extracted/PACKAGE/"app"
            entry=extracted/PACKAGE/"run_spider_audio_studio.py"
            self.assertTrue((app/"studio/main.py").is_file())
            self.assertTrue((app/"system/apps.py").is_file())
            self.assertTrue((app/"the-web/shell/workspace_max_native.py").is_file())
            manifest=json.loads(
                (extracted/PACKAGE/"manifest.json").read_text())
            self.assertEqual(manifest["version"],VERSION)
            self.assertTrue(manifest["private_developer_preview"])
            env=dict(os.environ)
            env.setdefault("QT_QPA_PLATFORM","offscreen")
            verified=subprocess.run(
                [sys.executable,str(entry),"--verify-only"],
                text=True,capture_output=True,env=env,timeout=45)
            self.assertEqual(verified.returncode,0,verified.stderr)
            self.assertIn("PACKAGE VERIFIED",verified.stdout)
            imported=subprocess.run(
                [sys.executable,"-c",
                 "from studio.main import SpiderStudio; "
                 "from studio.session_clip_edit import normalize_clip_edit; "
                 "assert callable(normalize_clip_edit); "
                 "assert SpiderStudio.__name__ == 'SpiderStudio'"],
                env={**env,"PYTHONPATH":str(app)},
                text=True,capture_output=True,timeout=45)
            self.assertEqual(imported.returncode,0,imported.stderr)
            with (app/"studio/session_mix.py").open("a") as output:
                output.write("# injected owner-side modification\n")
            denied=subprocess.run(
                [sys.executable,str(entry),"--verify-only"],
                env=env,text=True,capture_output=True,timeout=45)
            self.assertNotEqual(denied.returncode,0)
            self.assertIn("verification failed",denied.stderr)

if __name__=="__main__":
    unittest.main()
