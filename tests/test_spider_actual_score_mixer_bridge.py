"""Actual score-to-recording backend validation, beyond an injected mixer fake."""
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch
import tempfile
import unittest
import wave

from studio.score_performer import Performance,Part,Note
from studio.studio_score_mix import render_score_mix,MixChannel
from studio.backing_cue import render_score_backing,validate_recordable_cue

def fake_sf(path):
    path.write_bytes(b"RIFF"+bytes(4)+b"sfbk"+bytes(72))
    return path

def song():
    return Performance("Spider Safeguarded Band",120,
        [Part("Guitar",27,0),Part("Bass",33,1)],
        [Note(0,60,Fraction(0),Fraction(1)),
         Note(1,40,Fraction(0),Fraction(1))],
         Fraction(2)).validated()

class RealScoreMixerTests(unittest.TestCase):
    def test_real_mixer_renders_multiple_soundfont_parts_as_stereo_pcm(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            bank=fake_sf(root/"bank.sf2")
            destinations=[]
            def fake_instrument(performance,selected,output,rate=48000):
                # This replaces only the external FluidSynth process, not
                # Spider's actual multi-channel mixing and delivery code.
                self.assertEqual(Path(selected),bank)
                destinations.append(len(performance.parts))
                self.assertEqual(len(performance.parts),1)
                with wave.open(str(output),"wb") as w:
                    w.setnchannels(2)
                    w.setsampwidth(2)
                    w.setframerate(rate)
                    w.writeframes(b"\x20\x00\x20\x00"*256)
                return output
            chosen=root/"new-render.wav"
            output=render_score_mix(
                song(),bank,chosen,
                channels=[MixChannel(gain=80,pan=-25),
                          MixChannel(gain=100,pan=20)],
                rate=48000,part_renderer=fake_instrument)
            self.assertEqual(output,chosen)
            self.assertEqual(destinations,[1,1])
            with wave.open(str(output),"rb") as w:
                self.assertEqual((w.getframerate(),w.getnchannels(),
                                  w.getsampwidth(),w.getnframes()),
                                 (48000,2,2,256))
                self.assertTrue(any(w.readframes(5)))
            original=chosen.read_bytes()
            with self.assertRaises(FileExistsError):
                render_score_mix(song(),bank,chosen,part_renderer=fake_instrument)
            self.assertEqual(chosen.read_bytes(),original)
            self.assertFalse(list(root.glob("*.wav.tmp")))

    def test_virtual_band_handoff_uses_real_mixer_without_opening_audio(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            bank=fake_sf(root/"bank.sf2")
            count=[]
            def fake_sf_process(performance,soundbank,output,rate=48000):
                count.append(len(performance.parts))
                with wave.open(str(output),"wb") as w:
                    w.setnchannels(2)
                    w.setsampwidth(2)
                    w.setframerate(rate)
                    w.writeframes(b"\x40\x00\x40\x00"*512)
                return output
            with patch("studio.studio_score_mix.render_soundfont",fake_sf_process):
                path,info=render_score_backing(song(),bank,output_root=root)
            self.assertEqual(count,[1,1])
            self.assertEqual(info["frames"],512)
            self.assertEqual(validate_recordable_cue(path)["rate"],48000)
            self.assertEqual(path.stat().st_mode&0o777,0o600)
            self.assertTrue(bank.exists())
            self.assertFalse(list(root.glob("*.tmp")))

    def test_output_symlink_never_publishes_over_an_owner_wav(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            bank=fake_sf(root/"bank.sf2")
            original=root/"keep.wav"
            original.write_bytes(b"OWNER ORIGINAL")
            link=root/"existing-render.wav"
            link.symlink_to(original)
            with self.assertRaises(FileExistsError):
                render_score_mix(song(),bank,link)
            self.assertEqual(original.read_bytes(),b"OWNER ORIGINAL")

if __name__=="__main__":
    unittest.main()
