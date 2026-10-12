"""Saved take-comp reopening, tamper rejection, private receipt verification."""
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

from studio.take_comp import render_take_comp
from studio.take_comp_library import inspect_take_comp
from studio.multitrack import SessionError


def fixture(tmp):
    root = Path(tmp)
    source = root / "only-vocal-source.wav"
    with wave.open(str(source), "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(8000)
        writer.writeframes(struct.pack("<h", 777) * 16000)
    target = render_take_comp(
        [{"source": str(source), "in_ms": 0, "out_ms": 1000, "at_ms": 250}],
        role="lead_vocal", output_root=root / "comps")
    return source, target


class SavedCompTests(unittest.TestCase):
    def test_reopen_verified_pcm_without_reading_original_source(self):
        with tempfile.TemporaryDirectory() as temp:
            source, target = fixture(temp)
            original = source.read_bytes()
            source.unlink()
            info = inspect_take_comp(target.parent)
            self.assertEqual(info["path"], target)
            self.assertEqual(info["role"], "lead_vocal")
            self.assertEqual(info["duration_seconds"], 1.25)
            self.assertEqual(info["edits"], 1)
            self.assertTrue(info["original_recordings_not_accessed"])
            self.assertEqual(info["sha256"], hashlib.sha256(target.read_bytes()).hexdigest())
            self.assertEqual(original[:4], b"RIFF")
            self.assertFalse(source.exists())

    def test_invalid_or_tampered_output_manifest_and_links_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            source, target = fixture(temp)
            original = target.read_bytes()
            with target.open("ab") as stream:
                stream.write(b"changed")
            with self.assertRaisesRegex(SessionError, "changed"):
                inspect_take_comp(target.parent)
            target.write_bytes(original)
            manifest = target.parent / "comp.json"
            data = json.loads(manifest.read_text())
            data["output"] = "../wrong.wav"
            manifest.write_text(json.dumps(data))
            with self.assertRaisesRegex(SessionError, "name or checksum"):
                inspect_take_comp(target.parent)
            data["output"] = "lead_vocal.wav"
            data["edits"][0]["project_start_frame"] = -25
            manifest.write_text(json.dumps(data))
            with self.assertRaisesRegex(SessionError, "inconsistent"):
                inspect_take_comp(target.parent)
            data["edits"][0]["project_start_frame"] = 2000
            manifest.write_text(json.dumps(data))
            info = inspect_take_comp(target.parent)
            self.assertEqual(info["edits"], 1)
            redirect = target.parent.parent / "linked-take"
            redirect.symlink_to(target.parent, target_is_directory=True)
            with self.assertRaisesRegex(SessionError, "real saved"):
                inspect_take_comp(redirect)

    def test_cancel_before_hash_review(self):
        with tempfile.TemporaryDirectory() as temp:
            _, target = fixture(temp)
            stop = threading.Event()
            stop.set()
            with self.assertRaisesRegex(SessionError, "cancelled"):
                inspect_take_comp(target.parent, stop=stop)

    def test_saved_dialog_requires_verified_audio_at_handoff(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        try:
            from PyQt5.QtWidgets import QApplication
            from studio.take_comp_dialog import TakeCompDialog
        except ImportError as error:
            self.skipTest(f"PyQt5 unavailable: {error}")
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as temp:
            _, target = fixture(temp)
            dialog = TakeCompDialog()
            with patch("studio.take_comp_dialog.QFileDialog.getExistingDirectory",
                       return_value=str(target.parent)):
                dialog.reopen_comp()
            self.assertEqual(dialog.output, target)
            self.assertEqual(dialog.completed_role, "lead_vocal")
            self.assertTrue(dialog.accept.isEnabled())
            seen = []
            dialog.take_accepted.connect(lambda *args: seen.append(args))
            dialog.accept_comp()
            self.assertEqual(len(seen), 1)
            self.assertEqual(seen[0][1], "lead_vocal")
            dialog.accept.setEnabled(True)
            with target.open("ab") as stream:
                stream.write(b"tampered")
            dialog.accept_comp()
            self.assertEqual(len(seen), 1)
            self.assertFalse(dialog.accept.isEnabled())
            self.assertIn("changed", dialog.status.text())
            dialog.close()


if __name__ == "__main__":
    unittest.main()
