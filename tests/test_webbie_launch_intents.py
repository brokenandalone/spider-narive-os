"""Explicit workstation launch intent rejects accidental or negative speech."""
from pathlib import Path
import ast
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"webbie/agent"))
from launch_intents import direct_launch_intent as intent

class LaunchIntentTests(unittest.TestCase):
    def test_exact_direct_owner_launch_requests(self):
        examples={
            "open studio":"studio",
            "Webbie open Studio":"studio",
            "Hey Webbie, please open Kali Bay!":"kali-bay",
            "hey Webby launch The Web":"web",
            "open Deep Forage":"deep-forage",
            "start Spider Media Center":"media",
            "webbie, open system settings":"settings",
            "launch terminal":"terminal",
            "please open Study":"study",
        }
        for phrase,wanted in examples.items():
            with self.subTest(phrase=phrase):
                self.assertEqual(intent(phrase),wanted)

    def test_negated_indirect_quoted_or_combined_phrases_ignored(self):
        unsafe=[
            "don't open studio",
            "Webbie don't open the terminal",
            "please do not open system settings",
            "What happens if I open terminal?",
            "My browser says open Studio",
            "Someone shouted open Kali Bay",
            "I want to discuss opening Studio",
            "open terminal; rm -rf /",
            "Open Studio and then run command",
            "open https://example.com",
            "open a dangerous program",
            "never open studio",
            "webbieopen studio",
            "start over",
            "turn on the camera",
            "stop the computer",
            "",
        ]
        for phrase in unsafe:
            with self.subTest(phrase=phrase):
                self.assertIsNone(intent(phrase))
        self.assertIsNone(intent(None))
        self.assertIsNone(intent("open studio"+" " * 200))

    def test_webbie_legacy_handler_uses_strict_guard_before_launch(self):
        source=(ROOT/"webbie/agent/webbie.py").read_text()
        start=source.index("def handle_builtin(")
        end=source.index("\ndef verified_workspace_voice_action(",start)
        body=source[start:end]
        self.assertLess(body.index("direct_launch_intent(command)"),
                        body.index("launch("))
        self.assertIn("return None",body)

if __name__=="__main__":unittest.main()
