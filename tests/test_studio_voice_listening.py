"""Regression tests for real, private, randomized human My Voice A/B trials."""
import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile
import threading
import unittest
from unittest.mock import patch
import wave

from studio.voice_profile import VoiceSampleError
from studio.voice_listening import CRITERIA, create_voice_trial, save_voice_review


def make_audio(path, value=1000, seconds=2, rate=8000):
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(rate)
        audio.writeframes(struct.pack("<h", value) * int(seconds * rate))


def ratings(a=3, b=4):
    return {key: {part: score for part in CRITERIA}
            for key, score in (("A", a), ("B", b))}


class VoiceTrialTests(unittest.TestCase):
    def test_blind_a_b_copies_hashes_private_files_and_preserves_recordings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original, converted = root / "original.wav", root / "converted.wav"
            make_audio(original, value=2000)
            make_audio(converted, value=3200)
            before = original.read_bytes(), converted.read_bytes()
            with patch("studio.voice_listening.secrets.randbelow", return_value=1):
                trial = create_voice_trial(original, converted, output_root=root / "trials")
            receipt = json.loads((trial / "trial.json").read_text())
            secret = json.loads((trial / "private-assignment.json").read_text())
            self.assertEqual(secret["assignment"], {"A": "converted", "B": "original"})
            self.assertEqual(receipt["candidate_labels"], ["A", "B"])
            self.assertNotIn("assignment", receipt)
            self.assertFalse(receipt["trained_model_verified"])
            self.assertFalse(receipt["audio_level_matched"])
            self.assertEqual((trial / "A.wav").read_bytes(), before[1])
            self.assertEqual((trial / "B.wav").read_bytes(), before[0])
            self.assertEqual(before, (original.read_bytes(), converted.read_bytes()))
            self.assertEqual(os.stat(trial).st_mode & 0o777, 0o700)
            for item in trial.iterdir():
                self.assertEqual(os.stat(item).st_mode & 0o777, 0o600)

    def test_manual_listener_review_does_not_approve_identity_and_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_audio(root / "a.wav", value=1000)
            make_audio(root / "b.wav", value=1500)
            trial = create_voice_trial(root / "a.wav", root / "b.wav",
                                       output_root=root / "trials")
            with self.assertRaisesRegex(VoiceSampleError, "Listen to both"):
                save_voice_review(trial, ratings(), listened_to_both=False)
            one = save_voice_review(trial, ratings(), listened_to_both=True,
                                    notes="Warm timbre; some notes need work")
            two = save_voice_review(trial, ratings(4, 2), listened_to_both=True)
            self.assertNotEqual(one, two)
            self.assertEqual(len(list(trial.glob("review-*.json"))), 2)
            record = json.loads(one.read_text())
            self.assertTrue(record["subjective_review_only"])
            self.assertFalse(record["identity_auto_verified"])
            self.assertFalse(record["training_started"])
            self.assertEqual(record["ratings"]["B"]["identity"], 4)
            self.assertEqual(os.stat(one).st_mode & 0o777, 0o600)

    def test_refuses_identical_audio_bad_timing_and_cancel(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_audio(root / "a.wav", value=1000)
            make_audio(root / "copy.wav", value=1000)
            with self.assertRaisesRegex(VoiceSampleError, "identical audio"):
                create_voice_trial(root / "a.wav", root / "copy.wav", output_root=root)
            make_audio(root / "far.wav", value=2000, seconds=8)
            with self.assertRaisesRegex(VoiceSampleError, "differ by"):
                create_voice_trial(root / "a.wav", root / "far.wav", output_root=root)
            make_audio(root / "b.wav", value=1500)
            stop = threading.Event()
            stop.set()
            with self.assertRaisesRegex(VoiceSampleError, "cancelled"):
                create_voice_trial(root / "a.wav", root / "b.wav",
                                   output_root=root / "out", stop=stop)
            self.assertFalse((root / "out").exists())

    def test_review_rejects_invalid_scores_and_rechecked_tampered_wave(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_audio(root / "a.wav", value=1000)
            make_audio(root / "b.wav", value=1500)
            trial = create_voice_trial(root / "a.wav", root / "b.wav",
                                       output_root=root / "private")
            attempts = [
                {"A": {c: 3 for c in CRITERIA}},
                ratings(a=0), ratings(a=True),
                {"A": {"identity": 3}, "B": {c: 3 for c in CRITERIA}},
            ]
            for invalid in attempts:
                with self.subTest(data=invalid), self.assertRaises(VoiceSampleError):
                    save_voice_review(trial, invalid, listened_to_both=True)
            with self.assertRaisesRegex(VoiceSampleError, "notes"):
                save_voice_review(trial, ratings(), listened_to_both=True, notes="z"*501)
            with (trial / "B.wav").open("ab") as altered:
                altered.write(b"tamper")
            with self.assertRaisesRegex(VoiceSampleError, "changed"):
                save_voice_review(trial, ratings(), listened_to_both=True)
            self.assertEqual(list(trial.glob("review-*.json")), [])

    def test_ui_has_explicit_owner_controls_and_does_not_auto_train(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        try:
            from PyQt5.QtWidgets import QApplication
            from studio.voice_review_dialog import VoiceReviewDialog
            from studio.ai_panel import StudioAIPanel
        except ImportError as error:
            self.skipTest(f"PyQt5 unavailable: {error}")
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_audio(root / "a.wav", value=1000)
            make_audio(root / "b.wav", value=1500)
            dialog = VoiceReviewDialog(root / "a.wav", root / "b.wav")
            self.assertIsNone(dialog.trial)
            self.assertFalse(dialog.save_button.isEnabled())
            with patch("studio.voice_review_dialog.TrialWorker") as worker:
                dialog.start_trial()
                worker.assert_called_once()
                worker.return_value.start.assert_called_once()
                dialog.worker = None
            trial = create_voice_trial(root / "a.wav", root / "b.wav",
                                       output_root=root / "trial")
            dialog.trial_done(str(trial), "ready")
            self.assertTrue(dialog.save_button.isEnabled())
            dialog.save_review()
            self.assertIn("Listen to both", dialog.status.text())
            dialog.heard.setChecked(True)
            dialog.save_review()
            self.assertIn("NOT automatic", dialog.status.text())
            dialog.close()
            panel = StudioAIPanel(tmp)
            panel.rvc_vocal.setText(str(root / "a.wav"))
            panel.last_converted_vocal = root / "b.wav"
            with patch("studio.ai_panel.VoiceReviewDialog") as review:
                panel.open_voice_review()
                review.assert_called_once_with(
                    original=str(root / "a.wav"),
                    converted=str(root / "b.wav"), parent=panel)
                review.return_value.exec_.assert_called_once()
            panel.close()


if __name__ == "__main__":
    unittest.main()
