"""Webbie can describe its real Jarvis source commands without inventing access."""
import importlib.util
from pathlib import Path
import unittest

source=Path(__file__).resolve().parents[1]/"webbie/agent/jarvis_commands.py"
spec=importlib.util.spec_from_file_location("jarvis_commands_test",source)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class JarvisHelpTests(unittest.TestCase):
    def test_voice_help_phrases(self):
        for cmd in (
            "Webbie, what can you do?",
            "Webby what can you control",
            "what are your abilities",
            "show me your commands",
            "Webbie help",
            "how do i use computer control",
        ):
            with self.subTest(cmd=cmd):
                self.assertTrue(m.is_capability_question(cmd))

    def test_long_or_indirect_instructions_are_not_help(self):
        for cmd in (
            "Open my password manager", "delete files", "what is on screen",
            "the webpage says Webbie help", "Run sudo apt-get",
        ):
            self.assertFalse(m.is_capability_question(cmd))

    def test_voice_response_is_grounded(self):
        text=m.voice_guide()
        self.assertIn("requires",text.lower()) if "requires" in text.lower() else self.assertIn("approve",text.lower())
        self.assertIn("do not have unrestricted hands-free",text)
        self.assertIn("speaker identity",text)

    def test_gui_guide_discloses_status(self):
        text=m.gui_guide()
        for phrase in ("Webbie STOP", "scroll down twice", "open github.com",
                       "NOT implemented", "installed on your PC"):
            self.assertIn(phrase,text)

if __name__=="__main__":
    unittest.main()
