"""Private multitrack preset tests: no clobbering, no stale WAV references."""
import json
import os
from pathlib import Path
import tempfile
import unittest
import wave

from studio.multitrack import SessionError, export_session
from studio.session_project import inspect_session
from studio.session_presets import save_preset, load_preset, list_presets


def wav(path):
    with wave.open(str(path), "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(8000)
        writer.writeframes(b"\x00\x00" * 800)


def project(root):
    files = []
    for role in ("lead_vocal", "rhythm_guitar", "lead_guitar"):
        source = root / f"{role}.wav"
        wav(source)
        files.append({"path": str(source), "role": role, "label": role})
    folder = export_session(files, title="Preset test song", output_root=root / "sessions")
    return folder, inspect_session(folder)


class SavedMixTests(unittest.TestCase):
    def test_save_and_restore_without_modifying_any_wav(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder, session = project(root)
            originals = {p.name: p.read_bytes() for p in folder.glob("*.wav")}
            first = "01-lead_vocal.wav"
            settings = {first: {"gain": 0.65, "pan": -0.25, "solo": True,
                                "delay_ms": 90}}
            one = save_preset(session, settings, name="Guest chorus lower")
            two = save_preset(session, settings, name="Guest chorus lower")
            self.assertNotEqual(one, two)
            self.assertEqual(len(list_presets(session)), 2)
            recalled = load_preset(session, one)
            self.assertEqual(recalled["name"], "Guest chorus lower")
            self.assertEqual(recalled["controls"][first]["gain"], 0.65)
            self.assertEqual(recalled["controls"][first]["pan"], -0.25)
            self.assertEqual(recalled["controls"][first]["delay_ms"], 90)
            self.assertTrue(recalled["controls"][first]["solo"])
            self.assertFalse(recalled["include_reference"])
            self.assertEqual(os.stat(one).st_mode & 0o777, 0o600)
            for name, data in originals.items():
                self.assertEqual((folder / name).read_bytes(), data)

    def test_stale_or_external_preset_is_not_loaded(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder, session = project(root)
            saved = save_preset(session, {}, name="Trusted")
            external = root / saved.name
            external.write_bytes(saved.read_bytes())
            with self.assertRaisesRegex(SessionError, "local"):
                load_preset(session, external)
            stale = dict(session)
            stale["tracks"] = [dict(t) for t in session["tracks"]]
            stale["tracks"][0]["sha256"] = "0" * 64
            with self.assertRaisesRegex(SessionError, "different or changed"):
                load_preset(stale, saved)
            saved.unlink()
            saved.symlink_to(external)
            with self.assertRaisesRegex(SessionError, "local"):
                load_preset(session, saved)

    def test_preset_rejects_unknown_roles_corrupt_json_and_unsafe_label(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder, session = project(root)
            with self.assertRaises(SessionError):
                save_preset(session, {"fake.wav": {"gain": 1}}, name="bad")
            for bad in ("", "A\nB", "n" * 81):
                with self.assertRaises(SessionError):
                    save_preset(session, {}, name=bad)
            saved = save_preset(session, {}, name="Valid")
            saved.write_text("{invalid", encoding="utf-8")
            with self.assertRaisesRegex(SessionError, "Cannot read"):
                load_preset(session, saved)
            self.assertEqual(list_presets(session), [])

    def test_session_ui_presets_are_roundtrip(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        try:
            from PyQt5.QtWidgets import QApplication
            from PyQt5.QtTest import QTest
            from studio.session_mix_dialog import SessionMixDialog
        except ImportError as error:
            self.skipTest(f"PyQt5 unavailable: {error}")
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder, _ = project(root)
            dialog = SessionMixDialog(folder)
            import time
            end = time.monotonic() + 4
            while dialog.checker is not None and time.monotonic() < end:
                QTest.qWait(10)
            self.assertIsNotNone(dialog.session)
            dialog.table.cellWidget(0, 2).setValue(0.35)
            with unittest.mock.patch("studio.session_mix_dialog.QInputDialog.getText",
                                     return_value=("Heavy guitars", True)):
                dialog.save_mix_preset()
            self.assertEqual(dialog.preset_list.count(), 1)
            dialog.table.cellWidget(0, 2).setValue(1.25)
            dialog.load_mix_preset()
            self.assertEqual(dialog.table.cellWidget(0, 2).value(), 0.35)
            self.assertIn("No render was started", dialog.status.text())
            self.assertFalse(dialog.play_button.isEnabled())
            dialog.close()


if __name__ == "__main__":
    unittest.main()
