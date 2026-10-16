"""Wave 11: source-frame clip editing, visible waveform, presets and real render."""
import json
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
import shutil
import tempfile
import unittest
import wave
from pathlib import Path
from array import array
import sys

from studio.multitrack import SessionError, export_session
from studio.session_project import inspect_session
from studio.session_clip_edit import (
    DEFAULTS,normalize_clip_edit,clip_ffmpeg_filters)
from studio.session_mix import mix_plan,ffmpeg_command,render_session
from studio.session_presets import save_preset,load_preset
from studio.session_waveform import waveform_peaks


def create_wav(path,rate=48000,width=2):
    # Three source regions: first ~250ms is quiet, middle is loud,
    # final quarter is inverted; produces obvious original source boundaries.
    one_second=rate
    with wave.open(str(path),"wb") as wav:
        wav.setnchannels(1);wav.setsampwidth(width);wav.setframerate(rate)
        for start in range(0,one_second,4096):
            end=min(start+4096,one_second)
            payload=bytearray()
            for i in range(start,end):
                amplitude=(100 if i<rate//4 else
                           10000 if i<3*rate//4 else -4000)
                payload.extend(amplitude.to_bytes(width,"little",signed=True))
            wav.writeframesraw(payload)
        wav.writeframes(b"")


def read_samples(filename):
    with wave.open(str(filename),"rb") as wav:
        info=(wav.getframerate(),wav.getnchannels(),wav.getsampwidth(),
              wav.getnframes())
        raw=wav.readframes(wav.getnframes())
    width=info[2]
    values=[int.from_bytes(raw[i:i+width],"little",signed=True)
            for i in range(0,len(raw),width)]
    return info,values


class ClipDecisionTests(unittest.TestCase):
    def setUp(self):
        self.root=tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        folder=Path(self.root.name)
        self.original=folder/"owner-recording.wav"
        create_wav(self.original)
        self.original_bytes=self.original.read_bytes()
        self.folder=export_session(
            [{"path":str(self.original),"role":"lead_vocal","label":"Lead Vocal"}],
            title="Clip alignment",tempo_bpm=120,
            output_root=folder/"sessions")
        self.session=inspect_session(self.folder)
        self.track=self.session["tracks"][0]
        self.filename=self.track["filename"]

    def test_integer_pcm_boundaries_and_time_after_trim(self):
        options,region=normalize_clip_edit(
            self.track,{"trim_start_ms":250,"trim_end_ms":750,
                        "fade_in_ms":100,"fade_out_ms":100},
            delay_ms=200)
        self.assertEqual((region.start_frame,region.end_frame),
                         (12000,36000))
        self.assertEqual(region.duration_seconds,.5)
        self.assertIn("atrim=start_sample=12000:end_sample=36000",
                      clip_ffmpeg_filters(region))
        self.assertIn("afade=t=in:st=0:d=0.100",clip_ffmpeg_filters(region))
        self.assertIn("afade=t=out:st=0.400000:d=0.100",
                      clip_ffmpeg_filters(region))
        plan=mix_plan(self.session,{self.filename:{
            "delay_ms":200,"clip":options}})
        self.assertEqual(plan["active"][0]["clip_region"],region)
        cmd=ffmpeg_command("/usr/bin/ffmpeg",plan,
                           Path(self.root.name)/"song.wav")
        filters=cmd[cmd.index("-filter_complex")+1]
        self.assertIn("asetpts=PTS-STARTPTS",filters)
        self.assertIn("adelay=200:all=1",filters)
        self.assertEqual(filters.count("alimiter=limit=0.95"),1)

    def test_bad_edits_bounded_before_source_export(self):
        for edit in (
            {"trim_start_ms":751,"trim_end_ms":750},
            {"trim_start_ms":1000},
            {"trim_end_ms":1001},
            {"trim_end_ms":1,"fade_in_ms":10},
            {"fade_in_ms":900,"fade_out_ms":900},
            {"fade_in_ms":30001},
            {"fade_out_ms":-1},
            {"trim_start_ms":.3},
            {"trim_start_ms":True},
            {"trim_end_ms":"atrim=0"},
            {"path":"overwrite-all"},
            [],
        ):
            with self.subTest(edit=edit),self.assertRaises(SessionError):
                normalize_clip_edit(self.track,edit)
        with self.assertRaises(SessionError):
            mix_plan(self.session,{self.filename:{"clip":{"fade_out_ms":False}}})
        with self.assertRaises(SessionError):
            mix_plan(self.session,{self.filename:{"clip":{"unknown":1}}})
        options,whole=normalize_clip_edit(self.track)
        self.assertEqual(options,DEFAULTS)
        self.assertEqual(whole.start_frame,0)
        self.assertEqual(whole.end_frame,self.track["frames"])

    def test_existing_mix_presets_and_new_clip_presets(self):
        requested={
            "trim_start_ms":100,"trim_end_ms":800,
            "fade_in_ms":50,"fade_out_ms":60}
        preset=save_preset(
            self.session,{self.filename:{"clip":requested,"delay_ms":125}},
            name="Late vocals")
        self.assertEqual(preset.stat().st_mode&0o777,0o600)
        restored=load_preset(self.session,preset)
        self.assertEqual(restored["controls"][self.filename]["clip"],requested)
        self.assertEqual(restored["controls"][self.filename]["delay_ms"],125)
        original_preset=json.loads(preset.read_text())
        for control in original_preset["controls"].values():
            del control["clip"]  # simulate older Wave 10 mix preset
        old=self.folder/"mix-presets"/("preset-"+"b"*32+".json")
        old.write_text(json.dumps(original_preset))
        with_old=load_preset(self.session,old)
        self.assertEqual(with_old["controls"][self.filename]["clip"],DEFAULTS)

    def test_bounded_waveform_reads_real_16_and_24_bit_pcm(self):
        for width in (2,3):
            path=Path(self.root.name)/f"wave-{width}.wav"
            create_wav(path,rate=44100,width=width)
            peaks=waveform_peaks(path,columns=128)
            self.assertEqual(len(peaks),128)
            self.assertTrue(all(0<=n<=1 for n in peaks))
            self.assertGreater(max(peaks),0)
            with self.assertRaises(SessionError):
                waveform_peaks(path,columns=100000)
        link=Path(self.root.name)/"linked.wav"
        link.symlink_to(self.original)
        with self.assertRaises(SessionError):
            waveform_peaks(link)

    @unittest.skipUnless(shutil.which("ffmpeg"),"FFmpeg unavailable")
    def test_actual_24bit_stereo_audio_is_trimmed_faded_and_delayed(self):
        result=render_session(
            self.folder,controls={self.filename:{
                "clip":{"trim_start_ms":250,"trim_end_ms":750,
                        "fade_in_ms":100,"fade_out_ms":100},
                "delay_ms":200}},
            output_root=Path(self.root.name)/"mixes",timeout=45)
        (rate,channels,width,frames),samples=read_samples(result)
        self.assertEqual((rate,channels,width),(48000,2,3))
        self.assertGreaterEqual(frames,round(rate*.695))
        self.assertLessEqual(frames,round(rate*.710))
        def energy(t,amount=.012):
            a=round(t*rate)*2
            b=min(len(samples),a+round(amount*rate)*2)
            subset=samples[a:b]
            return sum(abs(x) for x in subset)/max(1,len(subset))
        self.assertLess(energy(.10),10)
        self.assertLess(energy(.205),energy(.40))
        self.assertGreater(energy(.40),2000)
        self.assertLess(energy(.685),energy(.40)/2)
        self.assertEqual(self.original.read_bytes(),self.original_bytes)
        receipt=json.loads((result.parent/"mix-receipt.json").read_text())
        self.assertEqual(receipt["tracks"][0]["clip"]["trim_start_ms"],250)
        self.assertEqual(receipt["tracks"][0]["clip"]["fade_out_ms"],100)


class ClipEditorGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from PyQt5.QtWidgets import QApplication
        except ImportError:
            raise unittest.SkipTest("PyQt5 unavailable")
        cls.app=QApplication.instance() or QApplication([])

    def test_native_waveform_and_direct_mix_editor_controls(self):
        from studio.session_clip_dialog import TrackClipDialog
        from studio.session_mix_dialog import SessionMixDialog
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            src=root/"owner.wav"
            create_wav(src)
            session_path=export_session(
                [{"path":str(src),"role":"lead_vocal","label":"Singer"}],
                title="Visual track",output_root=root/"sessions")
            session=inspect_session(session_path)
            source=session["tracks"][0]
            editor=TrackClipDialog(source)
            try:
                self.assertEqual(len(editor.peaks),260)
                editor.start.setValue(.250)
                editor.end.setValue(.750)
                editor.fade_in.setValue(100)
                editor.fade_out.setValue(100)
                editor.position.setValue(.200)
                edit,offset,region=editor.values()
                self.assertEqual(region.start_frame,12000)
                self.assertEqual(region.duration_ms,500)
                self.assertEqual(offset,200)
                self.assertEqual(edit["trim_end_ms"],750)
            finally:
                editor.close()
            ui=SessionMixDialog()
            try:
                ui.audit_done(session,"")
                self.assertEqual(ui.table.columnCount(),10)
                self.assertTrue(ui.clip_button.isEnabled())
                class Accepted:
                    Accepted=1
                    def __init__(self,*args):pass
                    def exec_(self):return self.Accepted
                    def values(self):
                        return edit,offset,region
                with patch("studio.session_mix_dialog.TrackClipDialog",Accepted):
                    ui.edit_recorded_clip()
                ctl=ui.mix_controls()[source["filename"]]
                self.assertEqual(ctl["clip"]["trim_start_ms"],250)
                self.assertEqual(ctl["delay_ms"],200)
                self.assertIn("Source",ui.table.item(0,9).text())
                ui.save_preset_button.setEnabled(True)
                saved=save_preset(session,ui.mix_controls(),name="Clip edit")
                ui.refresh_presets()
                row=next(i for i in range(ui.preset_list.count())
                         if ui.preset_list.itemData(i)==str(saved))
                ui.preset_list.setCurrentIndex(row)
                ui.clip_edits[source["filename"]]=dict(DEFAULTS)
                ui.load_mix_preset()
                self.assertEqual(
                    ui.mix_controls()[source["filename"]]["clip"]["trim_start_ms"],
                    250)
            finally:
                ui.close()

if __name__=="__main__":
    unittest.main()
