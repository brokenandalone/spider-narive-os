"""Wave 13: real native WAV import, protected song session and internal playback.

No actual audio input device is opened. Where QtMultimedia cannot play on
headless runners, the fallback is verified without claiming live sound output.
"""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
import json
import shutil
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from studio.multitrack import SessionError
from studio.stem_import_panel import StemImportPanel,infer_role,prepare_tracks
from studio.session_project import inspect_session
from studio.session_mix import render_session
from studio.session_mix_player import MixPlaybackBar,nice_time


def wav(path):
    with wave.open(str(path),"wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(48000)
        stream.writeframes(b"\x20\x00"*4800)


class ImportedBrokenSorrowSong(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.paths=[]
        for label in (
            "Broken_Sorrow_Rhythm_L_96BPM_Dm.wav",
            "Broken_Sorrow_Rhythm_R_96BPM_Dm.wav",
            "Broken_Sorrow_Lead_96BPM_Dm.wav",
            "Broken_Sorrow_Ambient_96BPM_Dm.wav",
        ):
            path=self.root/label
            wav(path)
            self.paths.append(path)
        self.original={p:p.read_bytes() for p in self.paths}

    def test_inference_matches_actual_guitar_pack_with_no_unrequested_roles(self):
        self.assertEqual([infer_role(p.name) for p in self.paths],[
            "rhythm_guitar","rhythm_guitar",
            "lead_guitar","other_instrument"])
        self.assertEqual(infer_role("Lead_Vocals.wav"),"lead_vocal")
        self.assertEqual(infer_role("Piano and Keys.wav"),"piano_keys")
        self.assertEqual(infer_role("My Unknown Instrument.wav"),
                         "other_instrument")

    def test_song_stem_import_validates_and_preserves_originals(self):
        entries=prepare_tracks(self.paths)
        self.assertEqual([a["role"] for a in entries],[
            "rhythm_guitar","rhythm_guitar","lead_guitar","other_instrument"])
        self.assertEqual(entries[0]["label"],self.paths[0].stem)
        with self.assertRaises(SessionError):
            prepare_tracks([self.paths[0],self.paths[0]])
        link=self.root/"link.wav"
        link.symlink_to(self.paths[0])
        with self.assertRaises(SessionError):
            prepare_tracks([link])
        with self.assertRaises(SessionError):
            prepare_tracks(self.paths,[1,2,3,4])
        with self.assertRaises(SessionError):
            prepare_tracks(self.paths+[self.paths[0]]*21)
        for path,original in self.original.items():
            self.assertEqual(path.read_bytes(),original)

    @unittest.skipUnless(shutil.which("ffmpeg"),"FFmpeg unavailable")
    def test_imported_song_mixes_all_four_guitars_with_real_wav_audio(self):
        from studio.multitrack import export_session
        session=export_session(
            prepare_tracks(self.paths),title="Broken Sorrow - What the Silence Kept",
            tempo_bpm=96,output_root=self.root/"sessions")
        verified=inspect_session(session)
        self.assertEqual(len(verified["tracks"]),4)
        self.assertTrue(verified["verified"])
        result=render_session(session,output_root=self.root/"mixes",timeout=35)
        with wave.open(str(result),"rb") as mix:
            self.assertEqual(mix.getframerate(),48000)
            self.assertEqual(mix.getsampwidth(),3)
            self.assertEqual(mix.getnchannels(),2)
            self.assertGreater(mix.getnframes(),0)
        receipt=json.loads((result.parent/"mix-receipt.json").read_text())
        self.assertEqual(len(receipt["active_filenames"]),4)
        for path,original in self.original.items():
            self.assertEqual(path.read_bytes(),original)


class ImportAndTransportUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from PyQt5.QtWidgets import QApplication
        except ImportError:
            raise unittest.SkipTest("Qt is not available")
        cls.app=QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.paths=[]
        for name in ("Rhythm_L.wav","Rhythm_R.wav","Lead.wav","Ambient.wav"):
            path=self.root/name
            wav(path)
            self.paths.append(path)

    def test_native_import_panel_roles_and_session_worker(self):
        from studio.stem_import_panel import StemImportWorker
        from unittest.mock import patch
        panel=StemImportPanel()
        try:
            panel.add_paths(self.paths)
            self.assertEqual(panel.table.rowCount(),4)
            self.assertEqual(panel.items[0]["role"],"rhythm_guitar")
            self.assertEqual(panel.items[2]["role"],"lead_guitar")
            self.assertEqual(panel.items[3]["role"],"other_instrument")
            guitar=panel.table.cellWidget(3,1)
            guitar.setCurrentIndex(guitar.findData("lead_guitar"))
            self.assertEqual(panel.items[3]["role"],"lead_guitar")
            panel.song.setText("Broken Sorrow - Guitar Demo")
            panel.tempo.setValue(96)
            entries=prepare_tracks(
                [item["path"] for item in panel.items],
                [item["role"] for item in panel.items])
            with patch("studio.stem_import_panel.export_session") as save:
                # Use the real exporter underneath, but choose a temporary
                # output directory rather than the user's Documents.
                from studio.multitrack import export_session
                save.side_effect=lambda *args,**kwargs:export_session(
                    *args,**{**kwargs,"output_root":self.root/"songs"})
                worker=StemImportWorker(entries,panel.song.text(),96,panel)
                results=[]
                worker.created.connect(lambda folder,error:results.append(
                    (folder,error)))
                worker.run()
            self.assertEqual(len(results),1)
            self.assertFalse(results[0][1])
            imported=Path(results[0][0])
            self.assertEqual(inspect_session(imported)["tempo_bpm"],96)
            panel.session_created(str(imported),"")
            self.assertTrue(panel.mixer_button.isEnabled())
            class FakeMixer:
                def __init__(self,folder,owner):
                    self.folder=folder
                def exec_(self):
                    return 0
            with patch("studio.stem_import_panel.SessionMixDialog",FakeMixer):
                panel.open_mixer()
            self.assertEqual(panel.last_mixer.folder,str(imported))
        finally:
            panel.close()

    def test_real_in_app_transport_has_position_and_media_safety(self):
        output=self.root/"fresh-render.wav"
        wav(output)
        transport=MixPlaybackBar()
        try:
            self.assertEqual(nice_time(62500),"1:02")
            self.assertEqual(nice_time(-3),"0:00")
            link=self.root/"linked.wav"
            link.symlink_to(output)
            self.assertFalse(transport.load(link))
            self.assertIsNone(transport.file)
            loaded=transport.load(output)
            self.assertEqual(transport.file,output)
            if transport.player is not None:
                self.assertTrue(loaded)
                self.assertTrue(transport.play_button.isEnabled())
                transport._duration(123000)
                self.assertEqual(transport.seek.maximum(),123000)
                transport._position(32000)
                self.assertIn("0:32",transport.elapsed.text())
                transport.play()
                transport.pause()
                transport.stop()
            else:
                self.assertFalse(loaded)
                self.assertIn("system player",transport.status.text())
        finally:
            transport.shutdown()
            transport.close()

    def test_original_studio_has_integrated_import_and_mixer_transport(self):
        from studio.main import SpiderStudio
        window=SpiderStudio()
        try:
            names=[
                window.tool_tabs.tabText(i)
                for i in range(window.tool_tabs.count())]
            self.assertIn("Import WAVs · Create Song",names)
            self.assertEqual(window.stem_import_panel.table.rowCount(),0)
            from studio.session_mix_dialog import SessionMixDialog
            mixer=SessionMixDialog()
            try:
                self.assertIsInstance(mixer.internal_player,MixPlaybackBar)
                self.assertFalse(mixer.internal_player.play_button.isEnabled())
            finally:
                mixer.close()
        finally:
            window.close()

if __name__=="__main__":
    unittest.main()
