"""Detached music-render recovery tests: never resubmit or overwrite takes."""
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import wave

from studio.music_backend import LocalMusicClient, MusicError, StopWaiting
from studio.music_resume import discover_resumable, resume_music_job


def wav(path):
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(8000)
        stream.writeframes(b"\x00\x00" * 800)


def saved_job(root, *, status="detached", takes=2, files=None):
    folder = root / "song-fixture"
    folder.mkdir()
    data = {
        "schema": 1, "backend": "ACE-Step",
        "endpoint": "http://127.0.0.1:8001",
        "status": status, "task_id": "original-render-123",
        "request": {"title": "Broken Sorrow fixture", "takes": takes},
        "files": files or [],
    }
    (folder / "job.json").write_text(json.dumps(data))
    return folder


class SongResumeTests(unittest.TestCase):
    def test_discover_and_recover_without_submitting_new_song(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = saved_job(root)
            found = discover_resumable(root)
            self.assertEqual(len(found), 1)
            self.assertEqual(found[0]["task_id"], "original-render-123")
            client = LocalMusicClient()
            called = []
            def status(path, payload):
                called.append((path, payload))
                return [{"task_id": "original-render-123", "status": 1,
                         "result": [{"file": "/v1/audio?id=1", "status": 1},
                                    {"file": "/v1/audio?id=2", "status": 1}]}]
            def download(_url, target, _stop):
                wav(target)
            with patch.object(client, "health", return_value={"status": "ok"}), \
                 patch.object(client, "_json", side_effect=status), \
                 patch.object(client, "download", side_effect=download):
                result = resume_music_job(client, folder, root, poll_interval=0.05)
            self.assertEqual(result, folder)
            self.assertEqual(called, [
                ("/query_result", {"task_id_list": ["original-render-123"]})
            ])
            self.assertFalse(any(c[0] == "/release_task" for c in called))
            job = json.loads((folder / "job.json").read_text())
            self.assertEqual(job["status"], "completed")
            self.assertEqual(job["task_id"], "original-render-123")
            self.assertEqual(job["files"], ["take-1.wav", "take-2.wav"])
            self.assertEqual(discover_resumable(root), [])

    def test_reconnect_keeps_previously_saved_take_byte_for_byte(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = saved_job(root, files=["take-1.wav"])
            wav(folder / "take-1.wav")
            before = (folder / "take-1.wav").read_bytes()
            client = LocalMusicClient()
            with patch.object(client, "health", return_value={"status": "ok"}), \
                 patch.object(client, "_json", return_value=[
                    {"task_id": "original-render-123", "status": 1,
                     "result": [{"file": "/v1/audio?id=1", "status": 1},
                                {"file": "/v1/audio?id=2", "status": 1}]}]), \
                 patch.object(client, "download", side_effect=lambda url, target, stop: wav(target)) as downloader:
                resume_music_job(client, folder, root)
                self.assertEqual(downloader.call_count, 1)
                self.assertEqual(downloader.call_args.args[1].name, "take-2.wav")
            self.assertEqual((folder / "take-1.wav").read_bytes(), before)

    def test_pre_cancel_never_queries_or_touches_original_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = saved_job(root)
            original = (folder / "job.json").read_bytes()
            stop = threading.Event()
            stop.set()
            client = LocalMusicClient()
            with patch.object(client, "health") as health:
                with self.assertRaises(StopWaiting):
                    resume_music_job(client, folder, root, stop=stop)
                health.assert_not_called()
            self.assertEqual((folder / "job.json").read_bytes(), original)
            self.assertFalse((folder / ".studio-resume.lock").exists())

    def test_invalid_task_missing_id_and_another_endpoint_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = saved_job(root)
            manifest = folder / "job.json"
            data = json.loads(manifest.read_text())
            data["task_id"] = None
            manifest.write_text(json.dumps(data))
            self.assertEqual(discover_resumable(root), [])
            with self.assertRaisesRegex(MusicError, "task ID"):
                resume_music_job(LocalMusicClient(), folder, root)
            data["task_id"] = "valid"
            data["endpoint"] = "http://127.0.0.1:8999"
            manifest.write_text(json.dumps(data))
            with self.assertRaisesRegex(MusicError, "different local service"):
                resume_music_job(LocalMusicClient(), folder, root)
            data["endpoint"] = "http://127.0.0.1:8001"
            data["status"] = "completed"
            manifest.write_text(json.dumps(data))
            with self.assertRaisesRegex(MusicError, "unfinished"):
                resume_music_job(LocalMusicClient(), folder, root)

    def test_lock_and_unexpected_unlisted_take_fail_without_overwriting(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = saved_job(root)
            lock = folder / ".studio-resume.lock"
            lock.write_text("do not touch")
            with self.assertRaisesRegex(MusicError, "Another resume"):
                resume_music_job(LocalMusicClient(), folder, root)
            self.assertEqual(lock.read_text(), "do not touch")
            lock.unlink()
            unexpected = folder / "take-1.wav"
            wav(unexpected)
            before = unexpected.read_bytes()
            client = LocalMusicClient()
            with patch.object(client, "health", return_value={"status": "ok"}), \
                 patch.object(client, "_json", return_value=[
                    {"task_id": "original-render-123", "status": 1,
                     "result": [{"file": "/v1/audio?id=1", "status": 1}]}]), \
                 patch.object(client, "download") as downloaded:
                with self.assertRaisesRegex(MusicError, "outside the manifest"):
                    resume_music_job(client, folder, root)
                downloaded.assert_not_called()
            self.assertEqual(unexpected.read_bytes(), before)

    def test_studio_gui_manually_resumes_only_selected_saved_job(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        try:
            from PyQt5.QtWidgets import QApplication
            from studio.ai_panel import StudioAIPanel
        except ImportError as error:
            self.skipTest(f"PyQt5 missing: {error}")
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = saved_job(root)
            panel = StudioAIPanel(root)
            self.assertEqual(panel.pending_song_jobs.count(), 1)
            with patch("studio.ai_panel.MusicResumeWorker") as worker:
                panel.resume_song()
                worker.assert_not_called()
                panel.pending_song_jobs.setCurrentRow(0)
                panel.resume_song()
                worker.assert_called_once()
                self.assertEqual(worker.call_args.args[1], str(folder))
                worker.return_value.start.assert_called_once()
                panel.resume_worker = None
            panel.close()


if __name__ == "__main__":
    unittest.main()
