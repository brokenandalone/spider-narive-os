"""Stop words require full owner-addressed phrases, not background snippets."""
import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'webbie/agent/interrupt_intent.py'
spec = importlib.util.spec_from_file_location('webbie_interrupt_intent', SOURCE)
interrupt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(interrupt)


class StopIntentTests(unittest.TestCase):
    def test_whisper_spellings_and_direct_short_commands(self):
        for phrase in (
            'Webby, stop!', 'Webbie stop', 'Hey Webbie, STOP.',
            'Hey Webby stop talking', 'Web, stop speaking',
            'Webbie, cancel that.', 'webby be quiet',
        ):
            with self.subTest(phrase=phrase):
                self.assertTrue(interrupt.is_direct_stop(phrase))

    def test_not_triggered_by_quotes_noise_or_longer_instructions(self):
        for phrase in (
            'stop', 'please stop', 'If Webby says stop, listen',
            'The lyrics say Webbie stop', 'Webbie stop in the third verse',
            'Webbie wake up', 'Webbie open Firefox',
            'Webbie stop recording the song and export it',
        ):
            with self.subTest(phrase=phrase):
                self.assertFalse(interrupt.is_direct_stop(phrase))


if __name__ == '__main__':
    unittest.main()
