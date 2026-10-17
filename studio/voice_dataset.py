"""Prepare private, consented My Voice samples for an RVC training session.

Only stages source audio; never installs models or launches training.
Requires ffprobe locally to measure real usable duration.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid
try:
    from .voice_profile import HOME, samples, VoiceSampleError
except ImportError:
    from voice_profile import HOME, samples, VoiceSampleError

MIN_TRAIN_SECONDS = 600.0


def duration_seconds(path):
    if not shutil.which("ffprobe"):
        raise VoiceSampleError("ffprobe is required to check recording length.")
    try:
        finished = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, timeout=15, check=True,
        )
        value = float(finished.stdout.strip())
    except (OSError, ValueError, subprocess.TimeoutExpired, subprocess.CalledProcessError) as error:
        raise VoiceSampleError("A sample has no valid measurable audio duration.") from error
    if not 0.2 <= value <= 3600:
        raise VoiceSampleError("A recording must be real audio, under an hour, and not empty.")
    return round(value, 3)


def inspect_samples(root=None):
    entries = []
    for path in samples(root):
        try:
            seconds = duration_seconds(path)
            entries.append({"path": path, "seconds": seconds, "usable": True})
        except VoiceSampleError:
            entries.append({"path": path, "seconds": 0.0, "usable": False})
    duration = round(sum(entry["seconds"] for entry in entries), 3)
    return {
        "total_seconds": duration,
        "usable_clips": sum(entry["usable"] for entry in entries),
        "rejected_clips": sum(not entry["usable"] for entry in entries),
        "ready_to_prepare": duration >= MIN_TRAIN_SECONDS and not any(not entry["usable"] for entry in entries),
        "entries": entries,
        "trained": False,
    }


def prepare_training_set(root=None, destination=None, *, consent=False):
    """Stage a single-speaker dataset without modifying original recordings."""
    if consent is not True:
        raise VoiceSampleError("Explicitly authorize use of your own voice samples for model training.")
    info = inspect_samples(root)
    if not info["ready_to_prepare"]:
        raise VoiceSampleError(
            "Collect at least ten minutes of valid, consented vocal recordings "
            "before preparing a voice-model training set."
        )
    parent = Path(destination) if destination else (Path(root) if root else HOME) / "Training Sets"
    if parent.is_symlink():
        raise VoiceSampleError("Training set destination cannot be a symlink.")
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if parent.is_symlink():
        raise VoiceSampleError("Training set destination cannot be a symlink.")
    os.chmod(parent, 0o700)
    folder = Path(tempfile.mkdtemp(prefix="dataset-", dir=parent))
    os.chmod(folder, 0o700)
    training_audio = folder / "audio"
    training_audio.mkdir(mode=0o700)
    manifest = {"schema": 1, "owner_consent": True,
                "speaker": "owner", "seconds": info["total_seconds"], "training_started": False,
                "trained_model_created": False, "samples": []}
    try:
        for index, entry in enumerate(info["entries"], 1):
            src = entry["path"]
            if not src.is_file() or src.is_symlink():
                raise VoiceSampleError("Recording changed during dataset preparation.")
            target = training_audio / f"clip-{index:04d}{src.suffix.lower()}"
            digest = hashlib.sha256()
            with src.open("rb") as inp, target.open("xb") as out:
                os.chmod(target, 0o600)
                for chunk in iter(lambda: inp.read(1024 * 1024), b""):
                    digest.update(chunk)
                    out.write(chunk)
            if duration_seconds(target) != entry["seconds"]:
                raise VoiceSampleError("Recording changed during dataset copy.")
            manifest["samples"].append({
                "file": "audio/" + target.name,
                "duration_seconds": entry["seconds"],
                "sha256": digest.hexdigest(),
            })
        path = folder / "manifest.json"
        with path.open("x", encoding="utf-8") as out:
            os.chmod(path, 0o600)
            json.dump(manifest, out, indent=2)
    except BaseException:
        shutil.rmtree(folder)
        raise
    return folder
