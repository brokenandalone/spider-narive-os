"""Reconnect to an already-submitted local ACE-Step song task, NEVER resubmit it.

The only network calls use the existing loopback-restricted LocalMusicClient.
Existing takes and voice originals are never modified or overwritten.
"""
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import wave

try:
    from .music_backend import LocalMusicClient, MusicError, StopWaiting, write_manifest
except ImportError:
    from music_backend import LocalMusicClient, MusicError, StopWaiting, write_manifest

_ALLOWED = {"queued_or_running", "detached", "error"}


def _read_job(folder, output_root):
    root = Path(output_root).expanduser().resolve()
    path = Path(folder).expanduser()
    if (not path.is_dir() or path.is_symlink() or not path.name.startswith("song-")
            or path.resolve().parent != root):
        raise MusicError("Choose an existing Spider Studio song job in your private song library.")
    path = path.resolve()
    manifest = path / "job.json"
    if (manifest.is_symlink() or not manifest.is_file()
            or not 0 < manifest.stat().st_size <= 128 * 1024):
        raise MusicError("This song has no valid local resume manifest.")
    try:
        job = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError) as error:
        raise MusicError("Cannot read this song render status.") from error
    if (not isinstance(job, dict) or job.get("schema") != 1
            or job.get("backend") != "ACE-Step"
            or job.get("status") not in _ALLOWED):
        raise MusicError("Only previously submitted unfinished local ACE-Step tasks can resume.")
    task_id = job.get("task_id")
    if not isinstance(task_id, str) or not 0 < len(task_id) <= 200:
        raise MusicError("No saved task ID; cannot safely resubmit an uncertain task.")
    requested = job.get("request", {})
    takes = requested.get("takes") if isinstance(requested, dict) else None
    if type(takes) is not int or not 1 <= takes <= 2:
        raise MusicError("The original request has an invalid take count.")
    files = job.get("files")
    if (not isinstance(files, list) or len(files) > takes
            or any(item not in ("take-1.wav", "take-2.wav") for item in files)
            or len(set(files)) != len(files)):
        raise MusicError("Saved take manifest is inconsistent; refusing to overwrite.")
    for name in files:
        existing = path / name
        if existing.is_symlink() or not existing.is_file():
            raise MusicError("Previously saved take is missing or linked; review it manually.")
        try:
            with wave.open(str(existing), "rb") as audio:
                if audio.getnframes() <= 0 or audio.getframerate() <= 0:
                    raise MusicError("Previously saved take is empty or invalid.")
        except (OSError, wave.Error, EOFError) as error:
            raise MusicError("Previously saved take is not an intact WAV.") from error
    if len(files) == takes:
        raise MusicError("All requested takes already exist; no restart is needed.")
    return path, manifest, job


def discover_resumable(output_root):
    """Read-only: list incomplete job IDs, without making network calls."""
    root = Path(output_root).expanduser()
    if not root.is_dir() or root.is_symlink():
        return []
    pending = []
    for manifest in sorted(root.glob("song-*/job.json"), reverse=True):
        try:
            path, _, job = _read_job(manifest.parent, root)
            title = job.get("request", {}).get("title", "")
            if not isinstance(title, str):
                title = ""
            pending.append({"directory": str(path), "title": title[:120],
                            "status": job["status"], "task_id": job["task_id"]})
        except (MusicError, OSError, ValueError):
            continue
    return pending


def resume_music_job(client, directory, output_root, *, stop=None,
                     progress=None, timeout=1800, poll_interval=2):
    """Query saved task and fetch missing takes; never call /release_task."""
    if not isinstance(client, LocalMusicClient):
        raise MusicError("Use the authenticated local music-engine adapter.")
    if (type(timeout) not in (int, float) or not 1 <= timeout <= 7200
            or type(poll_interval) not in (int, float) or not 0.05 <= poll_interval <= 60):
        raise MusicError("Invalid saved-job polling limits.")
    stop = stop if stop is not None else threading.Event()
    progress = progress or (lambda message: None)
    path, manifest, job = _read_job(directory, output_root)
    if job.get("endpoint") != client.base_url:
        raise MusicError("The saved song belongs to a different local service endpoint.")
    if stop.is_set():
        raise StopWaiting("Resume cancelled before contacting the local music service.")
    # Exclusive lock. Separate GUI resumes cannot write one job simultaneously.
    lock = path / ".studio-resume.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise MusicError("Another resume owns this job (or a stale lock needs review).") from error
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(str(os.getpid()))
    try:
        client.health()
        progress("Reconnected to local music engine. Checking saved task ID...")
        deadline = time.monotonic() + timeout
        task_id = job["task_id"]
        while True:
            if stop.is_set():
                raise StopWaiting("Stopped waiting. Existing local engine render may continue.")
            if time.monotonic() >= deadline:
                raise MusicError("Resumed waiting timed out. The original render may continue.")
            rows = client._json("/query_result", {"task_id_list": [task_id]})
            if not isinstance(rows, list):
                raise MusicError("Local engine returned an invalid job-status response.")
            item = next((x for x in rows if isinstance(x, dict)
                         and x.get("task_id") == task_id), None)
            if item is None or type(item.get("status")) is not int:
                raise MusicError("Saved song ID not found at this local engine.")
            if item["status"] == 2:
                raise MusicError("The original song job failed; use a new request only if desired.")
            if item["status"] == 1:
                results = item.get("result")
                if isinstance(results, str):
                    try:
                        results = json.loads(results)
                    except (ValueError, TypeError) as error:
                        raise MusicError("Invalid returned song-take metadata.") from error
                if (not isinstance(results, list) or not results
                        or len(results) > job["request"]["takes"]
                        or any(not isinstance(x, dict) or x.get("status") != 1
                               or not isinstance(x.get("file"), str) for x in results)):
                    raise MusicError("Resumed job produced invalid audio metadata.")
                for n, result in enumerate(results, 1):
                    name = f"take-{n}.wav"
                    target = path / name
                    if name in job["files"]:
                        continue
                    if target.exists() or target.is_symlink():
                        raise MusicError("A take already exists outside the manifest; refusing overwrite.")
                    progress(f"Saving missing take {n} of {len(results)}...")
                    client.download(result["file"], target, stop)
                    job["files"].append(name)
                    write_manifest(manifest, job)
                job["status"] = "completed"
                job.pop("error", None)
                write_manifest(manifest, job)
                return path
            if item["status"] != 0:
                raise MusicError("Unknown status for resumed local music job.")
            stop.wait(poll_interval)
    except (StopWaiting, MusicError) as error:
        job["status"] = "detached" if isinstance(error, StopWaiting) else "error"
        job["error"] = str(error)
        write_manifest(manifest, job)
        raise
    finally:
        lock.unlink(missing_ok=True)
