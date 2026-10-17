"""Real protected local song library and app reopen workflow."""
import json
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from pathlib import Path
import tempfile
import unittest
import wave
from unittest.mock import patch

from studio.multitrack import export_session
from studio.session_library import recent_sessions

def create_wav(path):
    with wave.open(str(path),"wb") as writer:
        writer.setnchannels(1)
        writer.setframerate(48000)
        writer.setsampwidth(2)
        writer.writeframes(b"\x12\x00"*4800)

class RecentSongs(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder=Path(self.tmp.name)
        track=self.folder/"Owner-Guitar.wav"
        create_wav(track)
        self.output=self.folder/"Private Sessions"
        self.alpha=export_session(
            [{"path":str(track),"role":"rhythm_guitar","label":"Guitar"}],
            title="Broken Sorrow - Song One",tempo_bpm=96,output_root=self.output)
        self.beta=export_session(
            [{"path":str(track),"role":"lead_guitar","label":"Lead"}],
            title="Broken Sorrow - Song Two",tempo_bpm=105,output_root=self.output)

    def test_sessions_are_read_only_bounded_and_not_recursively_discovered(self):
        entries=recent_sessions(self.output)
        self.assertEqual(len(entries),2)
        self.assertEqual({x["title"] for x in entries},{
            "Broken Sorrow - Song One","Broken Sorrow - Song Two"})
        self.assertEqual({x["track_count"] for x in entries},{1})
        self.assertEqual({x["bpm"] for x in entries},{96,105})
        self.assertFalse(recent_sessions(self.folder/"none"))
        broken=self.output/"session-not-a-song"
        broken.mkdir()
        (broken/"session.json").write_text("{bad json")
        linked=self.output/"session-link"
        linked.symlink_to(self.alpha,target_is_directory=True)
        self.assertEqual(len(recent_sessions(self.output)),2)
        nested=self.output/"nested"
        nested.mkdir()
        deep=nested/"fake-session"
        deep.mkdir()
        (deep/"session.json").write_text(
            (self.alpha/"session.json").read_text())
        self.assertEqual(len(recent_sessions(self.output)),2)

    def test_only_selected_saved_songs_open_actual_existing_mixer(self):
        from PyQt5.QtWidgets import QApplication
        from studio.saved_songs_dialog import SavedSongsDialog
        app=QApplication.instance() or QApplication([])
        dialog=SavedSongsDialog(root=self.output)
        try:
            self.assertEqual(dialog.table.rowCount(),2)
            self.assertTrue(dialog.open_button.isEnabled())
            class FakeMixer:
                received=[]
                def __init__(self,folder,parent):
                    self.received.append(Path(folder))
                def exec_(self):
                    return 0
            with patch("studio.saved_songs_dialog.SessionMixDialog",FakeMixer):
                dialog.table.setCurrentCell(0,0)
                dialog.open_selected()
            self.assertIn(dialog.selected_path,(self.alpha,self.beta))
            self.assertEqual(FakeMixer.received,[dialog.selected_path])
            self.assertTrue((dialog.selected_path/"session.json").is_file())
        finally:
            dialog.close()

if __name__=="__main__":
    unittest.main()
