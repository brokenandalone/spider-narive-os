import importlib.util
from pathlib import Path
import unittest

S = Path(__file__).resolve().parents[1]/'webbie/agent/voice_turns.py'
spec=importlib.util.spec_from_file_location('voice_turns',S)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class VoiceTurnsTests(unittest.TestCase):
    def test_stop_invalidates_prior_reply_but_allows_new_conversation(self):
        tracker=mod.VoiceTurnTracker()
        first=tracker.start()
        self.assertTrue(tracker.current(first))
        tracker.interrupted()
        self.assertFalse(tracker.current(first))
        second=tracker.start()
        self.assertTrue(tracker.current(second))
        self.assertNotEqual(first,second)

if __name__=='__main__':
    unittest.main()
