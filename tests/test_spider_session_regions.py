"""Wave 12: multi-region source edits, private presets and real FFmpeg mixing.

A source WAV can now contribute multiple independently trimmed/timed regions
without being cut, rewritten, or copied. Tests do not open audio hardware.
"""
import json
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
import shutil
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from studio.multitrack import SessionError,export_session
from studio.session_project import inspect_session
from studio.session_regions import (
    REGION_FIELDS,normalize_regions,timeline_filter_segments)
from studio.session_mix import mix_plan,ffmpeg_command,render_session
from studio.session_presets import save_preset,load_preset
from studio.session_clip_edit import DEFAULTS


def fixture(path):
    with wave.open(str(path),"wb") as wav:
        wav.setnchannels(1)
        wav.setframerate(48000)
        wav.setsampwidth(2)
        for base in range(0,48000,4800):
            payload=bytearray()
            for i in range(base,min(base+4800,48000)):
                val=(10000 if i<24000 else -6000)
                payload.extend(val.to_bytes(2,"little",signed=True))
            wav.writeframesraw(payload)
        wav.writeframes(b"")


def levels(path,at,duration=.01):
    with wave.open(str(path),"rb") as stream:
        rate=stream.getframerate()
        stream.setpos(min(stream.getnframes()-1,round(at*rate)))
        data=stream.readframes(round(duration*rate))
        width=stream.getsampwidth()
        channels=stream.getnchannels()
    return sum(abs(int.from_bytes(data[i:i+width],"little",signed=True))
               for i in range(0,len(data),width))/max(1,len(data)//width)


def first_region(**overrides):
    return {"start_ms":100,"end_ms":300,"at_ms":0,
            "fade_in_ms":0,"fade_out_ms":0,**overrides}


class RegionDecisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.src=self.root/"owner-original.wav"
        fixture(self.src)
        self.original=self.src.read_bytes()
        self.folder=export_session(
            [{"path":str(self.src),"role":"lead_vocal","label":"Owner vocals"}],
            title="Spider multi-region song",output_root=self.root/"sessions")
        self.session=inspect_session(self.folder)
        self.track=self.session["tracks"][0]
        self.filename=self.track["filename"]

    def test_validated_audio_regions_use_separate_source_and_destination(self):
        edits=[first_region(),first_region(
            start_ms=600,end_ms=900,at_ms=700,fade_in_ms=40,fade_out_ms=60)]
        normalized,final=normalize_regions(self.track,edits)
        self.assertEqual(normalized,edits)
        self.assertAlmostEqual(final,1.0)
        self.assertEqual(normalize_regions(self.track,None),([],0.))
        self.assertEqual(normalize_regions(self.track,[]),([],0.))
        parts,pad=timeline_filter_segments(0,self.track,edits)
        graph=";".join(parts)
        self.assertIn("[0:a:0]asplit=2",graph)
        self.assertIn("atrim=start_sample=4800:end_sample=14400",graph)
        self.assertIn("atrim=start_sample=28800:end_sample=43200",graph)
        self.assertIn("adelay=700:all=1",graph)
        self.assertIn("afade=t=in:st=0:d=0.040",graph)
        self.assertIn("amix=inputs=2",graph)
        self.assertEqual(pad,"[regions0]")
        plan=mix_plan(self.session,{self.filename:{"regions":edits}})
        self.assertEqual(plan["active"][0]["region_end"],1.)
        cmd=ffmpeg_command("/usr/bin/ffmpeg",plan,self.root/"fresh.wav")
        graph=cmd[cmd.index("-filter_complex")+1]
        self.assertEqual(cmd.count("-i"),1)
        self.assertIn("[regions0]",graph)
        self.assertEqual(graph.count("alimiter=limit=0.95"),1)

    def test_duplicate_overlap_and_max_regions_are_bounded(self):
        overlap=[first_region(at_ms=500),first_region(at_ms=500)]
        normalized,final=normalize_regions(self.track,overlap)
        self.assertEqual(len(normalized),2)
        self.assertAlmostEqual(final,.7)
        self.assertEqual(len(normalize_regions(
            self.track,[first_region()]*12)[0]),12)
        with self.assertRaises(SessionError):
            normalize_regions(self.track,[first_region()]*13)
        with self.assertRaises(SessionError):
            normalize_regions(self.track,"[]")
        bad=[
            first_region(at_ms=7200001),
            first_region(at_ms=True),
            first_region(start_ms=400,end_ms=300),
            first_region(end_ms=1500),
            first_region(fade_in_ms=300),
            first_region(fade_out_ms=-5),
            first_region(start_ms=1.2),
            first_region(extra="arbitrary ffmpeg"),
        ]
        for invalid in bad:
            with self.subTest(invalid=invalid),self.assertRaises(SessionError):
                normalize_regions(self.track,[invalid])
        with self.assertRaises(SessionError):
            mix_plan(self.session,{self.filename:{
                "clip":{"trim_start_ms":10},
                "regions":[first_region()]}})
        with self.assertRaises(SessionError):
            mix_plan(self.session,{self.filename:{
                "delay_ms":50,"regions":[first_region()]}})

    def test_legacy_presets_load_dry_and_multiregions_roundtrip(self):
        edits=[first_region(start_ms=200,end_ms=400,at_ms=0),
               first_region(start_ms=600,end_ms=900,at_ms=750)]
        path=save_preset(
            self.session,{self.filename:{"regions":edits}},
            name="Multi-part singer comp")
        self.assertEqual(path.stat().st_mode&0o777,0o600)
        preset=load_preset(self.session,path)
        self.assertEqual(preset["controls"][self.filename]["regions"],edits)
        self.assertEqual(preset["controls"][self.filename]["clip"],DEFAULTS)
        old=json.loads(path.read_text())
        old["controls"][self.filename].pop("regions")
        legacy=self.folder/"mix-presets"/("preset-"+"c"*32+".json")
        legacy.write_text(json.dumps(old))
        self.assertEqual(load_preset(self.session,legacy)["controls"][
            self.filename]["regions"],[])
        self.assertEqual(self.src.read_bytes(),self.original)

    @unittest.skipUnless(shutil.which("ffmpeg"),"FFmpeg unavailable")
    def test_real_multi_region_render_has_gaps_and_independent_polarity(self):
        edits=[
            first_region(start_ms=100,end_ms=300,at_ms=0,
                         fade_in_ms=20,fade_out_ms=20),
            first_region(start_ms=600,end_ms=900,at_ms=700,
                         fade_in_ms=30,fade_out_ms=30)]
        destination=render_session(
            self.folder,controls={self.filename:{"regions":edits}},
            output_root=self.root/"mixed",timeout=35)
        with wave.open(str(destination),"rb") as result:
            self.assertEqual((result.getframerate(),result.getnchannels(),
                              result.getsampwidth()),(48000,2,3))
            self.assertGreaterEqual(result.getnframes(),48000*.998)
            self.assertLessEqual(result.getnframes(),48000*1.012)
        self.assertGreater(levels(destination,.10),1500)
        self.assertLess(levels(destination,.43),10)
        self.assertGreater(levels(destination,.82),1000)
        self.assertEqual(self.src.read_bytes(),self.original)
        receipt=json.loads(
            (destination.parent/"mix-receipt.json").read_text())
        self.assertEqual(receipt["tracks"][0]["regions"],edits)
        self.assertTrue(receipt["original_tracks_preserved"])


class MultiRegionQtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from PyQt5.QtWidgets import QApplication
        except ImportError:
            raise unittest.SkipTest("PyQt5 not available")
        cls.app=QApplication.instance() or QApplication([])

    def test_native_editor_preserves_old_single_clip_and_adds_second_region(self):
        from studio.session_regions_dialog import TrackRegionsDialog
        from studio.session_mix_dialog import SessionMixDialog
        with tempfile.TemporaryDirectory() as root_name:
            root=Path(root_name)
            original=root/"owner.wav"
            fixture(original)
            directory=export_session(
                [{"path":str(original),"role":"lead_vocal","label":"Owner"}],
                title="Native region UI",output_root=root/"sessions")
            session=inspect_session(directory)
            track=session["tracks"][0]
            clip={"trim_start_ms":100,"trim_end_ms":400}
            editor=TrackRegionsDialog(track,clip=clip,offset_ms=250)
            try:
                self.assertEqual(editor.table.rowCount(),1)
                self.assertEqual(editor.rows()[0]["start_ms"],100)
                self.assertEqual(editor.rows()[0]["at_ms"],250)
                editor.add_region()
                self.assertEqual(editor.table.rowCount(),2)
                self.assertEqual(editor.rows()[1]["at_ms"],550)
                self.assertEqual(len(editor.values()),2)
                editor.table.cellWidget(1,1).setValue(.800)
                self.assertEqual(editor.values()[1]["end_ms"],800)
                editor.move_region(-1)
                self.assertEqual(editor.table.currentRow(),0)
                editor.remove_region()
                self.assertEqual(editor.table.rowCount(),1)
            finally:
                editor.close()
            ui=SessionMixDialog()
            try:
                ui.audit_done(session,"")
                self.assertTrue(ui.region_button.isEnabled())
                to_apply=[first_region(),first_region(
                    start_ms=500,end_ms=750,at_ms=800)]
                class FakeEditor:
                    Accepted=1
                    def __init__(self,*args,**kwargs):pass
                    def exec_(self):return self.Accepted
                    def values(self):return to_apply
                with patch("studio.session_mix_dialog.TrackRegionsDialog",FakeEditor):
                    ui.edit_multi_regions()
                controls=ui.mix_controls()[track["filename"]]
                self.assertEqual(controls["regions"],to_apply)
                self.assertEqual(controls["delay_ms"],0)
                self.assertEqual(controls["clip"],DEFAULTS)
                self.assertIn("2 regions",ui.table.item(0,9).text())
                preset=save_preset(
                    session,ui.mix_controls(),name="Region layout")
                ui.refresh_presets()
                for row in range(ui.preset_list.count()):
                    if ui.preset_list.itemData(row)==str(preset):
                        ui.preset_list.setCurrentIndex(row)
                        break
                ui.region_edits[track["filename"]]=[]
                ui.load_mix_preset()
                self.assertEqual(
                    ui.mix_controls()[track["filename"]]["regions"],to_apply)
            finally:
                ui.close()

if __name__=="__main__":
    unittest.main()
