"""Local preview-quality audit for owner-consented voice library.

Checks the FIRST 12 SECONDS of each recording, not full songs or identity.
No training, remote service, microphone access, or destructive processing.
"""
from array import array
import hashlib
import math
from pathlib import Path
import shutil
import subprocess
import sys
import threading

try:
    from .voice_profile import samples, VoiceSampleError
    from .voice_dataset import duration_seconds, MIN_TRAIN_SECONDS
except ImportError:
    from voice_profile import samples, VoiceSampleError
    from voice_dataset import duration_seconds, MIN_TRAIN_SECONDS

RATE = 16000
PREVIEW_SECONDS = 12
MAX_FILES = 256
MAX_TOTAL_BYTES = 2 * 1024 ** 3


def _sha256(source, stop):
    checksum = hashlib.sha256()
    with source.open("rb") as stream:
        while True:
            if stop.is_set():
                raise VoiceSampleError("My Voice quality audit cancelled.")
            block = stream.read(1024 * 1024)
            if not block:
                break
            checksum.update(block)
    return checksum.hexdigest()


def _decoded_preview(path, stop):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise VoiceSampleError("Local FFmpeg is needed for sampled My Voice quality checks.")
    if stop.is_set():
        raise VoiceSampleError("My Voice quality audit cancelled.")
    command = [ffmpeg, "-hide_banner", "-nostdin", "-loglevel", "error",
               "-i", str(path), "-t", str(PREVIEW_SECONDS), "-vn",
               "-ac", "1", "-ar", str(RATE), "-f", "s16le", "pipe:1"]
    try:
        finished = subprocess.run(command, capture_output=True, timeout=25)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise VoiceSampleError("The local voice preview could not be decoded.") from error
    if finished.returncode or not 0 < len(finished.stdout) <= RATE * PREVIEW_SECONDS * 2:
        raise VoiceSampleError("The recording has no decodable audio in the preview.")
    if len(finished.stdout) % 2:
        raise VoiceSampleError("Decoded preview has invalid sample alignment.")
    if stop.is_set():
        raise VoiceSampleError("My Voice quality audit cancelled.")
    return finished.stdout


def _measure(raw):
    data = array("h")
    data.frombytes(raw)
    if sys.byteorder != "little":
        data.byteswap()
    count = len(data)
    if not count:
        raise VoiceSampleError("Voice preview has no usable samples.")
    sum_samples = 0
    sum_squares = 0
    peak = 0
    clipped = 0
    for sample in data:
        sum_samples += sample
        sum_squares += sample * sample
        amp = abs(sample)
        peak = max(peak, amp)
        if amp >= 32500:
            clipped += 1
    rms = math.sqrt(sum_squares / count) / 32768
    peak_fraction = peak / 32768
    return {
        "preview_seconds": round(count / RATE, 3),
        "rms_dbfs": round(20 * math.log10(max(rms, 1e-12)), 2),
        "peak_dbfs": round(20 * math.log10(max(peak_fraction, 1e-12)), 2),
        "near_full_scale_fraction": round(clipped / count, 5),
        "dc_offset": round(sum_samples / count / 32768, 5),
    }


def audit_voice_library(root=None, *, stop=None):
    """Provide candid quality flags; owner must still listen and approve samples."""
    stop = stop if stop is not None else threading.Event()
    library = samples(root)
    if len(library) > MAX_FILES:
        raise VoiceSampleError("Audit at most 256 My Voice recordings per library.")
    if sum(p.stat().st_size for p in library) > MAX_TOTAL_BYTES:
        raise VoiceSampleError("My Voice audit exceeds the 2 GiB library limit.")
    report, seen, unique_seconds = [], set(), 0.0
    for path in library:
        if stop.is_set():
            raise VoiceSampleError("My Voice quality audit cancelled.")
        if path.is_symlink() or not path.is_file():
            raise VoiceSampleError("A voice recording changed during inspection.")
        notes = []
        seconds, measures = 0.0, None
        fingerprint = _sha256(path, stop)
        duplicate = fingerprint in seen
        seen.add(fingerprint)
        if duplicate:
            notes.append("Duplicate content of another recording; exclude from training.")
        try:
            seconds = duration_seconds(path)
            measures = _measure(_decoded_preview(path, stop))
        except VoiceSampleError as error:
            if stop.is_set():
                raise
            notes.append("Cannot preview or measure this recording; review or replace.")
        if measures is not None:
            if measures["rms_dbfs"] < -45:
                notes.append("Very quiet sampled audio; possible silence or low mic gain.")
            if measures["near_full_scale_fraction"] > 0.002:
                notes.append("Repeated near-full-scale samples; possible clipping.")
            if abs(measures["dc_offset"]) > 0.05:
                notes.append("DC offset found in sampled recording.")
        if seconds and seconds < 5:
            notes.append("Clip is shorter than five seconds.")
        accepted = bool(measures and seconds >= 5 and not duplicate
                        and measures["rms_dbfs"] >= -45
                        and measures["near_full_scale_fraction"] <= 0.002)
        if accepted:
            unique_seconds += seconds
        report.append({
            "filename": path.name, "sha256": fingerprint, "seconds": seconds,
            "accepted_for_preview_count": accepted, "duplicate": duplicate,
            "sampled_quality": measures, "warnings": notes,
        })
    return {
        "schema": 1, "full_audio_scanned": False,
        "sampling": "first 12 seconds of each file decoded locally to 16kHz mono",
        "total_recordings": len(report),
        "unique_preview_accepted_seconds": round(unique_seconds, 3),
        "minimum_reference_seconds": MIN_TRAIN_SECONDS,
        "potentially_sufficient_for_preparation": unique_seconds >= MIN_TRAIN_SECONDS,
        "clip_review_required": True,
        "training_started": False, "trained_model_verified": False,
        "files": report,
    }
