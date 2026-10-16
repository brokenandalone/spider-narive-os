"""Regression for the real Studio channel strip and non-destructive session FX.

No audio devices are opened. FFmpeg is optional for the end-to-end mix test.
"""
import json
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
import shutil
import tempfile
import unittest
import wave
from pathlib import Path

from studio.multitrack import export_session,SessionError
from studio.session_project import inspect_session
from studio.session_mix import mix_plan,ffmpeg_command,render_session
from studio.session_presets import save_preset,load_preset
from studio.session_track_fx import normalize_track_effects,track_effects_filter

class NativeMixerChannelFx(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        originals=[]
        for name,role,sample in (
            ("voice","lead_vocal",1000),("guitar","rhythm_guitar",260)):
            path=self.root/(name+".wav")
            with wave.open(str(path),"wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(44100)
                output.writeframes(
                    int(sample).to_bytes(2,"little",signed=True)*4410)
            originals.append({"path":str(path),"label":name,"role":role})
        self.originals=originals
        self.session_dir=export_session(
            originals,title="Spider channel FX",tempo_bpm=125,
            output_root=self.root/"sessions")
        self.session=inspect_session(self.session_dir)
        self.voice=self.session["tracks"][0]["filename"]
        self.guitar=self.session["tracks"][1]["filename"]

    def test_real_session_mixes_two_independent_track_fx_chains(self):
        chosen={
            self.voice:{"gain":1.1,"effects":{
                "bass_db":-4,"mids_db":2,"treble_db":3,
                "compression":True,"room":18}},
            self.guitar:{"pan":-.4,"effects":{
                "bass_db":5,"mids_db":0,"treble_db":-2,
                "compression":False,"room":0}},
        }
        plan=mix_plan(self.session,chosen)
        self.assertEqual(len(plan["active"]),2)
        self.assertEqual(plan["settings"][0]["effects"]["room"],18)
        self.assertEqual(plan["settings"][1]["effects"]["bass_db"],5)
        cmd=ffmpeg_command("/usr/bin/ffmpeg",plan,self.root/"fresh-mix.wav")
        graph=cmd[cmd.index("-filter_complex")+1]
        self.assertIn("equalizer=f=105:",graph)
        self.assertIn("equalizer=f=1050:",graph)
        self.assertIn("acompressor=threshold=0.25",graph)
        self.assertIn("aecho=in_gain=0.8",graph)
        self.assertEqual(graph.count("alimiter=limit=0.95"),1)
        self.assertTrue(graph.endswith("[out]"))
        self.assertEqual(cmd.count("-i"),2)
        self.assertEqual(normalize_track_effects(),{
            "bass_db":0,"mids_db":0,"treble_db":0,
            "compression":False,"room":0})
        self.assertEqual(track_effects_filter({}),"")

    def test_mix_preset_is_private_versioned_and_restores_fx(self):
        fx={"bass_db":8,"mids_db":-2,"compression":True,"room":10}
        settings={self.voice:{"effects":fx}}
        preset=save_preset(
            self.session,settings,name="Vocal warmth with acoustic guitar")
        self.assertEqual(preset.stat().st_mode&0o777,0o600)
        result=load_preset(self.session,preset)
        self.assertEqual(result["controls"][self.voice]["effects"]["bass_db"],8)
        self.assertEqual(result["controls"][self.voice]["effects"]["compression"],True)
        self.assertEqual(result["controls"][self.guitar]["effects"]["room"],0)
        self.assertEqual(
            inspect_session(self.session_dir)["tracks"],
            self.session["tracks"])

        # Backwards compatible with older pre-channel-FX presets.
        legacy_data=json.loads(preset.read_text())
        for value in legacy_data["controls"].values():
            value.pop("effects")
        legacy=self.session_dir/"mix-presets"/("preset-"+"a"*32+".json")
        legacy.write_text(json.dumps(legacy_data))
        restored=load_preset(self.session,legacy)
        self.assertEqual(restored["controls"][self.voice]["effects"],
                         normalize_track_effects())

    def test_effect_injection_and_bad_types_fail_before_ffmpeg(self):
        for bad in (
            {"bass_db":13},{"mids_db":"0;evil"},
            {"compression":1},{"compression":"true"},
            {"room":False},{"room":90},
            {"undocumented_chain":"amovie=file"},
        ):
            with self.subTest(bad=bad),self.assertRaises(SessionError):
                mix_plan(self.session,{self.voice:{"effects":bad}})
        for bad in (
            {"effects":[]},{"effects":"acompressor"},
            {"effects":{"bass_db":float("nan")}},
        ):
            with self.subTest(bad=bad),self.assertRaises(SessionError):
                mix_plan(self.session,{self.guitar:bad})
        with self.assertRaises(SessionError):
            mix_plan(self.session,{self.voice:{"x":1}})

    @unittest.skipUnless(shutil.which("ffmpeg"),"FFmpeg missing in CI runner")
    def test_actual_effect_mixed_wav_receipt_and_original_bytes_preserved(self):
        original=[Path(x["path"]).read_bytes() for x in self.originals]
        result=render_session(
            self.session_dir,
            controls={self.voice:{"effects":{
                "bass_db":4,"compression":True,"room":12}}},
            output_root=self.root/"mixed",timeout=30)
        with wave.open(str(result),"rb") as mixed:
            self.assertGreater(mixed.getnframes(),1000)
            self.assertEqual(mixed.getframerate(),48000)
            self.assertEqual(mixed.getnchannels(),2)
        receipt=json.loads((result.parent/"mix-receipt.json").read_text())
        self.assertEqual(receipt["tracks"][0]["effects"]["bass_db"],4)
        self.assertFalse(receipt["tracks"][1]["effects"]["compression"])
        self.assertTrue(receipt["original_tracks_preserved"])
        self.assertEqual(
            [Path(x["path"]).read_bytes() for x in self.originals],original)
        self.assertTrue(all(
            not (self.session_dir/filename).is_symlink()
            for filename in (self.voice,self.guitar)))

class ChannelStripUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from PyQt5.QtWidgets import QApplication
        except ImportError:
            raise unittest.SkipTest("Qt not installed")
        cls.qt=QApplication.instance() or QApplication([])

    def test_session_mixer_exposes_fx_and_restores_saved_track_parameters(self):
        from studio.session_mix_dialog import SessionMixDialog
        from unittest.mock import patch
        harness=NativeMixerChannelFx("test_real_session_mixes_two_independent_track_fx_chains")
        harness.setUp()
        self.addCleanup(harness.tmp.cleanup)
        dialog=SessionMixDialog()
        try:
            dialog.audit_done(harness.session,"")
            self.assertEqual(dialog.table.columnCount(),9)
            self.assertTrue(dialog.track_fx_button.isEnabled())
            self.assertEqual(dialog.table.currentRow(),0)
            class MockFxDialog:
                Accepted=1
                def __init__(self,*unused):
                    pass
                def exec_(self):return self.Accepted
                def values(self):
                    return normalize_track_effects(
                        {"bass_db":-5,"compression":True,"room":15})
            with patch("studio.session_mix_dialog.ChannelStripDialog",MockFxDialog):
                dialog.edit_track_effects()
            settings=dialog.mix_controls()
            self.assertEqual(settings[harness.voice]["effects"]["bass_db"],-5)
            self.assertTrue(settings[harness.voice]["effects"]["compression"])
            self.assertIn("Comp",dialog.table.item(0,8).text())
            saved=save_preset(harness.session,settings,name="Singer warm")
            dialog.refresh_presets()
            found=next(i for i in range(dialog.preset_list.count())
                       if dialog.preset_list.itemData(i)==str(saved))
            dialog.preset_list.setCurrentIndex(found)
            dialog.channel_effects[harness.voice]=normalize_track_effects()
            dialog.load_mix_preset()
            self.assertEqual(
                dialog.mix_controls()[harness.voice]["effects"]["room"],15)
            self.assertIn("Room",dialog.table.item(0,8).text())
        finally:
            dialog.close()

    def test_real_channel_strip_is_bounded_without_opening_audio(self):
        from studio.session_channel_strip import ChannelStripDialog
        dialog=ChannelStripDialog("Lead Vocal",{"bass_db":5,"room":12})
        try:
            self.assertEqual(dialog.values()["bass_db"],5)
            self.assertEqual(dialog.values()["room"],12)
            dialog.controls["treble_db"].setValue(-6)
            dialog.compression.setChecked(True)
            self.assertEqual(dialog.values()["treble_db"],-6)
            self.assertTrue(dialog.values()["compression"])
        finally:
            dialog.close()

if __name__=="__main__":
    unittest.main()
