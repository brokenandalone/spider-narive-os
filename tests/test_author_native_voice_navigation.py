"""The real Author voice/socket navigation works without selecting or editing books."""
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"author"))
from commands import parse_author_command

VIEWS={
    "open project map":"open_project_map",
    "show chapter outline":"open_project_map",
    "show story atlas":"open_story_atlas",
    "open character network":"open_story_atlas",
    "open master canon":"open_master_canon",
    "show canon dashboard":"open_master_canon",
    "show canon intelligence":"open_canon_intelligence",
    "show canon review dashboard":"open_canon_intelligence",
}
class AuthorNativeVoiceNavigationTests(unittest.TestCase):
    def test_exact_owner_requests_use_existing_author_tabs(self):
        for utterance, action in VIEWS.items():
            with self.subTest(utterance=utterance):
                self.assertEqual(parse_author_command("Hey Webbie, "+utterance),
                                 {"action":action})
    def test_negated_quoted_and_arbitrary_text_do_not_navigate(self):
        for phrase in (
            "do not open master canon",
            "open master canon and erase all chapters",
            "open author ../../private",
            "the villain said open story atlas",
            "read my private credential file",
        ):
            self.assertIsNone(parse_author_command(phrase),phrase)
    def test_existing_socket_and_native_window_share_exact_actions(self):
        server=(ROOT/"author"/"control_socket.py").read_text()
        window=(ROOT/"author"/"main.py").read_text()
        for command in VIEWS.values():
            self.assertIn('"'+command+'"',server)
            self.assertIn("'"+command+"'",window)
        self.assertIn("if self.flush():",window)
    def test_no_new_command_or_shell_executor_added(self):
        source=(ROOT/"author"/"commands.py").read_text()
        self.assertNotIn("subprocess",source)
        self.assertNotIn("os.system",source)

if __name__=="__main__":
    unittest.main()
