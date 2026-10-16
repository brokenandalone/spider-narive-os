"""Whitelisted DSP effect validation and real optional FFmpeg WAV test."""
import shutil
import tempfile
import unittest
import wave
from pathlib import Path
from studio.take_effects import TakeEffects,effects_graph,apply_take_effects
from studio.audio_capture_engine import CaptureError

class TakeEffectsTests(unittest.TestCase):
    def test_eq_compressor_room_graph_is_bounded(self):
        s=TakeEffects(bass_db=6,mids_db=-3,treble_db=5,
                      compression=True,room=20)
        graph=effects_graph(s)
        self.assertIn("equalizer=f=105:",graph)
        self.assertIn("equalizer=f=1050:",graph)
        self.assertIn("equalizer=f=6300:",graph)
        self.assertIn("acompressor=threshold=0.25",graph)
        self.assertIn("aecho=in_gain=0.8",graph)
        self.assertTrue(graph.endswith("alimiter=limit=0.95:level=0"))
        self.assertNotIn(";",graph)
        self.assertEqual(effects_graph(TakeEffects()),"alimiter=limit=0.95:level=0")
        for bad in ({"bass_db":13},{"mids_db":True},
                    {"treble_db":-13},{"compression":"on"},
                    {"room":99},{"room":.5}):
            with self.subTest(bad=bad),self.assertRaises(CaptureError):
                effects_graph(TakeEffects(**bad))

    @unittest.skipUnless(shutil.which("ffmpeg"),"FFmpeg not installed in source runner")
    def test_real_24bit_offline_effects_keep_original_wav_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            source=root/"source.wav"
            with wave.open(str(source),"wb") as out:
                out.setnchannels(1)
                out.setsampwidth(2)
                out.setframerate(44100)
                out.writeframes(b"\x10\x00"*4410)
            original=source.read_bytes()
            new=root/"modified.wav"
            result=apply_take_effects(
                source,new,TakeEffects(bass_db=3,compression=True,room=10),
                timeout=60)
            self.assertEqual(result["sample_width_bits"],24)
            self.assertEqual(source.read_bytes(),original)
            self.assertEqual(new.stat().st_mode&0o777,0o600)
            with wave.open(str(new),"rb") as wav:
                self.assertEqual(wav.getsampwidth(),3)
                self.assertEqual(wav.getframerate(),44100)
                self.assertGreaterEqual(wav.getnframes(),4410)
            with self.assertRaises(CaptureError):
                apply_take_effects(source,new,TakeEffects())
            self.assertEqual(source.read_bytes(),original)
            self.assertFalse(list(root.glob("*.part")))

    def test_invalid_input_preflight_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            source=root/"fake.wav"
            source.write_bytes(b"not even a WAV")
            destination=root/"nothing.wav"
            with self.assertRaises((CaptureError,wave.Error)):
                apply_take_effects(source,destination)
            self.assertFalse(destination.exists())

if __name__=="__main__":
    unittest.main()
