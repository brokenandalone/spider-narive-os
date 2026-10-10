"""No-network coverage of Webbie homework review and rubric preflight."""
import unittest

from study.assignment_review import (
    count_words, word_target, draft_checklist, build_review_prompt
)


class AssignmentReviewTests(unittest.TestCase):
    def test_word_counts_and_explicit_limits(self):
        self.assertEqual(count_words("I can't ignore 200 sources."), 5)
        self.assertEqual(word_target("Write 250-350 words."), (250, 350))
        self.assertEqual(word_target("Between 300 and 500 words, please."), (300, 500))
        self.assertEqual(word_target("At least 200 words."), (200, None))
        self.assertEqual(word_target("No more than 800 words."), (None, 800))
        self.assertEqual(word_target("Approximately 300 words."), ("about", 300))
        self.assertIsNone(word_target("Include one citation and three examples."))

    def test_marks_short_draft_and_unresolved_sources_without_claiming_a_grade(self):
        result = draft_checklist("Write 250 to 300 words with APA citations.",
                                 "I noticed something important. [SOURCE NEEDED]")
        self.assertIn("below the stated minimum of 250", result)
        self.assertIn("1 unresolved source/citation", result)
        self.assertIn("Verify every factual claim", result)
        self.assertIn("cannot grade", result)

    def test_checks_include_available_course_materials_without_false_verification(self):
        result = draft_checklist("No more than 100 words.", "One simple sentence.",
                                 materials="Owner-provided lecture notes.")
        self.assertNotIn("No course readings", result)
        self.assertIn("within the detected range", result)
        with self.assertRaises(ValueError):
            draft_checklist("Write anything.", " ")

    def test_review_prompt_only_provides_feedback_and_respects_owner_selection(self):
        draft = "My existing words should remain intact."
        review = build_review_prompt(
            course="SOC-112", assignment="Module Seven",
            instructions="Compare two examples and add peer-reviewed sources.",
            draft=draft, materials="Selected article notes.",
            sample="In my experience, this issue matters.")
        self.assertIn(draft, review)
        self.assertIn("SOC-112", review)
        self.assertIn("Never invent citations", review)
        self.assertIn("Do not rewrite the complete essay", review)
        self.assertIn("Selected article notes.", review)
        self.assertIn("style only", review)
        with self.assertRaises(ValueError):
            build_review_prompt(course="SOC-112", assignment="Test",
                                instructions="Analyze it.", draft="")


if __name__ == "__main__":
    unittest.main()
