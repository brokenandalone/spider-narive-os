"""Regression check: owner-installed real WAV band workbench in current Studio."""
import ast
from pathlib import Path
import sys
import tempfile
import unittest
import wave

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"studio"))
from band_mix import validate_tracks
from song_mix import MixError

class StudioInstalledToolsTests(unittest.TestCase):
    def test_band_workbench_is_reconciled_into_real_studio_panel(self):
        source=(ROOT/"studio"/"ai_panel.py").read_text(encoding="utf-8")
        tree=ast.parse(source)
        cls=next(n for n in tree.body
                 if isinstance(n,ast.ClassDef) and n.name=="StudioAIPanel")
        methods={n.name for n in cls.body if isinstance(n,ast.FunctionDef)}
        for method in ("start_band_mix","cancel_band_mix",
                       "open_multitrack_session","open_saved_session_mix",
                       "open_mastering_desk","band_mix_finished"):
            self.assertIn(method,methods)
        self.assertIn("mix_band_tracks",source)
        self.assertIn("MultitrackDialog",source)
        self.assertIn("SessionMixDialog",source)
        self.assertIn("MasteringDialog",source)
        self.assertIn("Independent band stems mixed",source)

    def test_mixer_rejects_duplicate_stems(self):
        with tempfile.TemporaryDirectory() as directory:
            wav=Path(directory)/"guitar.wav"
            with wave.open(str(wav),"wb") as out:
                out.setnchannels(1)
                out.setsampwidth(2)
                out.setframerate(16000)
                out.writeframes(b"\x00\x00"*16000)
            with self.assertRaisesRegex(MixError,"different source WAV"):
                validate_tracks({"backing":str(wav),"lead_guitar":str(wav)})

    def test_mixer_keeps_two_real_independent_stems(self):
        with tempfile.TemporaryDirectory() as directory:
            sources=[]
            for name in ("lead","rhythm"):
                wav=Path(directory)/(name+".wav")
                with wave.open(str(wav),"wb") as out:
                    out.setnchannels(1)
                    out.setsampwidth(2)
                    out.setframerate(16000)
                    out.writeframes(b"\x00\x00"*16000)
                sources.append(str(wav))
            assigned,gains=validate_tracks({
                "lead_guitar":sources[0],"rhythm_guitar":sources[1]}, {
                "lead_guitar":.9,"rhythm_guitar":1.1,
            })
            self.assertEqual(len(assigned),2)
            self.assertAlmostEqual(gains["lead_guitar"],.9)
            self.assertTrue(all(Path(x).exists() for x in sources))

if __name__=="__main__":
    unittest.main()
