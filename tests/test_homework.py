"""Offline tests for Webbie academic drafting; no student data or network."""
import tempfile
import unittest
from pathlib import Path

from study.homework import (build_prompt, save_style, load_style, clear_style,
                            sample_from_file)


class WebbieHomeworkTests(unittest.TestCase):
    def test_drafting_uses_assignment_and_approved_personal_voice(self):
        prompt = build_prompt(
            course="PSY-328",
            assignment="Personality discussion",
            instructions="Compare two theories; 300 words and a real source.",
            materials="Textbook note supplied by the student.",
            sample="I think this matters because people react differently to the same situation.",
            mode="draft")
        self.assertIn("PSY-328", prompt)
        self.assertIn("Compare two theories", prompt)
        self.assertIn("AUTHENTIC USER WRITING SAMPLE", prompt)
        self.assertIn("do not fabricate", prompt.lower())
        self.assertIn("SOURCE NEEDED", prompt)
        self.assertNotIn("submit automatically", prompt)

    def test_revision_requires_existing_draft(self):
        with self.assertRaisesRegex(ValueError, "draft"):
            build_prompt(course="SOC-112", assignment="Reflection",
                         instructions="Revise your work", mode="revise")
        prompt = build_prompt(course="SOC-112", assignment="Reflection",
                              instructions="Revise your work", mode="revise",
                              existing_draft="My writing.", revision="Make it shorter.")
        self.assertIn("My writing.", prompt)
        self.assertIn("Make it shorter.", prompt)

    def test_missing_instructions_never_sends_empty_request(self):
        with self.assertRaises(ValueError):
            build_prompt(course="", assignment="", instructions="")

    def test_local_opt_in_sample_lifecycle(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "private" / "style.txt"
            self.assertEqual(load_style(path), "")
            with self.assertRaises(ValueError):
                save_style("Too brief.", path)
            own_words = "These are words written by the owner. " * 9
            save_style(own_words, path)
            self.assertEqual(load_style(path).strip(), own_words.strip())
            self.assertEqual(path.stat().st_mode & 0o077, 0)
            clear_style(path)
            self.assertFalse(path.exists())

    def test_explicit_local_sample_read_and_extension_guard(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "student.txt"
            path.write_text("Own writing sample", encoding="utf-8")
            self.assertEqual(sample_from_file(path), "Own writing sample")
            invalid = Path(root) / "private.json"
            invalid.write_text("{}", encoding="utf-8")
            with self.assertRaises(ValueError):
                sample_from_file(invalid)


if __name__ == "__main__":
    unittest.main()
