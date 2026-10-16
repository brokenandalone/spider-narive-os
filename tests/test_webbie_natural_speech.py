"""Speech is natural while current STOP-aware Natasha player stays authoritative."""
import pathlib
import sys
import unittest
from unittest import mock

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"webbie"/"voice"))
from interruptible_speech import InterruptibleSpeech, clean_spoken_text

class NaturalSpeechTests(unittest.TestCase):
    def test_formats_story_and_research_without_markup(self):
        original="# Chapter One\n\n**Broken City** [Map](https://example.com)\n- Rain falls black.\n"
        text=clean_spoken_text(original)
        self.assertNotIn("**",text)
        self.assertNotIn("https://",text)
        self.assertNotIn("#",text)
        self.assertIn("Broken City Map",text)
        self.assertIn("Rain falls black.",text)
    def test_empty_markdown_does_not_spawn_voice(self):
        voice=InterruptibleSpeech(popen=mock.Mock(),which=lambda _:None)
        self.assertFalse(voice.speak("   **   "))
        voice.popen.assert_not_called()
    def test_stop_aware_voice_generation_is_unchanged(self):
        voice=InterruptibleSpeech(popen=mock.Mock(),which=lambda _:None)
        voice.stop()
        self.assertTrue(voice.cancelled.is_set())
        self.assertFalse(voice.speak("Would speak but no TTS provider"))
    def test_literal_owner_words_survive(self):
        self.assertEqual(clean_spoken_text("I'm here, Writer. Let's open Author."),
                         "I'm here, Writer. Let's open Author.")

if __name__=="__main__":
    unittest.main()
