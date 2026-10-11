"""My Voice preview audit and real consented train/holdout isolation tests."""
import hashlib
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

from studio.voice_profile import VoiceSampleError
from studio.voice_quality import audit_voice_library
from studio.voice_training_split import training_split_plan, prepare_training_split


def sample(path, *, amplitude=8000, seconds=6, rate=16000):
    with wave.open(str(path), "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(rate)
        writer.writeframes(b"".join(
            struct.pack("<h", int(amplitude * math.sin(i * 2 * math.pi * 160 / rate)))
            for i in range(seconds * rate)
        ))


def dataset(root, *, count=4):
    folder = root / "consented-dataset"
    audio = folder / "audio"
    audio.mkdir(parents=True)
    entries = []
    for index in range(count):
        target = audio / f"clip-{index + 1:04d}.wav"
        sample(target, amplitude=7000 + index * 500)
        entries.append({
            "file": "audio/" + target.name,
            "duration_seconds": 6.0,
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest()
        })
    (folder / "manifest.json").write_text(json.dumps({
        "schema": 1, "speaker": "owner", "owner_consent": True,
        "training_started": False, "samples": entries
    }))
    return folder


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                     "Local FFmpeg/ffprobe required for voice preview tests")
class VoiceAuditTests(unittest.TestCase):
    def test_audit_identifies_silence_and_identical_duplicate_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            loud = root / "sample-loud.wav"
            duplicate = root / "sample-clone.wav"
            quiet = root / "sample-silence.wav"
            sample(loud)
            shutil.copyfile(loud, duplicate)
            sample(quiet, amplitude=0)
            before = {p.name: p.read_bytes() for p in (loud, duplicate, quiet)}
            report = audit_voice_library(root)
            self.assertEqual(report["total_recordings"], 3)
            self.assertFalse(report["full_audio_scanned"])
            self.assertFalse(report["training_started"])
            self.assertFalse(report["trained_model_verified"])
            duplicate_count = sum(row["duplicate"] for row in report["files"])
            self.assertEqual(duplicate_count, 1)
            silence = next(x for x in report["files"] if x["filename"] == quiet.name)
            self.assertFalse(silence["accepted_for_preview_count"])
            self.assertIn("quiet", " ".join(silence["warnings"]))
            self.assertLess(report["unique_preview_accepted_seconds"], 600)
            self.assertEqual({p.name: p.read_bytes() for p in (loud, duplicate, quiet)}, before)

    def test_cancel_before_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sample(root / "sample-a.wav")
            stop = threading.Event()
            stop.set()
            with self.assertRaisesRegex(VoiceSampleError, "cancelled"):
                audit_voice_library(root, stop=stop)


