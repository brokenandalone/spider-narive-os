"""Content-free Jarvis session activity history tests."""
from datetime import datetime
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"webbie/actions"))
from action_journal import ActionJournal, MAX_EVENTS

class JournalTests(unittest.TestCase):
    def test_redacted_names_only(self):
        journal=ActionJournal(clock=lambda:datetime(2026,10,11,17,0))
        journal.record("website_requested")
        journal.record("mission_step")
        output=journal.display()
        self.assertIn("17:00:00",output)
        self.assertIn("Approved website opening requested",output)
        self.assertNotIn("http",output.lower())
        self.assertEqual(len(journal.latest()),2)

    def test_untrusted_strings_cannot_be_logged(self):
        journal=ActionJournal()
        for attack in ("secret=abcd", "website_requested: https://example.com",
                       "window bound username", "user message content", ""):
            with self.subTest(attack=attack),self.assertRaises(ValueError):
                journal.record(attack)
        self.assertEqual(journal.latest(),[])

    def test_bounded_history(self):
        journal=ActionJournal()
        for _ in range(MAX_EVENTS+14):
            journal.record("mission_step")
        self.assertEqual(len(journal.latest()),MAX_EVENTS)

    def test_clear_is_in_memory_only(self):
        journal=ActionJournal()
        journal.record("stopped")
        journal.clear()
        self.assertIn("No desktop activity",journal.display())

if __name__=="__main__":
    unittest.main()
