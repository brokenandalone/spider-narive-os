"""Regression tests for explicitly limited Spider Studio PCM preview checks."""
import math
import os
from pathlib import Path
import tempfile
import threading
import unittest
import wave

from studio.session_qc import analyze_wav, audit_session_audio
from studio.multitrack import export_session, SessionError


def wav(path, value=0, *, seconds=2, rate=8000):
    with wave.open(str(path), "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(rate)
        writer.writeframes(value.to_bytes(2, "little", signed=True) * rate * seconds)


class QualityTests(unittest.TestCase):
    def test_silent_and_near_clipping_pcm_are_detected_without_edits(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            silent = root / "silent.wav"
            clip = root / "clipped.wav"
            wav(silent)
            wav(clip, 32767)
            before = silent.read_bytes(), clip.read_bytes()
            mute_report = analyze_wav(silent)
            clip_report = analyze_wav(clip)
            self.assertTrue(any("silent" in w for w in mute_report["warnings"]))
            self.assertAlmostEqual(clip_report["peak_dbfs"], 0.0, delta=0.1)
            self.assertGreater(clip_report["near_clip_samples"], 0)
            self.assertTrue(any("Near-full" in w for w in clip_report["warnings"]))
            self.assertEqual((silent.read_bytes(), clip.read_bytes()), before)

    def test_samples_two_edges_only_not_entire_long_audio(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "long.wav"
            wav(path, seconds=21)
            result = analyze_wav(path)
            self.assertAlmostEqual(result["sampled_seconds"], 10, delta=0.1)
            self.assertEqual(result["total_seconds"], 21)
            self.assertFalse(result["complete_file_scanned"])

    def test_quality_summarizes_sample_rate_mismatch_and_refuses_changed_wavs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            a, b = root / "vocal.wav", root / "guitar.wav"
            wav(a, value=2000, rate=8000)
            wav(b, value=1000, rate=11025)
            project = export_session([
                {"path": str(a), "role": "lead_vocal", "label": "lead"},
                {"path": str(b), "role": "lead_guitar", "label": "guitar"}
            ], title="Loudness preflight", output_root=root / "project")
            result = audit_session_audio(project)
            self.assertEqual(len(result["tracks"]), 2)
            self.assertTrue(result["quick_preview_only"])
            self.assertTrue(any("sample rates differ" in w for w in result["warnings"]))
            (project / "01-lead_vocal.wav").write_bytes(b"modified")
            with self.assertRaises(SessionError):
                audit_session_audio(project)

    def test_rejects_invalid_sampling_and_respects_stop(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "recording.wav"
            wav(path)
            for value in (0, -1, 11, "5", float("nan")):
                with self.subTest(value=value), self.assertRaises(SessionError):
                    analyze_wav(path, edge_seconds=value)
            stop = threading.Event()
            stop.set()
            with self.assertRaisesRegex(SessionError, "cancelled"):
                analyze_wav(path, stop=stop)

    def test_native_quality_preview_is_only_started_on_click(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        try:
            from PyQt5.QtWidgets import QApplication
            from PyQt5.QtTest import QTest
            from studio.session_mix_dialog import SessionMixDialog
        except ImportError as error:
            self.skipTest(f"Qt unavailable: {error}")
        import time
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "vocal.wav"
            wav(source)
            project = export_session(
                [{"path": str(source), "role": "lead_vocal", "label": "owner"}],
                title="One vocalist", output_root=root / "project")
            dialog = SessionMixDialog(project)
            deadline = time.monotonic() + 5
            while dialog.checker is not None and time.monotonic() < deadline:
                QTest.qWait(10)
            self.assertIsNotNone(dialog.session)
            self.assertIsNone(dialog.quality_worker)
            self.assertTrue(dialog.quality_button.isEnabled())
            dialog.start_quality_check()
            deadline = time.monotonic() + 5
            while dialog.quality_worker is not None and time.monotonic() < deadline:
                QTest.qWait(10)
            self.assertIsNone(dialog.quality_worker)
            self.assertIn("01-lead_vocal.wav", dialog.quality_report.toPlainText())
            self.assertIn("first and last five seconds", dialog.quality_report.toPlainText())
            dialog.close()


if __name__ == "__main__":
    unittest.main()
