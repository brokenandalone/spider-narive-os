"""Spider saved-song portable backup and malicious/damaged restore rejection."""
import hashlib
import json
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from pathlib import Path
import tempfile
import unittest
import wave
import zipfile

from studio.multitrack import SessionError,export_session
from studio.session_project import inspect_session
from studio.session_presets import save_preset,load_preset
from studio.session_archive import create_backup,restore_backup,ARCHIVE_NAME

def tone(path):
    with wave.open(str(path),"wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(48000)
        audio.writeframes(b"\x12\x22"*4800)

class PortableSongBackupTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.track=self.root/"BrokenSorrowGuitar.wav"
        tone(self.track)
        self.sessions=self.root/"Saved Songs"
        self.folder=export_session(
            [{"path":str(self.track),"role":"lead_guitar",
              "label":"Broken Sorrow lead"}],
            title="Broken Sorrow - What the Silence Kept",tempo_bpm=96,
            output_root=self.sessions)
        self.session=inspect_session(self.folder)
        self.source_digest=hashlib.sha256(self.track.read_bytes()).hexdigest()
        self.preset=save_preset(
            self.session,{self.session["tracks"][0]["filename"]:
                          {"gain":0.6,"pan":0.3}},
            name="Private Guitar Mix")
        self.original_hash=self.session["tracks"][0]["sha256"]

    def test_verifiable_non_overwriting_backup_restore_and_mix_presets(self):
        backup=self.root/"WhatTheSilenceKept.spiderstudio.zip"
        created=create_backup(self.folder,backup)
        self.assertEqual(created,backup)
        self.assertEqual(backup.stat().st_mode&0o777,0o600)
        with zipfile.ZipFile(backup) as package:
            names=package.namelist()
            self.assertIn("session.json",names)
            self.assertIn(ARCHIVE_NAME,names)
            self.assertIn(self.session["tracks"][0]["filename"],names)
            self.assertIn("mix-presets/"+self.preset.name,names)
            self.assertNotIn("owner guitar source folder",names)
            self.assertTrue(all(
                package.getinfo(name).compress_type==zipfile.ZIP_STORED
                for name in names))
        with self.assertRaises(SessionError):
            create_backup(self.folder,backup)
        restored=restore_backup(backup,output_root=self.sessions)
        self.assertNotEqual(restored,self.folder)
        self.assertTrue(restored.is_dir())
        checked=inspect_session(restored)
        self.assertEqual(checked["title"],self.session["title"])
        self.assertEqual(checked["tracks"][0]["sha256"],self.original_hash)
        restored_preset=load_preset(
            checked,restored/"mix-presets"/self.preset.name)
        self.assertEqual(
            restored_preset["controls"][checked["tracks"][0]["filename"]]["gain"],
            0.6)
        self.assertEqual(
            hashlib.sha256(self.track.read_bytes()).hexdigest(),self.source_digest)
        self.assertTrue((self.folder/"session.json").is_file())

    def test_unsafe_zip_paths_and_malformed_indices_are_rejected(self):
        original=list(self.sessions.iterdir())
        bad=self.root/"bad.zip"
        with zipfile.ZipFile(bad,"w") as package:
            package.writestr("../../outside.wav",b"OWNER DATA")
            package.writestr("session.json",b"{}")
            package.writestr(ARCHIVE_NAME,json.dumps({
                "schema":1,"application":"Spider Audio Studio","members":{}}))
        with self.assertRaises(SessionError):
            restore_backup(bad,output_root=self.sessions)
        self.assertFalse((self.root/"outside.wav").exists())
        self.assertEqual(set(self.sessions.iterdir()),set(original))
        broken=self.root/"modified.zip"
        good=self.root/"original.zip"
        create_backup(self.folder,good)
        with zipfile.ZipFile(good,"r") as from_archive:
            with zipfile.ZipFile(broken,"w",compression=zipfile.ZIP_STORED) as to_archive:
                for name in from_archive.namelist():
                    content=from_archive.read(name)
                    if name==self.session["tracks"][0]["filename"]:
                        content=bytes(len(content))  # valid size, wrong SHA
                    to_archive.writestr(name,content)
        with self.assertRaises(SessionError):
            restore_backup(broken,output_root=self.sessions)
        self.assertEqual(set(self.sessions.iterdir()),set(original))
        self.assertEqual(self.session["tracks"][0]["sha256"],self.original_hash)

    def test_backup_rejects_linked_presets_and_a_linked_output(self):
        link=self.folder/"mix-presets"/"preset-"+"a"*32+".json"
        link.symlink_to(self.preset)
        with self.assertRaises(SessionError):
            create_backup(self.folder,self.root/"a.zip")
        self.assertFalse((self.root/"a.zip").exists())
        link.unlink()
        redirect=self.root/"backup.zip"
        redirect.symlink_to(self.track)
        with self.assertRaises(SessionError):
            create_backup(self.folder,redirect)
        self.assertEqual(
            hashlib.sha256(self.track.read_bytes()).hexdigest(),self.source_digest)

class ArchiveUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt5.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([])

    def test_saved_song_ui_has_explicit_backup_and_restore_actions(self):
        from studio.saved_songs_dialog import SavedSongsDialog
        with tempfile.TemporaryDirectory() as scratch:
            ui=SavedSongsDialog(root=Path(scratch))
            try:
                self.assertFalse(ui.backup_button.isEnabled())
                self.assertTrue(ui.restore_button.isEnabled())
                self.assertIsNone(ui.archive_worker)
            finally:
                ui.close()

if __name__=="__main__":
    unittest.main()
