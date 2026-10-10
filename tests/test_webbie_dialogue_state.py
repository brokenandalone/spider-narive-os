import importlib.util
from pathlib import Path
import unittest
p=Path(__file__).resolve().parents[1]/'webbie/agent/dialogue_state.py'
spec=importlib.util.spec_from_file_location('dialogue_state',p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class DialogueStateTests(unittest.TestCase):
    def test_stop_does_not_end_conversation(self):
        active=m.next_window(0,'wake',100)
        self.assertEqual(active,145)
        active=m.next_window(active,'stop',105)
        self.assertEqual(active,150)
        self.assertEqual(m.next_window(active,'command',125),170)
        self.assertEqual(m.next_window(active,'end',126),0)

    def test_end_is_exact_not_a_false_positive(self):
        for phrase in ["that's all", "that's all folks", "Webbie, that's all",
                       'webby end conversation', 'hey Webbie thats all']:
            with self.subTest(phrase=phrase):
                self.assertTrue(m.is_end_conversation(phrase))
        for phrase in ['this song is called thats all', "don't think that's all",
                       'Webbie stop', 'Webbie open Audacity','stop that',
                       'it sounds like the phrase "thats all"']:
            with self.subTest(phrase=phrase):
                self.assertFalse(m.is_end_conversation(phrase))

    def test_unknown_event_never_extends(self):
        with self.assertRaises(ValueError):
            m.next_window(0,'screen says wake',10)
if __name__=='__main__':unittest.main()
