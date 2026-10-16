"""Prove stem alignment, isolated banks, silence, and no-overwrite behavior."""
from array import array
from fractions import Fraction
from pathlib import Path
import json
import sys
import tempfile
import unittest
import wave

from studio.score_performer import Performance,Note,Part
from studio.score_stem_export import render_score_stems

def fixture_bank(path):
    path.write_bytes(b"RIFF"+b"\x38\x00\x00\x00"+b"sfbk"+bytes(52))
    return path

def tiny():
    return Performance("Broken Band",120,
                       [Part("Guitar",27,0),Part("Bass",33,1),Part("Drums",0,9)],
                       [Note(0,64,Fraction(0),Fraction(1),98),
                        Note(1,40,Fraction(1),Fraction(1),92)],
                       Fraction(4)).validated()

class StemExportTests(unittest.TestCase):
    def test_24bit_dry_tracks_are_aligned_and_manifest_is_sanitized(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            guitar=fixture_bank(root/"guitar.sf2")
            bass=fixture_bank(root/"bass.sf3")
            called=[]
            def performer(score,bank,output,rate):
                self.assertEqual(len(score.parts),1)
                p=score.parts[0]
                called.append((p.name,Path(bank).name))
                frames=128 if p.name=="Guitar" else 256
                sample=array("h",[5000,-3000]*frames)
                if sys.byteorder!="little":
                    sample.byteswap()
                with wave.open(str(output),"wb") as writer:
                    writer.setnchannels(2)
                    writer.setsampwidth(2)
                    writer.setframerate(rate)
                    writer.writeframes(sample.tobytes())
            dest=root/"stems"
            result=render_score_stems(tiny(),guitar,dest,{1:bass},
                                      bit_depth=24,part_renderer=performer)
            self.assertEqual(result,dest)
            self.assertEqual(called,[("Guitar","guitar.sf2"),("Bass","bass.sf3")])
            manifest=json.loads((dest/"stems.json").read_text())
            self.assertEqual(manifest["frames"],256)
            self.assertEqual(manifest["bit_depth"],24)
            self.assertEqual(len(manifest["parts"]),3)
            self.assertEqual([p["note_count"] for p in manifest["parts"]],[1,1,0])
            self.assertNotIn(str(root),str(manifest))
            for i,part in enumerate(manifest["parts"]):
                with wave.open(str(dest/part["filename"]),"rb") as reader:
                    self.assertEqual((reader.getnchannels(),reader.getsampwidth(),
                                      reader.getframerate(),reader.getnframes()),
                                     (2,3,48000,256))
                    data=reader.readframes(256)
                    self.assertEqual(len(data),1536)
                    self.assertTrue(any(data) if i<2 else not any(data))
            self.assertTrue(guitar.exists())
            self.assertTrue(bass.exists())
            with self.assertRaises(FileExistsError):
                render_score_stems(tiny(),guitar,dest,part_renderer=performer)

    def test_failure_leaves_no_half_export_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            bank=fixture_bank(root/"kit.sf2")
            def failed(score,bank,output,rate):
                if score.parts[0].name=="Bass":
                    raise RuntimeError("Failed sample renderer")
                with wave.open(str(output),"wb") as writer:
                    writer.setnchannels(2);writer.setsampwidth(2)
                    writer.setframerate(rate);writer.writeframes(bytes(400))
            target=root/"uncommitted"
            with self.assertRaises(RuntimeError):
                render_score_stems(tiny(),bank,target,part_renderer=failed)
            self.assertFalse(target.exists())
            self.assertTrue(bank.is_file())

    def test_synchronized_16bit_original_pcm(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            bank=fixture_bank(root/"simple.sf2")
            def render(score,bank,out,rate):
                with wave.open(str(out),"wb") as audio:
                    audio.setnchannels(2);audio.setsampwidth(2);audio.setframerate(rate)
                    audio.writeframes(b"\x01\x00\xff\xff"*32)
            dest=root/"session"
            render_score_stems(tiny(),bank,dest,rate=44100,bit_depth=16,part_renderer=render)
            with wave.open(str(dest/"01-Guitar.wav"),"rb") as reader:
                self.assertEqual(reader.getsampwidth(),2)
                self.assertEqual(reader.getframerate(),44100)
                self.assertEqual(reader.readframes(1),b"\x01\x00\xff\xff")

if __name__=="__main__":
    unittest.main()
