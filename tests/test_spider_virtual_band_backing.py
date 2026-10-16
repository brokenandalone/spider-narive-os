"""Source-to-recorder virtual band backing bridge, no microphones or devices."""
from fractions import Fraction
from pathlib import Path
import tempfile
import unittest
import wave

from studio.backing_cue import (
    render_score_backing, render_song_backing, validate_recordable_cue)
from studio.audio_capture_engine import CaptureError
from studio.score_performer import Performance,Note,Part
from studio.studio_score_mix import MixChannel
from studio.song_arranger_engine import Song
from studio.instruments_engine import Pattern

def soundbank(path):
    # Header must be verified even with a test-injected renderer.
    path.write_bytes(b"RIFF"+bytes(4)+b"sfbk"+bytes(72))
    return path

def score():
    return Performance(
        "Spider / Guitar and Bass",120,
        [Part("Guitar",27,0),Part("Bass",33,1)],
        [Note(0,64,Fraction(0),Fraction(1)),
         Note(1,40,Fraction(1),Fraction(1))],Fraction(4),
    ).validated()

def fake_stereo(path,rate,frames=512):
    with wave.open(str(path),"wb") as file:
        file.setnchannels(2)
        file.setsampwidth(2)
        file.setframerate(rate)
        file.writeframes((b"\x10\x00\xf0\xff")*frames)

class BackingCueTests(unittest.TestCase):
    def test_score_render_uses_selected_banks_and_mix_and_honors_original(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            master=soundbank(root/"grand.sf2")
            bass=soundbank(root/"bass.sf3")
            src=score()
            original=list(src.notes)
            seen=[]
            def test_renderer(performance,bank,destination,*,part_banks,channels,rate,bit_depth):
                seen.append({
                    "notes":list(performance.notes),"rate":rate,"depth":bit_depth,
                    "banks":{i:Path(p).name for i,p in part_banks.items()},
                    "pans":[c.pan for c in channels],
                })
                fake_stereo(destination,rate)
            for i in range(2):
                dest,info=render_score_backing(
                    src,master,part_banks={1:bass},
                    channels=[MixChannel(pan=-30),MixChannel(pan=65)],
                    rate=48000,output_root=root,renderer=test_renderer)
                self.assertEqual(info["rate"],48000)
                self.assertEqual(info["frames"],512)
                self.assertEqual(dest.stat().st_mode & 0o777,0o600)
                self.assertTrue(dest.name.startswith("Spider-Band-"))
                with wave.open(str(dest),"rb") as output:
                    self.assertEqual((output.getnchannels(),output.getsampwidth(),
                                      output.getframerate()),(2,2,48000))
                if i==0:
                    first=dest
                else:
                    self.assertNotEqual(dest,first)
                    self.assertEqual(first.read_bytes(),dest.read_bytes())
            self.assertEqual(seen[0]["banks"],{1:"bass.sf3"})
            self.assertEqual(seen[0]["pans"],[-30,65])
            self.assertEqual(seen[0]["depth"],16)
            self.assertEqual(src.notes,original)
            self.assertEqual(list(root.glob(".spider-band-render-*")),[])
            self.assertTrue(master.exists())
            self.assertTrue(bass.exists())

    def test_song_arranger_creates_a_real_private_16bit_cue(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            tune=Song(title="One Bar Band",bpm=240)
            pattern=Pattern()
            pattern.set("bass",0,40)
            pattern.set("guitar",2,52)
            tune.capture("Intro",pattern)
            cue,info=render_song_backing(tune,rate=44100,output_root=root)
            self.assertEqual(info["rate"],44100)
            self.assertAlmostEqual(info["seconds"],1.0,places=2)
            with wave.open(str(cue),"rb") as wav:
                self.assertEqual(wav.getnchannels(),2)
                self.assertEqual(wav.getsampwidth(),2)
                self.assertEqual(wav.getframerate(),44100)
                self.assertEqual(wav.getnframes(),44100)
                self.assertTrue(any(wav.readframes(2000)))
            self.assertEqual(cue.stat().st_mode & 0o777,0o600)
            self.assertEqual(len(tune.bars),1)

    def test_invalid_or_truncated_cue_never_published(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            master=soundbank(root/"mybank.sf2")
            def incomplete(_score,_bank,out,**options):
                Path(out).write_bytes(b"not a wav")
            with self.assertRaises(CaptureError):
                render_score_backing(score(),master,output_root=root,
                                     renderer=incomplete)
            self.assertFalse(list(root.glob("Spider-Band-*.wav")))
            with self.assertRaises(CaptureError):
                validate_recordable_cue(master)
            too_short=root/"broken.wav"
            fake_stereo(too_short,48000)
            with self.assertRaises(CaptureError):
                validate_recordable_cue(too_short,expected_rate=44100)
            with self.assertRaises(CaptureError):
                render_score_backing(score(),master,rate=96000,output_root=root,
                                     renderer=incomplete)
            self.assertEqual(list(root.glob(".spider-band-render-*")),[])

    def test_invalid_song_and_untrusted_output_destination_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            empty=Song(bpm=120)
            with self.assertRaises(CaptureError):
                render_song_backing(empty,output_root=root)
            external=root/"outside"
            external.mkdir()
            alias=root/"unsafe-alias"
            alias.symlink_to(external,target_is_directory=True)
            song=Song(title="Safe song",bpm=240)
            song.capture("Bass",Pattern.preset("Rock"))
            with self.assertRaises(CaptureError):
                render_song_backing(song,output_root=alias)

    def test_bad_part_bank_is_refused_without_renderer_executing(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            bank=soundbank(root/"valid.sf2")
            calls=[]
            def bad_renderer(*args,**kwargs): calls.append(True)
            with self.assertRaises(ValueError):
                render_score_backing(score(),bank,part_banks={1:root/"missing.sf2"},
                                     output_root=root,renderer=bad_renderer)
            self.assertEqual(calls,[])

if __name__=="__main__":
    unittest.main()
