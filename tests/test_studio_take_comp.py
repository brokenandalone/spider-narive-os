"""Recorded independent instrument/vocal comping acceptance and safety tests."""
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

from studio.multitrack import SessionError, export_session
from studio.take_comp import render_take_comp, _read_layout, _fade_frames


def pcm(path, *, rate=8000, seconds=3, channels=1, width=2, peak=2000):
    frames = int(rate * seconds)
    with wave.open(str(path), "wb") as output:
        output.setframerate(rate)
        output.setnchannels(channels)
        output.setsampwidth(width)
        data = bytearray()
        for index in range(frames):
            number = ((index % 121) - 60) * peak // 60
            for _ in range(channels):
                if width == 1:
                    data.append(128 + (number // 256))
                else:
                    data.extend(int(number).to_bytes(width, "little", signed=True))
        output.writeframes(data)


def region(source, frm, to, at):
    return {"source": str(source), "in_ms": frm, "out_ms": to, "at_ms": at}


def sound_bytes(path):
    with wave.open(str(path), "rb") as audio:
        return (audio.getframerate(), audio.getnchannels(),
                audio.getsampwidth(), audio.getnframes(), audio.readframes(audio.getnframes()))


class TakeCompTests(unittest.TestCase):
    def test_sample_accurate_region_stitching_with_project_timeline_silence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first, second = root / "lead-one.wav", root / "lead-two.wav"
            pcm(first, peak=1000)
            pcm(second, peak=1900)
            originals = [first.read_bytes(), second.read_bytes()]
            edits = [region(second, 0, 500, 1500), region(first, 500, 1000, 0)]
            target = render_take_comp(edits, role="lead_guitar", fade_ms=0,
                                      output_root=root / "comps")
            rate, channels, width, frames, raw = sound_bytes(target)
            self.assertEqual((rate, channels, width, frames), (8000, 1, 2, 16000))
            self.assertEqual(raw[:8000], sound_bytes(first)[4][8000:16000])
            self.assertEqual(raw[8000:24000], b"\0" * 16000)
            self.assertEqual(raw[24000:], sound_bytes(second)[4][:8000])
            receipt = json.loads((target.parent / "comp.json").read_text())
            self.assertEqual([edit["project_start_frame"] for edit in receipt["edits"]],
                             [0, 12000])
            self.assertTrue(receipt["timeline_zero_aligned"])
            self.assertFalse(receipt["audio_generated_by_model"])
            self.assertFalse(receipt["preexisting_isolation_owner_attested"])
            self.assertEqual(receipt["output_sha256"],
                             hashlib.sha256(target.read_bytes()).hexdigest())
            self.assertEqual([first.read_bytes(), second.read_bytes()], originals)
            self.assertEqual(os.stat(target.parent).st_mode & 0o777, 0o700)
            self.assertEqual(os.stat(target).st_mode & 0o777, 0o600)
            self.assertEqual(os.stat(target.parent / "comp.json").st_mode & 0o777, 0o600)

    def test_fades_samples_for_8bit_16bit_24bit_32bit_and_stereo(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for width in (1, 2, 3, 4):
                with self.subTest(width=width):
                    source = root / f"rhythm-{width}.wav"
                    pcm(source, channels=2, width=width, peak=2000)
                    path = render_take_comp(
                        [region(source, 0, 1000, 0)], role="rhythm_guitar",
                        fade_ms=10, output_root=root / "comps")
                    rate, channels, w, count, raw = sound_bytes(path)
                    self.assertEqual((rate, channels, w, count), (8000, 2, width, 8000))
                    self.assertEqual(raw, _fade_frames(sound_bytes(source)[4][:len(raw)],
                                                       width=width, channels=2,
                                                       start=0, total=8000, fade_frames=80))
                    self.assertNotEqual(raw, sound_bytes(source)[4][:len(raw)])
                    self.assertEqual(len(raw), 8000 * 2 * width)

    def test_overlaps_mismatched_pcm_and_bad_regions_refused_before_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            one, two = root / "one.wav", root / "two.wav"
            pcm(one)
            pcm(two, rate=16000)
            attempts = [
                [region(one, 0, 1000, 0), region(one, 1000, 2000, 500)],
                [region(one, 1000, 1000, 0)],
                [region(one, -1, 2000, 0)],
                [region(one, 0, 5000, 0)],
                [region(one, 0, 1000, 599500)],
                [region(one, 0, 500, True)],
                [region(one, 0, 500, 0), region(two, 0, 500, 1000)],
            ]
            for attempt in attempts:
                with self.subTest(attempt=attempt):
                    with self.assertRaises(SessionError):
                        render_take_comp(attempt, role="lead_vocal",
                                         output_root=root / "private")
            self.assertFalse((root / "private").exists())
            with self.assertRaisesRegex(SessionError, "one real recorded"):
                render_take_comp([region(one, 0, 1000, 0)], role="reference_mix")
            with self.assertRaisesRegex(SessionError, "fades"):
                render_take_comp([region(one, 0, 1000, 0)], role="bass", fade_ms=17)

    def test_malformed_source_symlink_and_cancellation_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.wav"
            pcm(source)
            linked = root / "link.wav"
            linked.symlink_to(source)
            with self.assertRaises(SessionError):
                _read_layout([region(linked, 0, 500, 0)], "lead_vocal", 10)
            with self.assertRaises(SessionError):
                _read_layout([{"source": str(source), "in_ms": 0, "out_ms": 400,
                               "at_ms": 0, "extraneous": "ignored"}],
                             "lead_vocal", 10)
            stop = threading.Event()
            stop.set()
            with self.assertRaisesRegex(SessionError, "cancelled"):
                render_take_comp([region(source, 0, 1000, 0)],
                                 role="lead_vocal", output_root=root / "out",
                                 stop=stop)
            self.assertFalse((root / "out").exists())
            out = root / "not-safe"
            out.symlink_to(root)
            with self.assertRaisesRegex(SessionError, "symlink"):
                render_take_comp([region(source, 0, 1000, 0)],
                                 role="lead_vocal", output_root=out)

    def test_rendered_comp_is_real_valid_independent_track_for_daw_export(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "guest-singing.wav"
            pcm(source)
            target = render_take_comp(
                [region(source, 0, 500, 500)], role="backing_vocal",
                output_root=root / "comps", fade_ms=5)
            session = export_session([
                {"path": str(target), "role": "backing_vocal", "label": "Guest backing"},
            ], title="Comped singer export", output_root=root / "sessions")
            self.assertTrue((session / "01-backing_vocal.wav").is_file())
            self.assertEqual(sound_bytes(session / "01-backing_vocal.wav"),
                             sound_bytes(target))
            self.assertEqual(sound_bytes(source)[3], 24000)


class TakeCompUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        try:
            from PyQt5.QtWidgets import QApplication
            cls.app = QApplication.instance() or QApplication([])
        except ImportError as error:
            raise unittest.SkipTest(f"PyQt5 missing: {error}")

    def test_dialog_and_session_accept_only_owner_approved_render(self):
        from studio.take_comp_dialog import TakeCompDialog
        from studio.multitrack_dialog import MultitrackDialog
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original = root / "guitar.wav"
            pcm(original)
            dialog = TakeCompDialog()
            self.assertFalse(dialog.accept.isEnabled())
            dialog.source.setText(str(original))
            dialog.source_in.setValue(0)
            dialog.source_out.setValue(500)
            dialog.timeline_start.setValue(0)
            dialog.add_region()
            self.assertEqual(len(dialog.edits), 1)
            emitted = []
            dialog.take_accepted.connect(lambda *x: emitted.append(x))
            dialog.accept_comp()
            self.assertEqual(emitted, [])
            with patch("studio.take_comp_dialog.CompWorker") as worker:
                dialog.render()
                worker.assert_called_once()
                worker.return_value.start.assert_called_once()
                dialog.worker = None
            created = render_take_comp(
                [region(original, 0, 500, 0)], role="rhythm_guitar",
                output_root=root / "test")
            dialog.rendered(str(created), "saved")
            self.assertTrue(dialog.accept.isEnabled())
            dialog.accept_comp()
            self.assertEqual(emitted[0][0], str(created))
            dialog.close()
            studio = MultitrackDialog()
            self.assertTrue(studio.comp_button.isEnabled())
            studio.add_comped_take(*emitted[0])
            self.assertEqual(studio.entries[0]["role"], "rhythm_guitar")
            self.assertEqual(len(studio.entries), 1)
            studio.close()


if __name__ == "__main__":
    unittest.main()
