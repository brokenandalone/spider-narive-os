"""Private, consent-first voice recording library for Spider Studio.

Samples are **not** trained voice models. Optional ACE-Step reference conditioning
may influence style but cannot promise singer identity or studio pitch correction.
"""
from pathlib import Path
import json
import os
import shutil
import subprocess
import tempfile
import time
import uuid

HOME = Path.home() / "Documents" / "Spider Studio" / "Music" / "My Voice"
ACCEPTED = {".wav", ".mp3", ".flac"}
MAX_SIZE = 64 * 1024 * 1024


class VoiceSampleError(ValueError):
    pass


def _root(root=None):
    path = Path(root) if root is not None else HOME
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink():
        raise VoiceSampleError("Voice folder must not be a symlink.")
    os.chmod(path, 0o700)
    return path


def _file_check(path):
    source = Path(path).expanduser()
    if (not source.is_file() or source.is_symlink()
            or source.suffix.lower() not in ACCEPTED
            or not 0 < source.stat().st_size <= MAX_SIZE):
        raise VoiceSampleError("Choose a regular WAV, MP3 or FLAC file, 64 MiB maximum.")
    return source


def import_sample(path, root=None, *, consent=False):
    if not consent:
        raise VoiceSampleError("Confirm this is your recording or you have permission.")
    source = _file_check(path)
    folder = _root(root)
    target = folder / ("sample-" + uuid.uuid4().hex + source.suffix.lower())
    try:
        with source.open("rb") as src, target.open("xb") as dest:
            os.chmod(target, 0o600)
            shutil.copyfileobj(src, dest)
        _file_check(target)
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return target


def start_capture(root=None, seconds=30):
    """Start explicitly requested microphone capture; does not touch Webbie config."""
    if not isinstance(seconds, int) or not 10 <= seconds <= 60:
        raise VoiceSampleError("Recording duration must be 10–60 seconds.")
    if not shutil.which("arecord"):
        raise VoiceSampleError("ALSA arecord is unavailable; import a recorded vocal instead.")
    folder = _root(root)
    target = folder / ("sample-" + uuid.uuid4().hex + ".wav")
    command = ["arecord", "-q", "-f", "S16_LE", "-r", "44100", "-c", "1",
               "-d", str(seconds), "-t", "wav", str(target)]
    proc = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return proc, target


def finish_capture(proc, path, *, stop=False):
    """Stop if requested; accept only a completed, real recording."""
    if stop and proc.poll() is None:
        proc.send_signal(2)
    try:
        _, stderr = proc.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        Path(path).unlink(missing_ok=True)
        raise VoiceSampleError("Recording did not stop cleanly.")
    if proc.returncode not in (0, 130) or not Path(path).is_file():
        Path(path).unlink(missing_ok=True)
        raise VoiceSampleError("Recording failed. Check microphone permissions or Webbie microphone contention.")
    return _file_check(path)


def samples(root=None):
    folder = _root(root)
    return sorted((p for p in folder.iterdir() if p.name.startswith("sample-")
                   and p.is_file() and not p.is_symlink() and p.suffix.lower() in ACCEPTED),
                  key=lambda p: p.stat().st_mtime, reverse=True)


def training_status(root=None):
    """Honest readiness display; clips alone never establish a trained model."""
    files = samples(root)
    return {"clips": len(files), "trained": False,
            "label": "Recorded clips collected. No learned singing-voice model has been trained."}
