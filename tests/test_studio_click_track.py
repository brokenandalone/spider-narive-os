"""Real short click-WAV and tracking-guide exclusion regressions."""
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import wave

from studio.click_track import validate, write_guide
from studio.multitrack import SessionError, export_session
from studio.session_project import inspect_session
from studio.session_mix import mix_plan


class ClickGuideTests(unittest.TestCase):
    def test_real_pcm_countin_with_bar_markers(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            source = write_guide(tempo=120, bars=2, countin_bars=1,
                                 meter="4/4", output_root=folder / "guides")
            self.assertEqual(source.name, "click-guide.wav")
            with wave.open(str(source), "rb") as stream:
                self.assertEqual(stream.getframerate(), 48000)
                self.assertEqual(stream.getnchannels(), 2)
                self.assertEqual(stream.getsampwidth(), 2)
                self.assertEqual(stream.getnframes(), 6 * 48000)
                self.assertNotEqual(stream.readframes(500), b"\0" * 500 * 4)
            receipt = json.loads((source.parent / "guide.json").read_text())
            self.assertEqual(receipt["music_begins_seconds"], 2.0)
            self.assertEqual(len(receipt["bar_markers"]), 3)
            self.assertEqual([x["bar"] for x in receipt["bar_markers"]],
                             [None, 1, 2])
            self.assertTrue(receipt["not_for_final_mix"])
            self.assertEqual(os.stat(source).st_mode & 0o777, 0o600)

    def test_six_eight_is_eighth_note_pulse(self):
        r = validate(tempo=120, bars=3, countin_bars=1, meter="6/8")
        self.assertEqual(r["pulses_per_bar"], 6)
        self.assertEqual(r["length_seconds"], 6.0)
        for kwargs in (
            {"tempo": 0, "bars": 1, "countin_bars": 1, "meter": "4/4"},
            {"tempo": 260, "bars": 1, "countin_bars": 1, "meter": "4/4"},
            {"tempo": 100, "bars": 0, "countin_bars": 1, "meter": "4/4"},
            {"tempo": 100, "bars": 1, "countin_bars": 5, "meter": "4/4"},
            {"tempo": 100, "bars": 1, "countin_bars": 1, "meter": "8/9"},
            {"tempo": 40, "bars": 300, "countin_bars": 4, "meter": "4/4"},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(SessionError):
                validate(**kwargs)

    def test_click_not_in_final_band_mix_even_if_reference_opted_in(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            guide = write_guide(tempo=100, bars=1, countin_bars=1,
                                output_root=root / "guides")
            with wave.open(str(root / "vocal.wav"), "wb") as out:
                out.setnchannels(1)
                out.setsampwidth(2)
                out.setframerate(8000)
                out.writeframes(b"\x00\x00" * 800)
            session_path = export_session([
                {"path": str(root / "vocal.wav"), "role": "lead_vocal", "label": "Voice"},
                {"path": str(guide), "role": "click_guide", "label": "Tracking only"},
            ], title="Never mix click", output_root=root / "sessions")
            data = inspect_session(session_path)
            self.assertEqual(len(data["tracks"]), 2)
            self.assertEqual([t["role"] for t in mix_plan(data)["active"]],
                             ["lead_vocal"])
            self.assertEqual([t["role"] for t in
                              mix_plan(data, include_reference=True)["active"]],
                             ["lead_vocal"])

    def test_early_cancel_keeps_output_folder_uncreated(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            stop = threading.Event()
            stop.set()
            with self.assertRaisesRegex(SessionError, "cancelled"):
                write_guide(output_root=root / "guides", stop=stop)
            self.assertFalse((root / "guides").exists())

    def test_native_dialog_prepares_click_only_after_explicit_action(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        try:
            from PyQt5.QtWidgets import QApplication
            from studio.multitrack_dialog import MultitrackDialog
        except ImportError as error:
            self.skipTest(f"PyQt5 unavailable: {error}")
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as temp:
            dialog = MultitrackDialog(title="Studio Test")
            self.assertIsNone(dialog.click_worker)
            dialog.start_click_guide()
            self.assertIn("tempo", dialog.status.text().lower())
            dialog.tempo.setValue(120)
            with patch("studio.multitrack_dialog.ClickExportWorker") as worker:
                dialog.start_click_guide()
                worker.assert_called_once_with(120, 32, 2, "4/4")
                worker.return_value.start.assert_called_once()
                dialog.click_worker = None
            clicked = write_guide(tempo=120, bars=1, countin_bars=0,
                                  output_root=Path(temp) / "click")
            dialog.click_done(str(clicked), "Ready")
            self.assertEqual(dialog.entries[0]["role"], "click_guide")
            dialog.close()


if __name__ == "__main__":
    unittest.main()
