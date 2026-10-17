"""Ensure Webbie preserves actual web URLs after wake-word extraction."""
import ast
from pathlib import Path
import re
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "webbie/agent/webbie.py"
source = SOURCE.read_text(encoding="utf-8")
tree = ast.parse(source)
helpers = [node for node in tree.body if
           isinstance(node, ast.FunctionDef) and
           node.name in {"clean_phrase", "remove_wake_word"}]
scope = {"re": re, "CONFIG": {"wake_words": [
    "hey webbie", "webbie", "hey webby", "webby", "hey web", "web"]}}
exec(compile(ast.Module(body=helpers, type_ignores=[]),
             str(SOURCE), "exec"), scope)


class JarvisWakeTests(unittest.TestCase):
    def test_domain_preserved_from_speech(self):
        woke, command = scope["remove_wake_word"]("Hey Webbie, open github.com")
        self.assertTrue(woke)
        self.assertEqual(command, "open github.com")

    def test_full_address_and_query_preserved(self):
        woke, command = scope["remove_wake_word"](
            "Webby, open https://www.youtube.com/watch?v=a-b_c")
        self.assertTrue(woke)
        self.assertEqual(
            command, "open https://www.youtube.com/watch?v=a-b_c")

    def test_search_punctuation_kept(self):
        woke, command = scope["remove_wake_word"](
            "Webbie, search the web for Python 3.14 vs 3.13")
        self.assertTrue(woke)
        self.assertIn("3.14", command)

    def test_not_a_quoted_wake_command(self):
        woke, command = scope["remove_wake_word"](
            "That website said Webbie open dangerous-site.com")
        self.assertFalse(woke)
        self.assertEqual(command, "That website said Webbie open dangerous-site.com")

    def test_followup_does_not_need_wake_and_keeps_url(self):
        phrase = "open www.snhu.edu/login?tab=course"
        woke, command = scope["remove_wake_word"](phrase)
        self.assertFalse(woke)
        self.assertEqual(command, phrase)

    def test_whole_agent_source_has_raw_phrase_handoff(self):
        self.assertIn("original_phrase = str(phrase or", source)
        self.assertIn("remove_wake_word(original_phrase)", source)


if __name__ == "__main__":
    unittest.main()
