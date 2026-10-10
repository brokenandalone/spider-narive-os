"""Contract tests for Spider Studio AI intent controls; no audio backend or microphone."""
import importlib.util
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[1] / "studio/ai_controls.py"
spec = importlib.util.spec_from_file_location("spider_ai_controls", MODULE)
module = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = module
spec.loader.exec_module(module)
CreativeControls = module.CreativeControls


class AIControlsTests(unittest.TestCase):
    def test_default_is_user_voice_first_but_not_ready_without_profile(self):
        plan = CreativeControls().plan()
        self.assertFalse(plan["ready_for_backend"])
        self.assertIn("singer profile", plan["blocker"])
        self.assertFalse(plan["generation_started"])

    def test_default_backend_never_claims_any_control_is_effective(self):
        plan = CreativeControls().plan(singer_profile_available=True)
        self.assertTrue(plan["ready_for_backend"])
        self.assertTrue(all(not x["enabled"] for x in plan["controls"].values()))

    def test_supported_audio_influence_requires_an_actual_reference(self):
        controls = CreativeControls(vocal_mode="standard_ai_voice")
        no_source = controls.plan(backend_supported={"audio_influence"})
        self.assertFalse(no_source["controls"]["audio_influence"]["enabled"])
        with_source = controls.plan(
            backend_supported={"audio_influence"}, reference_available=True)
        self.assertTrue(with_source["controls"]["audio_influence"]["enabled"])

    def test_cleanup_and_identity_need_owner_reference_and_backend(self):
        controls = CreativeControls(vocal_mode="my_ai_voice", vocal_cleanup=30)
        missing = controls.plan(
            backend_supported={"vocal_cleanup", "vocal_identity"})
        self.assertFalse(missing["controls"]["vocal_identity"]["enabled"])
        ready = controls.plan(
            backend_supported={"vocal_cleanup", "vocal_identity"},
            singer_profile_available=True)
        self.assertTrue(ready["controls"]["vocal_cleanup"]["enabled"])
        self.assertEqual(ready["controls"]["vocal_identity"]["requested"], 90)

    def test_real_recording_is_a_distinct_mode(self):
        controls = CreativeControls(vocal_mode="actual_recording")
        self.assertFalse(controls.plan()["ready_for_backend"])
        self.assertTrue(controls.plan(actual_vocal_available=True)["ready_for_backend"])

    def test_reject_bad_values_and_unknown_capability(self):
        for bad in (-1, 101, 2.5, "50", True):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    CreativeControls(weirdness=bad)
        with self.assertRaises(ValueError):
            CreativeControls(quality="ultra")
        with self.assertRaises(ValueError):
            CreativeControls().plan(backend_supported={"not_a_real_slider"})

    def test_fast_mode_cannot_claim_suno_v6_mini_is_running(self):
        plan = CreativeControls(
            vocal_mode="instrumental", song_mode="quick",
            quality="max").plan()
        self.assertEqual(plan["owner_intent"]["song_mode"], "quick")
        self.assertEqual(plan["audio_engine"], "unselected")
        self.assertTrue(plan["ready_for_backend"])
        self.assertFalse(plan["generation_started"])


if __name__ == "__main__":
    unittest.main()
