"""My Voice training-set preparation is offline, opt-in and never trains a model."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from studio import voice_dataset as dataset
from studio.voice_profile import VoiceSampleError


class VoiceDatasetTests(unittest.TestCase):
    def _make_clips(self, source, count=2):
        source.mkdir(exist_ok=True)
        clips = []
        for index in range(count):
            file = source / f"sample-{index:04d}.wav"
            file.write_bytes(f"private-test-vocal-{index}".encode())
            clips.append(file)
        return clips

    def test_duration_checks_local_ffprobe(self):
        with patch.object(dataset.shutil, "which", return_value="/usr/bin/ffprobe"):
            with patch.object(dataset.subprocess, "run") as process:
                process.return_value.stdout = "33.12345\n"
                self.assertEqual(dataset.duration_seconds("/tmp/example.wav"), 33.123)
                args, kwargs = process.call_args
                self.assertEqual(args[0][0], "ffprobe")
                self.assertEqual(kwargs["timeout"], 15)
                process.return_value.stdout = "not audio"
                with self.assertRaises(VoiceSampleError):
                    dataset.duration_seconds("/tmp/example.wav")

    def test_prepare_requires_consent_and_10_minutes(self):
        with tempfile.TemporaryDirectory() as t:
            home = Path(t)
            source = home / "My Voice"
            self._make_clips(source)
            output = home / "Datasets"
            with patch.object(dataset, "duration_seconds", return_value=299.0):
                self.assertFalse(dataset.inspect_samples(source)["ready_to_prepare"])
                with self.assertRaises(VoiceSampleError):
                    dataset.prepare_training_set(source, output, consent=True)
            with patch.object(dataset, "duration_seconds", return_value=305.0):
                with self.assertRaises(VoiceSampleError):
                    dataset.prepare_training_set(source, output)
            self.assertFalse(output.exists())

    def test_prepared_copies_are_private_and_do_not_modify_originals(self):
        with tempfile.TemporaryDirectory() as t:
            home = Path(t)
            source = home / "My Voice"
            clips = self._make_clips(source)
            originals = {c.name: c.read_bytes() for c in clips}
            with patch.object(dataset, "duration_seconds", return_value=305.0):
                prepared = dataset.prepare_training_set(source, home / "Datasets", consent=True)
            self.assertEqual(prepared.stat().st_mode & 0o777, 0o700)
            self.assertEqual((prepared / "audio").stat().st_mode & 0o777, 0o700)
            manifest_file = prepared / "manifest.json"
            self.assertEqual(manifest_file.stat().st_mode & 0o777, 0o600)
            manifest = json.loads(manifest_file.read_text())
            self.assertEqual(manifest["seconds"], 610.0)
            self.assertFalse(manifest["trained_model_created"])
            self.assertFalse(manifest["training_started"])
            self.assertEqual(len(manifest["samples"]), 2)
            for idx, record in enumerate(manifest["samples"]):
                output = prepared / record["file"]
                self.assertEqual(output.stat().st_mode & 0o777, 0o600)
                self.assertEqual(record["sha256"], hashlib.sha256(output.read_bytes()).hexdigest())
                self.assertEqual(output.read_bytes(), clips[idx].read_bytes())
            self.assertEqual({c.name: c.read_bytes() for c in clips}, originals)

    def test_rejects_invalid_clip_and_symlinked_destination(self):
        with tempfile.TemporaryDirectory() as t:
            home = Path(t)
            source = home / "samples"; self._make_clips(source)
            dest = home / "dest"; dest.mkdir()
            linked = home / "link"; linked.symlink_to(dest, target_is_directory=True)
            with patch.object(dataset, "duration_seconds", side_effect=[301.0, VoiceSampleError("bad")]):
                info = dataset.inspect_samples(source)
                self.assertEqual(info["rejected_clips"], 1)
                self.assertFalse(info["ready_to_prepare"])
            with patch.object(dataset, "duration_seconds", return_value=350.0):
                with self.assertRaises(VoiceSampleError):
                    dataset.prepare_training_set(source, linked, consent=True)


if __name__ == "__main__":
    unittest.main()
