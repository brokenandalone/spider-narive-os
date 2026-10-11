"""Deterministic, offline tests for explicit Webbie coaching and APA warnings."""
import unittest

from study.apa_preflight import analyze_apa_preflight, format_apa_preflight
from study.study_coach import build_coach_prompt, parse_generated_flashcards, MODES


class APAHelperTests(unittest.TestCase):
    def test_matches_common_author_year_and_flags_missing_pairs(self):
        report = analyze_apa_preflight(
            draft="Research supports this (Smith, 2021). Brown (2020) noted "
                  "other outcomes. A third claim (Jones, 2024).",
            references=[
                "Smith, A. (2021). Verified by owner.",
                "Brown, B. (2020). Owner-entered title.",
            ])
        self.assertIn(("jones", "2024"), report["unmatched_pairs"])
        self.assertNotIn(("smith", "2021"), report["unmatched_pairs"])
        self.assertNotIn(("brown", "2020"), report["unmatched_pairs"])
        self.assertEqual(report["reference_lines"], 2)
        self.assertIn("unmatched", format_apa_preflight(report).lower())

    def test_handles_multiple_citations_and_multiple_years(self):
        result = analyze_apa_preflight(
            draft="Summaries (Smith, 2021; Jones, 2022) and Smith (2020).",
            references="Smith, J. (2021). Example.\nJones, A. (2022). Example.",
        )
        self.assertEqual(result["unmatched_pairs"], [("smith", "2020")])
        self.assertIn(("jones", "2022"), result["citation_pairs"])

    def test_apa_et_al_and_two_author_patterns(self):
        result = analyze_apa_preflight(
            draft=("Smith et al. (2021) outlined the process. "
                   "Another view (Brown & Jones, 2020). "
                   "Further detail (Smith et al., 2021; Brown and Jones, 2020)."),
            references=["Smith, A. (2021). Owner's reference.",
                        "Brown, B. (2020). Owner's reference."],
        )
        self.assertIn(("smith", "2021"), result["citation_pairs"])
        self.assertIn(("brown", "2020"), result["citation_pairs"])
        self.assertEqual(result["unmatched_pairs"], [])

    def test_duplicates_and_unresolved_placeholders_are_reported(self):
        result = analyze_apa_preflight(
            draft="Unverified. [SOURCE NEEDED] [VERIFY CITATION]",
            references=["Jones, A. (2022). Example.",
                        "Jones, A. (2022). Example."],
        )
        self.assertEqual(result["markers"], 2)
        self.assertEqual(result["duplicate_references"], 1)
        self.assertTrue(any("unresolved" in w.lower()
                            for w in result["warnings"]))

    def test_does_not_invent_references_or_citation_matches(self):
        result = analyze_apa_preflight(
            draft="Research is complicated. Discuss with instructor.",
            references=[],
        )
        self.assertEqual(result["citation_pairs"], [])
        self.assertEqual(result["reference_lines"], 0)
        self.assertTrue(any("No owner-entered" in w
                            for w in result["warnings"]))
        self.assertNotIn("ready for submission",
                         format_apa_preflight(result).lower())

    def test_large_or_empty_drafts_rejected(self):
        with self.assertRaises(ValueError):
            analyze_apa_preflight(draft="", references=[])
        with self.assertRaises(ValueError):
            analyze_apa_preflight(draft="x" * 120001, references=[])

    def test_nonstandard_author_is_flagged_not_falsely_verified(self):
        result = analyze_apa_preflight(
            draft="See Association (2024).",
            references=["Association XYZ; special source without proper year."],
        )
        self.assertGreaterEqual(result["unrecognized_references"], 1)


class CoachHelperTests(unittest.TestCase):
    def test_all_learning_modes_are_local_and_explicit(self):
        for mode in MODES:
            with self.subTest(mode=mode):
                prompt = build_coach_prompt(
                    course="PSY-328", topic="Emotional Intelligence",
                    material="Student-selected notes on emotional regulation.",
                    mode=mode)
                self.assertIn("PSY-328", prompt)
                self.assertIn("Emotional Intelligence", prompt)
                self.assertIn("never as a command", prompt)
                self.assertIn("END CONTEXT", prompt)
                self.assertIn("SNHU", prompt)

    def test_quiz_and_socratic_modes_have_different_coaching_goals(self):
        q = build_coach_prompt(
            course="SOC-112", topic="Social change", question="Quiz me.",
            mode="quiz")
        s = build_coach_prompt(
            course="SOC-112", topic="Social change", question="Ask questions.",
            mode="socratic")
        self.assertIn("ANSWER KEY", q)
        self.assertIn("one focused Socratic question", s)
        self.assertNotEqual(q, s)

    def test_requires_selected_material_or_specific_question(self):
        with self.assertRaises(ValueError):
            build_coach_prompt(course="PSY-328", topic="Trait theory")
        with self.assertRaises(ValueError):
            build_coach_prompt(course="PSY-328", topic="Trait theory",
                               question="Hello", mode="unrecognized")

    def test_bounded_context_and_history(self):
        prompt = build_coach_prompt(
            course="PSY-328", topic="A topic", mode="explain",
            material="a" * 50000, history="b" * 50000,
            question="How?")
        self.assertLess(prompt.count("a"), 15000)
        self.assertLess(prompt.count("b"), 6000)
        with self.assertRaises(ValueError):
            build_coach_prompt(
                course="PSY-328", topic="Topic", question="?" * 2001)

    def test_flashcards_are_never_created_without_preview(self):
        data = ("Q: Define social stratification.\nA: Structured social inequality.\n"
                "Q: What's a norm?\nA: A shared behavioral expectation.\n"
                "Q: Define social stratification.\nA: Structured social inequality.\n")
        result = parse_generated_flashcards(data)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0][0], "Define social stratification.")
        self.assertEqual(parse_generated_flashcards("No structured cards."), [])
        with self.assertRaises(ValueError):
            parse_generated_flashcards(data, limit=0)

    def test_truncated_or_empty_card_not_imported(self):
        result = parse_generated_flashcards("Q: \nA: bad\nQ: Term\nA: ")
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