@unittest.skipUnless(shutil.which("ffprobe"), "ffprobe needed to validate duration")
class HoldoutTests(unittest.TestCase):
    def test_different_files_really_staged_and_model_not_trained(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            owner_data = dataset(root)
            planned = training_split_plan(owner_data)
            self.assertEqual(len(planned["train"]), 3)
            self.assertEqual(len(planned["holdout"]), 1)
            self.assertEqual(planned["training_seconds"], 18.0)
            self.assertFalse(planned["ready_for_ten_minute_training"])
            with self.assertRaisesRegex(VoiceSampleError, "Confirm permission"):
                prepare_training_split(owner_data)
            result = prepare_training_split(owner_data, consent=True)
            other = prepare_training_split(owner_data, consent=True)
            self.assertNotEqual(result, other)
            r = json.loads((result / "split.json").read_text())
            self.assertTrue(r["owner_consent"])
            self.assertFalse(r["training_started"])
            self.assertFalse(r["voice_identity_qualified"])
            train = {p.name for p in (result / "train/audio").glob("*")}
            holdout = {p.name for p in (result / "holdout/audio").glob("*")}
            self.assertEqual(len(train), 3)
            self.assertEqual(len(holdout), 1)
            self.assertTrue(train.isdisjoint(holdout))
            for group in ("train", "holdout"):
                for row in r[group]:
                    target = result / group / row["file"]
                    self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(),
                                     row["sha256"])
                    self.assertEqual(os.stat(target).st_mode & 0o777, 0o600)
            for original in r["train"] + r["holdout"]:
                self.assertTrue((owner_data / original["file"]).exists())

    def test_reject_changed_data_external_path_and_stale_duration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            owner_data = dataset(root)
            manifest_file = owner_data / "manifest.json"
            entries = json.loads(manifest_file.read_text())
            entries["samples"][0]["file"] = "../private.wav"
            manifest_file.write_text(json.dumps(entries))
            with self.assertRaises(VoiceSampleError):
                training_split_plan(owner_data)
            entries["samples"][0]["file"] = "audio/clip-0001.wav"
            entries["samples"][0]["duration_seconds"] = 650.0
            manifest_file.write_text(json.dumps(entries))
            with self.assertRaisesRegex(VoiceSampleError, "duration metadata"):
                training_split_plan(owner_data)
            entries["samples"][0]["duration_seconds"] = 6.0
            manifest_file.write_text(json.dumps(entries))
            clip = owner_data / "audio" / "clip-0001.wav"
            with clip.open("ab") as out:
                out.write(b"altered")
            with self.assertRaisesRegex(VoiceSampleError, "checksum"):
                training_split_plan(owner_data)

    def test_duplicate_content_rejected_and_cancellation_creates_no_split(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            owner_data = dataset(root)
            clips = list((owner_data / "audio").glob("*.wav"))
            shutil.copyfile(clips[0], clips[1])
            contents = json.loads((owner_data / "manifest.json").read_text())
            contents["samples"][1]["sha256"] = hashlib.sha256(clips[1].read_bytes()).hexdigest()
            (owner_data / "manifest.json").write_text(json.dumps(contents))
            with self.assertRaisesRegex(VoiceSampleError, "Duplicate voice clips"):
                training_split_plan(owner_data)
            owner_data = dataset(root / "second")
            stop = threading.Event()
            stop.set()
            with self.assertRaisesRegex(VoiceSampleError, "cancelled"):
                prepare_training_split(owner_data, consent=True, stop=stop)
            self.assertFalse((owner_data / "training-splits").exists())

    def test_consent_missing_and_audio_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            owner_data = dataset(root)
            data_file = owner_data / "manifest.json"
            record = json.loads(data_file.read_text())
            record["owner_consent"] = False
            data_file.write_text(json.dumps(record))
            with self.assertRaisesRegex(VoiceSampleError, "consented"):
                training_split_plan(owner_data)
            record["owner_consent"] = True
            data_file.write_text(json.dumps(record))
            audio = owner_data / "audio"
            moved = owner_data / "actual-audio"
            audio.rename(moved)
            audio.symlink_to(moved)
            with self.assertRaisesRegex(VoiceSampleError, "symlink"):
                training_split_plan(owner_data)


class VoicePanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        try:
            from PyQt5.QtWidgets import QApplication
            cls.app = QApplication.instance() or QApplication([])
        except ImportError as error:
            raise unittest.SkipTest("PyQt5 unavailable") from error

    def test_voice_quality_button_does_not_train_or_send_network(self):
        from studio.ai_panel import StudioAIPanel
        with tempfile.TemporaryDirectory() as tmp:
            panel = StudioAIPanel(tmp)
            self.assertTrue(panel.voice_quality_button.isEnabled())
            self.assertFalse(panel.split_button.isEnabled())
            with patch("studio.ai_panel.VoiceQualityWorker") as worker:
                panel.check_voice_quality()
                worker.assert_called_once()
                worker.return_value.start.assert_called_once()
                panel.voice_quality_worker = None
            panel.voice_quality_done({
                "total_recordings": 1, "unique_preview_accepted_seconds": 12,
                "files": [{"filename": "sample-1.wav", "warnings": ["quiet"]}]
            })
            self.assertIn("quiet", panel.voice_quality_details.toPlainText())
            panel.close()

    def test_training_split_requires_explicit_yes_and_prepared_dataset(self):
        from PyQt5.QtWidgets import QMessageBox
        from studio.ai_panel import StudioAIPanel
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            panel = StudioAIPanel(tmp)
            with patch("studio.ai_panel.TrainingSplitWorker") as worker:
                panel.start_training_split()
                worker.assert_not_called()
                made = root / "prepared"
                made.mkdir()
                (made / "manifest.json").write_text("{}")
                panel.last_training_set = made
                with patch("studio.ai_panel.QMessageBox.question",
                           return_value=QMessageBox.No):
                    panel.start_training_split()
                    worker.assert_not_called()
                with patch("studio.ai_panel.QMessageBox.question",
                           return_value=QMessageBox.Yes):
                    panel.start_training_split()
                    worker.assert_called_once_with(made)
                    worker.return_value.start.assert_called_once()
                panel.training_split_worker = None
            panel.close()


if __name__ == "__main__":
    unittest.main()
