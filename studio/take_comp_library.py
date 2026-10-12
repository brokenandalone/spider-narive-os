"""Reopen and verify locally produced Take Comp Lab WAVs and receipts.

Source paths in receipts are historical only: never follow or open them while
reopening a finished comp. Users may have moved original recordings afterward.
"""
import hashlib
import json
from pathlib import Path
import re
import stat
import threading
import wave

try:
    from .multitrack import ROLES, SessionError
    from .take_comp import NON_PERFORMANCE, MAX_EDITS, MAX_DURATION_MS
except ImportError:
    from multitrack import ROLES, SessionError
    from take_comp import NON_PERFORMANCE, MAX_EDITS, MAX_DURATION_MS

_DIGEST = re.compile(r"^[0-9a-f]{64}$")


def inspect_take_comp(folder, *, stop=None):
    """Validate previous independent track WAV and timeline receipt without edits."""
    stop = stop if stop is not None else threading.Event()
    directory = Path(folder).expanduser()
    if directory.is_symlink() or not directory.is_dir() or not directory.name.startswith("take-"):
        raise SessionError("Choose a real saved Spider Studio Take Comp folder.")
    directory = directory.resolve()
    manifest = directory / "comp.json"
    if (manifest.is_symlink() or not manifest.is_file()
            or not 0 < manifest.stat().st_size <= 128 * 1024):
        raise SessionError("Take Comp receipt is missing or too large.")
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (UnicodeError, OSError, ValueError) as error:
        raise SessionError("Take Comp metadata cannot be opened.") from error
    if not isinstance(data, dict) or data.get("schema") != 1:
        raise SessionError("Unknown Take Comp release format.")
    role = data.get("role")
    if role not in ROLES or role in NON_PERFORMANCE:
        raise SessionError("Saved take has an invalid performance role.")
    if (data.get("output") != role + ".wav"
            or not isinstance(data.get("output_sha256"), str)
            or not _DIGEST.fullmatch(data["output_sha256"])):
        raise SessionError("Saved Take Comp WAV name or checksum is invalid.")
    audio = directory / data["output"]
    if audio.is_symlink() or not audio.is_file():
        raise SessionError("Saved comp is missing or linked.")
    metadata = audio.stat()
    if not stat.S_ISREG(metadata.st_mode) or not 44 <= metadata.st_size <= 2 * 1024 ** 3:
        raise SessionError("Saved comp is empty or too large.")
    fmt = data.get("format")
    if not isinstance(fmt, dict) or set(fmt) != {
        "sample_rate", "channels", "sample_width_bytes",
    }:
        raise SessionError("Saved PCM output format is malformed.")
    try:
        with wave.open(str(audio), "rb") as reader:
            if (reader.getcomptype() != "NONE"
                    or (reader.getframerate(), reader.getnchannels(),
                        reader.getsampwidth()) != (
                            fmt["sample_rate"], fmt["channels"],
                            fmt["sample_width_bytes"])):
                raise SessionError("Saved Take Comp PCM parameters changed.")
            frames = reader.getnframes()
            if frames <= 0 or frames > reader.getframerate() * 600:
                raise SessionError("Saved comp duration exceeds ten minutes.")
    except (wave.Error, OSError, EOFError, ValueError) as error:
        raise SessionError("Cannot decode previously rendered PCM comp.") from error
    edits = data.get("edits")
    if not isinstance(edits, list) or not 1 <= len(edits) <= MAX_EDITS:
        raise SessionError("Saved Take Comp lacks a valid edit decision list.")
    previous_end = 0
    for item in edits:
        if not isinstance(item, dict):
            raise SessionError("Invalid Take Comp edit entry.")
        first = item.get("source_first_frame")
        last = item.get("source_last_frame")
        at = item.get("project_start_frame")
        count = item.get("frames_written")
        if (any(type(x) is not int for x in (first, last, at, count))
                or not 0 <= first < last or last-first != count
                or at < previous_end or at+count > frames):
            raise SessionError("Saved Take Comp has overlapping or inconsistent edit metadata.")
        previous_end = at + count
        source_digest = item.get("source_sha256")
        if not isinstance(source_digest, str) or not _DIGEST.fullmatch(source_digest):
            raise SessionError("Saved comp source checksums are incomplete.")
    if previous_end != frames:
        raise SessionError("Saved comp timeline differs from recorded final frames.")
    digest = hashlib.sha256()
    with audio.open("rb") as stream:
        while True:
            if stop.is_set():
                raise SessionError("Take Comp validation cancelled.")
            block = stream.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    after = audio.stat()
    if (after.st_size != metadata.st_size or
            after.st_mtime_ns != metadata.st_mtime_ns or
            digest.hexdigest() != data["output_sha256"]):
        raise SessionError("Saved comp WAV changed since it was rendered.")
    return {
        "directory": directory, "path": audio, "role": role,
        "sha256": data["output_sha256"], "edits": len(edits),
        "duration_seconds": frames / fmt["sample_rate"],
        "original_recordings_not_accessed": True,
        "genuine_stem_isolation_not_automatically_verified": True,
    }
