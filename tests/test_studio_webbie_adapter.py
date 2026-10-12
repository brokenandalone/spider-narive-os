"""Webbie-to-Studio read-only query contract tests, no resident service changes."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from studio.webbie_adapter import query_studio, main


class StudioReadOnlyToolsTests(unittest.TestCase):
    def test_allowlist_and_no_device_control(self):
        with self.assertRaises(ValueError):
            query_studio("open_program")
        with self.assertRaises(ValueError):
            query_studio("record_microphone")
        with self.assertRaises(ValueError):
            query_studio("train_owner_model")
        with patch("studio.webbie_adapter.discover_resumable") as discovery:
            result = query_studio("capabilities")
            discovery.assert_not_called()
            self.assertTrue(result["read_only"])
            self.assertFalse(result["live_webbie_tool_binding_installed"])
            self.assertFalse(result["trained_owner_singer_verified"])
            self.assertFalse(result["song_generation_started"])
            self.assertTrue(result["requires_resident_speaker_authorization"])

    def test_pending_jobs_summary_redacts_song_name_task_ids_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            task = root / "song-pending"
            task.mkdir()
            (task / "job.json").write_text(json.dumps({
                "schema": 1, "backend": "ACE-Step",
                "endpoint": "http://127.0.0.1:8001",
                "task_id": "sensitive-task-id-999",
                "status": "detached",
                "files": [],
                "request": {"title": "PRIVATE SONG NAME", "takes": 1},
            }))
            with patch("studio.webbie_adapter.shutil.which", return_value=None):
                report = query_studio("pending_jobs", songs_root=root)
            self.assertEqual(report["unfinished_job_count"], 1)
            self.assertEqual(report["status_counts"]["detached"], 1)
            self.assertTrue(report["task_ids_redacted"])
            self.assertNotIn("PRIVATE SONG NAME", json.dumps(report))
            self.assertNotIn("sensitive-task-id-999", json.dumps(report))
            self.assertNotIn(str(root), json.dumps(report))

    def test_status_does_not_ping_engine_or_launch_training(self):
        with patch("studio.webbie_adapter.discover_resumable") as files:
            result = query_studio("status")
            self.assertEqual(result["local_music_engine_health"],
                             "not_checked_no_network_called")
            self.assertFalse(result["microphone_activated"])
            self.assertFalse(result["model_training_started"])
            files.assert_not_called()

    def test_cli_prints_structured_json_without_side_effects(self):
        with patch("builtins.print") as printing:
            self.assertEqual(main(["capabilities"]), 0)
        result = json.loads(printing.call_args.args[0])
        self.assertEqual(result["schema"], "spider-studio-webbie-readonly-v1")
        self.assertEqual(result["available_commands"],
                         ["capabilities", "status", "pending_jobs"])


if __name__ == "__main__":
    unittest.main()
