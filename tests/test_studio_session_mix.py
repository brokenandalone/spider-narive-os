"""Offline regression tests for saved Studio sessions and their verified mixer."""
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import wave

from studio.multitrack import SessionError, export_session
from studio.session_project import inspect_session
from studio.session_mix import ffmpeg_command, mix_plan, render_session


def make_wav(path, frames=1024, rate=8000):
    with wave.open(str(path), "wb") as track:
        track.setnchannels(1)
        track.setsampwidth(2)
        track.setframerate(rate)
        track.writeframes(b"\x00\x00" * frames)


def fixture(root, *, with_reference=True):
    roles = ["lead_vocal", "backing_vocal", "rhythm_guitar", "lead_guitar"]
    if with_reference:
        roles.append("reference_mix")
    original = []
    for role in roles:
        path = root / f"original-{role}.wav"
        make_wav(path, rate=8000 if role != "lead_guitar" else 11025)
        original.append({"path": str(path), "role": role, "label": role})
    session = export_session(original, title="Broken Sorrow - Master",
                             tempo_bpm=120, output_root=root / "exports")
    return session, original


class SessionVerifyTests(unittest.TestCase):
    def test_reopen_existing_project_without_original_source_recordings(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            exported, original = fixture(root)
            for file in original:
                Path(file["path"]).unlink()
            loaded = inspect_session(exported)
            self.assertTrue(loaded["verified"])
            self.assertEqual(loaded["title"], "Broken Sorrow - Master")
            self.assertEqual(loaded["sample_rates"], [8000, 11025])
            self.assertEqual(len(loaded["tracks"]), 5)
            self.assertTrue(all(t["path"].parent == exported for t in loaded["tracks"]))

    def test_modified_wav_is_rejected_even_when_header_still_valid(self):
        with tempfile.TemporaryDirectory() as temporary:
            exported, _ = fixture(Path(temporary))
            track = next(exported.glob("01-*.wav"))
            with track.open("r+b") as output:
                output.seek(-2, 2)
                output.write(b"\x01\x01")
            with self.assertRaisesRegex(SessionError, "checksum"):
                inspect_session(exported)

    def test_manifest_traversal_link_and_mismatch_blocked(self):
        with tempfile.TemporaryDirectory() as temporary:
            exported, _ = fixture(Path(temporary))
            manifest = exported / "session.json"
            data = json.loads(manifest.read_text())
            data["tracks"][0]["filename"] = "../outside.wav"
            manifest.write_text(json.dumps(data))
            with self.assertRaisesRegex(SessionError, "filename"):
                inspect_session(exported)
            data["tracks"][0]["filename"] = "01-lead_vocal.wav"
            manifest.write_text(json.dumps(data))
            first = exported / "01-lead_vocal.wav"
            first.unlink()
            first.symlink_to(exported / "02-backing_vocal.wav")
            with self.assertRaisesRegex(SessionError, "linked"):
                inspect_session(exported)

    def test_session_verification_stop(self):
        with tempfile.TemporaryDirectory() as temporary:
            exported, _ = fixture(Path(temporary))
            stop = threading.Event()
            stop.set()
            with self.assertRaisesRegex(SessionError, "cancelled"):
                inspect_session(exported, stop=stop)


class SessionMixTests(unittest.TestCase):
    def test_reference_excluded_and_solo_and_mute(self):
        with tempfile.TemporaryDirectory() as temporary:
            exported, _ = fixture(Path(temporary))
            verified = inspect_session(exported)
            normal = mix_plan(verified)
            self.assertEqual(len(normal["active"]), 4)
            self.assertFalse(normal["reference_included"])
            voice = "01-lead_vocal.wav"
            guitar = "04-lead_guitar.wav"
            plan = mix_plan(verified, {
                voice: {"solo": True, "gain": 0.75, "pan": -0.5},
                guitar: {"solo": True, "mute": True},
            })
            self.assertEqual([x["filename"] for x in plan["active"]], [voice])
            self.assertEqual(plan["active"][0]["gain"], 0.75)
            self.assertEqual(plan["active"][0]["pan"], -0.5)
            ref = mix_plan(verified, include_reference=True)
            self.assertEqual(len(ref["active"]), 5)
            self.assertTrue(ref["reference_included"])
            self.assertIn("may double", ref["warnings"][0])
            with self.assertRaisesRegex(SessionError, "No independent"):
                mix_plan(verified, {t["filename"]: {"mute": True}
                                    for t in verified["tracks"]})

    def test_cannot_invent_files_or_pass_invalid_control_values(self):
        with tempfile.TemporaryDirectory() as temporary:
            exported, _ = fixture(Path(temporary), with_reference=False)
            session = inspect_session(exported)
            first = session["tracks"][0]["filename"]
            invalid = [
                {"missing.wav": {"gain": 1}},
                {first: {"gain": True}},
                {first: {"gain": float("nan")}},
                {first: {"pan": float("inf")}},
                {first: {"pan": 1.1}},
                {first: {"delay_ms": -10}},
                {first: {"delay_ms": 2.5}},
                {first: {"mute": 1}},
                {first: {"unknown": 2}},
            ]
            for control in invalid:
                with self.subTest(control=control), self.assertRaises(SessionError):
                    mix_plan(session, control)
            with self.assertRaises(SessionError):
                mix_plan(session, include_reference="true")

    def test_command_has_independent_inputs_delays_pan_and_safe_export(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder, _ = fixture(root, with_reference=False)
            verified = inspect_session(folder)
            lead = verified["tracks"][0]["filename"]
            plan = mix_plan(verified, {lead: {"delay_ms": 300, "pan": 1.0}})
            destination = root / "never-before.wav"
            command = ffmpeg_command("/usr/bin/ffmpeg", plan, destination)
            graph = command[command.index("-filter_complex") + 1]
            self.assertIn("adelay=300:all=1", graph)
            self.assertIn("c0=0.0000*c0|c1=1.0000*c1", graph)
            self.assertIn("alimiter=limit=0.95", graph)
            self.assertEqual(command.count("-i"), 4)
            self.assertIn("-n", command)
            self.assertNotIn("sh", command[:1])
            destination.write_bytes(b"do not clobber")
            with self.assertRaisesRegex(SessionError, "new WAV"):
                ffmpeg_command("/usr/bin/ffmpeg", plan, destination)

    @unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg is not installed here")
    def test_real_offline_render_is_valid_and_sources_untouched(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder, sources = fixture(root, with_reference=False)
            files = {p["path"]: Path(p["path"]).read_bytes() for p in sources}
            first = "01-lead_vocal.wav"
            output = render_session(folder,
                                    controls={first: {"gain": 0.8, "pan": -0.2,
                                                      "delay_ms": 25}},
                                    output_root=root / "mixes")
            self.assertTrue(output.is_file())
            with wave.open(str(output), "rb") as reader:
                self.assertEqual(reader.getframerate(), 48000)
                self.assertEqual(reader.getnchannels(), 2)
                self.assertGreater(reader.getnframes(), 0)
            receipt = json.loads((output.parent / "mix-receipt.json").read_text())
            self.assertEqual(receipt["active_filenames"][0], first)
            self.assertEqual(receipt["tracks"][0]["delay_ms"], 25)
            self.assertTrue(receipt["verified_before_render"])
            self.assertEqual(os.stat(output).st_mode & 0o777, 0o600)
            for src, data in files.items():
                self.assertEqual(Path(src).read_bytes(), data)


class SessionMixUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        try:
            from PyQt5.QtWidgets import QApplication
            from PyQt5.QtTest import QTest
            from studio.session_mix_dialog import SessionMixDialog
            cls.app = QApplication.instance() or QApplication([])
            cls.dialog_class = SessionMixDialog
            cls.QTest = QTest
        except ImportError as error:
            raise unittest.SkipTest("PyQt5 is unavailable") from error

    def test_load_verified_session_and_snapshot_controls(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder, _ = fixture(Path(temporary))
            window = self.dialog_class(folder)
            deadline = time.monotonic() + 4
            while window.checker is not None and time.monotonic() < deadline:
                self.QTest.qWait(10)
            self.assertIsNotNone(window.session)
            self.assertEqual(window.table.rowCount(), 5)
            self.assertTrue(window.mix_button.isEnabled())
            window.table.cellWidget(0, 2).setValue(0.6)
            window.table.cellWidget(0, 5).setChecked(True)
            self.assertEqual(window.mix_controls()["01-lead_vocal.wav"]["gain"], 0.6)
            self.assertTrue(window.mix_controls()["01-lead_vocal.wav"]["solo"])
            self.assertFalse(window.include_reference.isChecked())
            window.close()

    def test_studio_can_open_session_console_without_touching_music_engine(self):
        from studio.ai_panel import StudioAIPanel
        with tempfile.TemporaryDirectory() as temporary:
            panel = StudioAIPanel(temporary)
            with patch("studio.ai_panel.SessionMixDialog") as window, \
                 patch("studio.ai_panel.LocalMusicClient") as music:
                panel.open_saved_session_mix()
                window.assert_called_once_with(parent=panel)
                window.return_value.exec_.assert_called_once()
                music.assert_not_called()
            panel.close()


if __name__ == "__main__":
    unittest.main()
