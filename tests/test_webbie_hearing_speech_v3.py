import sys
import tempfile
import wave
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"webbie"/"voice"))
sys.path.insert(0,str(ROOT/"webbie"/"brain"))
sys.path.insert(0,str(ROOT/"webbie"/"agent"))
from audio_gate import wav_has_activity,normalize_transcript,TranscriptDeduper
from tts import speakable,SpeechController
import brain
import webbie

class HearingSpeechTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/"chunk.wav"
    def make_wav(self,samples):
        from array import array
        with wave.open(str(self.path),"wb") as f:
            f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000)
            f.writeframes(array("h",samples).tobytes())
        return self.path
    def test_silence(self):
        self.assertFalse(wav_has_activity(self.make_wav([0]*64000)))
    def test_low_noise(self):
        self.assertFalse(wav_has_activity(self.make_wav([15,-15]*32000)))
    def test_speech_like_burst(self):
        import math
        samples=[5]*16000+[int(6500*math.sin(i*.11)) for i in range(16000)]+[5]*32000
        self.assertTrue(wav_has_activity(self.make_wav(samples)))
    def test_clipping_rejected(self):
        self.assertFalse(wav_has_activity(self.make_wav([32767]*64000)))
    def test_corrupt_audio(self):
        self.path.write_text("not wave")
        self.assertFalse(wav_has_activity(self.path))
    def test_hallucination_filter(self):
        self.assertEqual(normalize_transcript("[silence]"),"")
        self.assertEqual(normalize_transcript("Thanks for watching."),"")
        self.assertEqual(normalize_transcript("Hey Webbie, open Firefox."),"Hey Webbie, open Firefox.")
    def test_deduplication(self):
        clock=[10.]
        d=TranscriptDeduper(clock=lambda:clock[0])
        self.assertTrue(d.accept("Hey Webbie!"))
        self.assertFalse(d.accept("hey webbie"))
        clock[0]=13
        self.assertTrue(d.accept("hey webbie"))
    def test_wake_word_boundaries(self):
        self.assertEqual(webbie.remove_wake_word("website options"),(False,"website options"))
        self.assertEqual(webbie.remove_wake_word("Someone said hey Webbie"),(False,"someone said hey webbie"))
        self.assertEqual(webbie.remove_wake_word("Hey Webbie, stop"),(True,"stop"))
    def test_stop_phrases_are_not_sent_to_ai(self):
        old=webbie.speech_controller
        class Fake:
            stopped=False
            def stop(self): self.stopped=True
        fake=Fake()
        webbie.speech_controller=fake
        try:
            self.assertEqual(webbie.handle_command("stop",voice=True),"")
            self.assertTrue(fake.stopped)
        finally:
            webbie.speech_controller=old
    def test_tts_cleaning(self):
        s=speakable("## Status\n**Cory**, see https://example.com/details")
        self.assertIn("Cory",s)
        self.assertNotIn("https:",s)
    def test_tts_stop_without_speech(self):
        speech=SpeechController(marker=Path(self.temp.name)/"speaking")
        self.assertTrue(speech.stop())
    def test_context_is_per_speaker(self):
        brain._HISTORY.clear()
        brain.remember_exchange("voice:Cory","hello","hey")
        self.assertEqual(len(brain._get_history("voice:Cory")),2)
        self.assertEqual(brain._get_history("voice:Shayna"),[])
    def test_context_bounded(self):
        brain._HISTORY.clear()
        for i in range(12):
            brain.remember_exchange("voice:Cory",str(i),str(i))
        self.assertEqual(len(brain._get_history("voice:Cory")),8)

if __name__=="__main__":
    unittest.main()
