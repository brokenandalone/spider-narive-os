"""A read-only, non-network Studio query interface for future Webbie integration.

No Webbie services are changed. This does not authenticate speakers or grant
device control; the caller must independently enforce Webbie voice permissions.
Actions are allowlisted and cannot record, train, render, delete or launch.
"""
import argparse
import json
from pathlib import Path
import shutil

try:
    from .music_resume import discover_resumable
except ImportError:
    from music_resume import discover_resumable

DEFAULT_SONGS = Path.home() / "Documents/Spider Studio/Music/AI Songs"
ACTIONS = ("capabilities", "status", "pending_jobs")


def query_studio(action, *, songs_root=None):
    if not isinstance(action, str) or action not in ACTIONS:
        raise ValueError("Only read-only Spider Studio query actions are available.")
    result = {
        "schema": "spider-studio-webbie-readonly-v1",
        "action": action,
        "read_only": True,
        "requires_resident_speaker_authorization": True,
        "microphone_activated": False,
        "song_generation_started": False,
        "model_training_started": False,
        "files_modified": False,
    }
    if action == "capabilities":
        result.update({
            "available_commands": list(ACTIONS),
            "ui_actions_requiring_owner_confirmation": [
                "Generate new AI song", "Resume selected existing render",
                "Audit My Voice sample quality", "Prepare private training dataset",
                "Prepare separate train and holdout audio", "Master a WAV",
            ],
            "separate_guitars_generated": False,
            "trained_owner_singer_verified": False,
            "live_webbie_tool_binding_installed": False,
            "note": "This module does not change the active Webbie resident agent.",
        })
    elif action == "status":
        result.update({
            "ffmpeg_available": shutil.which("ffmpeg") is not None,
            "ffprobe_available": shutil.which("ffprobe") is not None,
            "local_music_engine_health": "not_checked_no_network_called",
            "rvc_training_status": "not_checked_no_training_started",
            "not_installed_to_owner_pc_by_github": True,
        })
    else:
        root = Path(songs_root).expanduser() if songs_root is not None else DEFAULT_SONGS
        pending = discover_resumable(root)
        counts = {"queued_or_running": 0, "detached": 0, "error": 0}
        for item in pending:
            counts[item["status"]] += 1
        result.update({
            "unfinished_job_count": len(pending),
            "status_counts": counts,
            "song_names_redacted": True,
            "task_ids_redacted": True,
            "message": "Use the Studio AI window to choose and approve a resume.",
        })
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Read-only Spider Studio information for Webbie planning.")
    parser.add_argument("action", choices=ACTIONS)
    parser.add_argument("--songs-root", type=Path)
    arguments = parser.parse_args(argv)
    report = query_studio(arguments.action, songs_root=arguments.songs_root)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
