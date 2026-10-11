"""Audio-provenance warnings and Qt session audit integration tests."""
import os
from pathlib import Path
import struct
import tempfile
import threading
import time
import unittest
import wave
from studio.multitrack import export_session, SessionError
from studio.session_stem_audit import assess_stem_independence


def wav(path, seed=1000, frames=16000):
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(8000)
        data = [int(seed * ((x % 17) / 9 - 0.7)) for x in range(frames)]
        output.writeframes(b"".join(struct.pack("<h", value) for value in data))


def project(root, *, duplicate=False, reference=False):
    roles = ["lead_vocal", "rhythm_guitar", "lead_guitar"]
    if reference:
        roles.append("reference_mix")
    files = []
    for i, role in enumerate(roles):
        file = root / f"{role}.wav"
        wav(file, 1000 if duplicate and i < 2 else 1000 + i * 330)
        files.append({"path": str(file), "role": role, "label": role})
    session = export_session(files, title="Independence audit", output_root=root / "exports")
    return session


class StemAuditTests(unittest.TestCase):
    def test_detects_identical_bytes_as_separate_role_without_calling_it_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = project(root, duplicate=True)
            result = assess_stem_independence(folder)
            self.assertEqual(result["track_count"], 3)
            self.assertFalse(result["all_stems_independently_verified"])
            self.assertTrue(result["needs_human_listening_review"])
            matches = result["identical_or_sampled_pcm_collisions"]
            self.assertTrue(any("identical_wav_bytes" == x["type"] for x in matches))
            self.assertTrue(any("matching_sampled_pcm_content" == x["type"] for x in matches))
            self.assertEqual({f.name for f in folder.glob("*.wav")},
                             {"01-lead_vocal.wav", "02-rhythm_guitar.wav", "03-lead_guitar.wav"})

    def test_nonmatching_pcm_makes_no_claim_of_instrument_isolation(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = project(Path(tmp))
            result = assess_stem_independence(folder)
            self.assertEqual(result["identical_or_sampled_pcm_collisions"], [])
            self.assertFalse(result["all_stems_independently_verified"])
            self.assertTrue(any("labels are user claims" in s
                                for s in result["notices"]))

    def test_reference_song_flag_and_changed_track_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = project(Path(tmp), reference=True)
            result = assess_stem_independence(folder)
            self.assertEqual(result["reference_tracks"], 1)
            self.assertTrue(any("full-song reference" in s
                                for s in result["notices"]))
            target = folder / "02-rhythm_guitar.wav"
            with target.open("ab") as writer:
                writer.write(b"modified")
            with self.assertRaisesRegex(SessionError, "checksum"):
                assess_stem_independence(folder)

    def test_stop_and_real_background_ui(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = project(Path(tmp))
            stop = threading.Event()
            stop.set()
            with self.assertRaisesRegex(SessionError, "cancelled"):
                assess_stem_independence(folder, stop=stop)
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
            try:
                from PyQt5.QtWidgets import QApplication
                from PyQt5.QtTest import QTest
                from studio.session_mix_dialog import SessionMixDialog
            except ImportError as error:
                self.skipTest(f"PyQt5 unavailable: {error}")
            app = QApplication.instance() or QApplication([])
            dialog = SessionMixDialog(folder)
            deadline = time.monotonic() + 5
            while dialog.checker is not None and time.monotonic() < deadline:
                QTest.qWait(10)
            self.assertIsNotNone(dialog.session)
            self.assertTrue(dialog.stem_button.isEnabled())
            dialog.start_stem_check()
            deadline = time.monotonic() + 5
            while dialog.stem_worker is not None and time.monotonic() < deadline:
                QTest.qWait(10)
            self.assertIsNone(dialog.stem_worker)
            self.assertTrue(dialog.quality_button.isEnabled())
            self.assertIn("No matching audio", dialog.quality_report.toPlainText())
            self.assertFalse(dialog.include_reference.isChecked())
            dialog.close()


if __name__ == "__main__":
    unittest.main()
