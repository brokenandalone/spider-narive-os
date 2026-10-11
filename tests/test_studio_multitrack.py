"""Regression checks for real WAV multitrack sessions and Studio UI handoff."""
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import wave

from studio.multitrack import SessionError, export_session


def make_wav(path, frames=800):
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(8000)
        wav.writeframes(b"\x00\x00" * frames)


class SessionTests(unittest.TestCase):
    def test_two_guitars_and_co_vocal_are_real_distinct_files(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            roles = ["lead_vocal", "backing_vocal", "rhythm_guitar",
                     "lead_guitar", "bass", "drums", "piano_keys"]
            tracks = []
            for index, role in enumerate(roles):
                source = root / f"{role}.wav"
                make_wav(source, frames=800 + index * 40)
                tracks.append({"path": str(source), "role": role, "label": role})
            exported = export_session(tracks, title="Broken Sorrow Session",
                                      tempo_bpm=105, output_root=root / "exports")
            data = json.loads((exported / "session.json").read_text())
            self.assertEqual(data["project_title"], "Broken Sorrow Session")
            self.assertEqual(data["tempo_bpm"], 105)
            self.assertEqual([part["role"] for part in data["tracks"]], roles)
            self.assertEqual(len(list(exported.glob("*.wav"))), 7)
            self.assertFalse(data["independence_verified"])
            self.assertTrue(data["reference_mix_is_not_isolated_stems"])
            self.assertTrue(all(part["start_seconds"] == 0.0 for part in data["tracks"]))
            self.assertIn("filename,role,label", (exported / "tracks.csv").read_text())
            self.assertIn("Ardour", (exported / "README.txt").read_text())
            for track, original in zip(data["tracks"], tracks):
                self.assertEqual((exported / track["filename"]).read_bytes(),
                                 Path(original["path"]).read_bytes())
                self.assertEqual(os.stat(exported / track["filename"]).st_mode & 0o777, 0o600)
            self.assertEqual(os.stat(exported).st_mode & 0o777, 0o700)

    def test_duplicate_source_disallowed_even_with_new_role(self):
        with tempfile.TemporaryDirectory() as workspace:
            source = Path(workspace) / "song.wav"
            make_wav(source)
            with self.assertRaisesRegex(SessionError, "same WAV"):
                export_session([
                    {"path": str(source), "role": "rhythm_guitar", "label": "Rhythm"},
                    {"path": str(source), "role": "lead_guitar", "label": "Lead"},
                ], title="No fake independent guitars", output_root=Path(workspace) / "out")
            self.assertFalse((Path(workspace) / "out").exists())

    def test_refuses_symlinks_and_bad_audio_without_creating_session(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            original = root / "lead.wav"
            make_wav(original)
            linked = root / "shortcut.wav"
            linked.symlink_to(original)
            for bad in (linked, root / "invalid.wav"):
                if bad.name == "invalid.wav":
                    bad.write_bytes(b"not a pcm wav")
                with self.subTest(bad=bad.name), self.assertRaises(SessionError):
                    export_session([{"path": str(bad), "role": "lead_vocal", "label": "Lead"}],
                                   title="Bad track", output_root=root / "exports")
            self.assertFalse((root / "exports").exists())

    def test_stop_preserves_originals_and_output_is_new_every_time(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            source = root / "lead.wav"
            make_wav(source)
            original = source.read_bytes()
            plan = [{"path": str(source), "role": "lead_vocal", "label": "Owner"}]
            with self.assertRaisesRegex(SessionError, "cancelled"):
                export_session(plan, title="Stopped", output_root=root / "out",
                               stop=_stopped())
            self.assertFalse((root / "out").exists())
            one = export_session(plan, title="Song", output_root=root / "out")
            two = export_session(plan, title="Song", output_root=root / "out")
            self.assertNotEqual(one, two)
            self.assertEqual(source.read_bytes(), original)

    def test_invalid_roles_csv_injection_and_track_limits(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            source = root / "lead.wav"
            make_wav(source)
            for role, label in (("fake_guitar_ai", "lead"), ("lead_vocal", "=1+1"),
                                ("lead_vocal", "=dangerous\ncell")):
                with self.assertRaises(SessionError):
                    export_session([{"path": str(source), "role": role, "label": label}],
                                   title="Invalid", output_root=root / "out")
            with self.assertRaises(SessionError):
                export_session([], title="Nothing", output_root=root / "out")
            with self.assertRaises(SessionError):
                export_session([{"path": str(source), "role": "lead_vocal", "label": "lead"}],
                               title="Bad\nTitle", output_root=root / "out")


def _stopped():
    event = threading.Event()
    event.set()
    return event


class SessionUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        try:
            from PyQt5.QtWidgets import QApplication
            from studio.multitrack_dialog import MultitrackDialog
            cls.app = QApplication.instance() or QApplication([])
            cls.dialog_class = MultitrackDialog
        except ImportError as error:
            raise unittest.SkipTest("PyQt5 not installed in this test environment") from error

    def test_dialog_does_not_generate_audio_and_rejects_duplicate(self):
        with tempfile.TemporaryDirectory() as workspace:
            source = Path(workspace) / "song.wav"
            make_wav(source)
            dialog = self.dialog_class(
                [{"path": str(source), "role": "reference_mix", "label": "AI whole song"}],
                title="Broken Sorrow")
            self.assertEqual(dialog.track_list.count(), 1)
            self.assertEqual(dialog.entries[0]["role"], "reference_mix")
            with self.assertRaises(SessionError):
                dialog.add_track_path(source, "rhythm_guitar")
            self.assertIsNone(dialog.worker)
            self.assertIsNone(dialog.exported_path)
            dialog.close()

    def test_native_studio_button_hands_selected_sources_to_editor(self):
        from studio.ai_panel import StudioAIPanel
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            source = root / "reference.wav"
            lead = root / "lead.wav"
            make_wav(source)
            make_wav(lead)
            panel = StudioAIPanel(root)
            panel.title.setText("Two guitar band")
            panel.mix_vocal.setText(str(lead))
            with patch.object(panel, "selected", return_value=source), \
                 patch("studio.ai_panel.MultitrackDialog") as editor:
                panel.open_multitrack_session()
                editor.assert_called_once()
                seeded = editor.call_args.args[0]
                self.assertEqual([item["role"] for item in seeded],
                                 ["reference_mix", "lead_vocal"])
                editor.return_value.exec_.assert_called_once()
            panel.close()


if __name__ == "__main__":
    unittest.main()
