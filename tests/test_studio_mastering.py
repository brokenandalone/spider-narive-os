"""Mastering source and native-UI regressions, with real FFmpeg when available."""
import json
import math
import os
from pathlib import Path
import shutil
import struct
import tempfile
import threading
import unittest
from unittest.mock import patch
import wave

from studio.session_master import (
    MasterError, PRESETS, _loudnorm, _report, master_wav,
    settings, source_wav,
)


def sine(path, seconds=5, rate=24000):
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(b"".join(
            struct.pack("<h", int(10000 * math.sin(2 * math.pi * 220 * i / rate)))
            for i in range(rate * seconds)
        ))


class MasteringTests(unittest.TestCase):
    def test_presets_and_valid_limits_and_filter_contract(self):
        self.assertEqual(PRESETS["modern_rock"]["integrated_lufs"], -11.0)
        result = settings(preset="dynamic_album")
        self.assertEqual(result["true_peak_dbtp"], -2.0)
        self.assertIn("loudnorm=I=-16.0:TP=-2.0:LRA=12.0", _loudnorm(result))
        for bad in (
            {"preset": "random"},
            {"integrated_lufs": float("nan")},
            {"integrated_lufs": -3},
            {"integrated_lufs": -31},
            {"true_peak_dbtp": 0},
            {"true_peak_dbtp": -4},
            {"lra": 25},
            {"lra": True},
        ):
            with self.subTest(bad=bad), self.assertRaises(MasterError):
                settings(**bad)
        measured = {key: float(index + 1) for index, key in enumerate(
            ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset"))}
        filter_graph = _loudnorm(settings(), measured)
        for key in ("measured_I", "measured_TP", "measured_LRA",
                    "measured_thresh", "offset", "linear=true"):
            self.assertIn(key, filter_graph)

    def test_reject_silent_or_corrupt_audio_and_parse_bad_loudnorm(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bad = root / "broken.wav"
            bad.write_bytes(b"fake audio")
            with self.assertRaises(MasterError):
                source_wav(bad)
            with self.assertRaises(MasterError):
                source_wav(root / "missing.wav")
            real = root / "real.wav"
            sine(real, seconds=1)
            linked = root / "shortcut.wav"
            linked.symlink_to(real)
            with self.assertRaises(MasterError):
                source_wav(linked)
            self.assertEqual(source_wav(real), real.resolve())
            with self.assertRaises(MasterError):
                _report('{"input_i":"-inf","input_tp":"-22","input_lra":"1",'
                        '"input_thresh":"-30","target_offset":"1"}', first=True)
            with self.assertRaises(MasterError):
                _report("No loudness analysis JSON", first=True)

    def test_cancellation_does_not_make_output_or_modify_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original = root / "original.wav"
            sine(original, seconds=1)
            before = original.read_bytes()
            stop = threading.Event()
            stop.set()
            with self.assertRaisesRegex(MasterError, "cancelled"):
                master_wav(original, output_root=root / "master", stop=stop)
            self.assertFalse((root / "master").exists())
            self.assertEqual(original.read_bytes(), before)

    @unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg not installed in runner")
    def test_two_pass_real_wav_and_measured_loudness(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original = root / "sung.wav"
            sine(original, seconds=5)
            before = original.read_bytes()
            result = master_wav(original, output_root=root / "export",
                                preset="balanced_stream", timeout=90)
            self.assertTrue(result.exists())
            self.assertEqual(result.name, "master.wav")
            with wave.open(str(result), "rb") as mastered:
                self.assertEqual(mastered.getframerate(), 48000)
                self.assertEqual(mastered.getnchannels(), 2)
                self.assertEqual(mastered.getsampwidth(), 3)
                self.assertGreater(mastered.getnframes(), 0)
            receipt_path = result.parent / "master-receipt.json"
            receipt = json.loads(receipt_path.read_text())
            self.assertTrue(receipt["two_pass"])
            self.assertTrue(receipt["quality_requires_owner_listening"])
            self.assertEqual(receipt["file_formats"], {"wav": "master.wav"})
            self.assertIn("output_i", receipt["output_measurements"])
            self.assertIn("output_tp", receipt["output_measurements"])
            self.assertEqual(os.stat(result).st_mode & 0o777, 0o600)
            self.assertEqual(original.read_bytes(), before)

    def test_ui_does_not_start_processing_without_user_request(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        try:
            from PyQt5.QtWidgets import QApplication
            from studio.mastering_dialog import MasteringDialog
            from studio.ai_panel import StudioAIPanel
        except ImportError as error:
            self.skipTest(f"PyQt5 not installed: {error}")
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "recording.wav"
            sine(source, seconds=1)
            panel = MasteringDialog(source=source)
            self.assertFalse(panel.stop_button.isEnabled())
            self.assertFalse(panel.play_button.isEnabled())
            self.assertEqual(panel.preset.currentData(), "balanced_stream")
            panel.preset.setCurrentIndex(2)
            self.assertEqual(panel.preset.currentData(), "modern_rock")
            with patch("studio.mastering_dialog.MasteringWorker") as worker:
                panel.start_master()
                worker.assert_called_once()
                worker.return_value.start.assert_called_once()
                args = worker.call_args.args
                self.assertEqual(args[0], str(source))
                self.assertEqual(args[1]["preset"], "modern_rock")
                worker.return_value.stop.set.assert_not_called()
                panel.worker = None
            panel.close()
            ai = StudioAIPanel(temp)
            with patch("studio.ai_panel.MasteringDialog") as editor:
                ai.open_mastering_desk()
                editor.assert_called_once()
                editor.return_value.exec_.assert_called_once()
            ai.close()


if __name__ == "__main__":
    unittest.main()
