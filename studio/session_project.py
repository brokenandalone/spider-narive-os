"""Read-only validation of saved Spider Studio multitrack sessions.

The original export format (schema 1) stays compatible. Imported manifests
never authorize arbitrary filesystem paths: only expected local PCM WAV names
inside the chosen session directory are read. The original source_path is
informational and is never opened.
"""
import hashlib
import json
from pathlib import Path
import re
import stat
import wave

try:
    from .multitrack import MAX_TRACKS, MAX_TOTAL_BYTES, ROLES, SessionError
except ImportError:
    from multitrack import MAX_TRACKS, MAX_TOTAL_BYTES, ROLES, SessionError

SHA256 = re.compile(r"^[a-f0-9]{64}$")
MAX_MANIFEST_BYTES = 256 * 1024


def inspect_session(folder, *, stop=None):
    """Verify hashes, metadata, and local-file confinement before mixing."""
    directory = Path(folder).expanduser()
    if directory.is_symlink() or not directory.is_dir():
        raise SessionError("Select a real Spider Studio session folder.")
    directory = directory.resolve()
    manifest_path = directory / "session.json"
    if (manifest_path.is_symlink() or not manifest_path.is_file()
            or not 0 < manifest_path.stat().st_size <= MAX_MANIFEST_BYTES):
        raise SessionError("The session manifest is missing or invalid.")
    try:
        with manifest_path.open("r", encoding="utf-8") as stream:
            manifest = json.load(stream)
    except (OSError, ValueError, UnicodeError) as error:
        raise SessionError("The session manifest cannot be read.") from error
    if not isinstance(manifest, dict) or manifest.get("schema") != 1:
        raise SessionError("Unsupported or damaged Spider Studio session version.")
    title = manifest.get("project_title")
    if not isinstance(title, str) or not title.strip() or len(title) > 120:
        raise SessionError("The session title is invalid.")
    bpm = manifest.get("tempo_bpm")
    if bpm is not None and (type(bpm) is not int or not 30 <= bpm <= 300):
        raise SessionError("Invalid session tempo.")
    entries = manifest.get("tracks")
    if not isinstance(entries, list) or not 1 <= len(entries) <= MAX_TRACKS:
        raise SessionError("A saved session must contain 1 to 24 tracks.")

    restored = []
    identities = set()
    total = 0
    for number, entry in enumerate(entries, 1):
        if stop is not None and stop.is_set():
            raise SessionError("Session verification cancelled.")
        if not isinstance(entry, dict):
            raise SessionError("Invalid saved track metadata.")
        role, filename = entry.get("role"), entry.get("filename")
        if role not in ROLES or filename != f"{number:02d}-{role}.wav":
            raise SessionError("Invalid track role, order, or filename in manifest.")
        expected_hash = entry.get("sha256")
        if not isinstance(expected_hash, str) or not SHA256.fullmatch(expected_hash):
            raise SessionError("A track checksum is missing or invalid.")
        label = entry.get("label")
        if not isinstance(label, str) or not label.strip() or len(label) > 100:
            raise SessionError("Invalid saved track label.")
        path = directory / filename
        if path.is_symlink() or not path.is_file():
            raise SessionError(f"Saved track is missing or linked: {filename}")
        metadata = path.stat()
        if (not stat.S_ISREG(metadata.st_mode) or not 44 <= metadata.st_size <= 2 * 1024 ** 3):
            raise SessionError(f"Track size is invalid: {filename}")
        identity = metadata.st_dev, metadata.st_ino
        if identity in identities:
            raise SessionError("Two saved tracks point to the same underlying file.")
        identities.add(identity)
        total += metadata.st_size
        if total > MAX_TOTAL_BYTES:
            raise SessionError("Saved tracks exceed the 8 GiB session limit.")
        try:
            with wave.open(str(path), "rb") as stream:
                if (stream.getcomptype() != "NONE" or stream.getnframes() <= 0
                        or stream.getnchannels() not in (1, 2)
                        or stream.getframerate() <= 0):
                    raise SessionError(f"Invalid PCM WAV track: {filename}")
                rate, channels, frames = (stream.getframerate(),
                                          stream.getnchannels(), stream.getnframes())
        except (wave.Error, EOFError, OSError) as error:
            raise SessionError(f"Cannot inspect WAV track: {filename}") from error
        if (entry.get("sample_rate") != rate or entry.get("channels") != channels
                or entry.get("frames") != frames):
            raise SessionError(f"WAV metadata changed since export: {filename}")
        digest = hashlib.sha256()
        try:
            with path.open("rb") as stream:
                while True:
                    if stop is not None and stop.is_set():
                        raise SessionError("Session verification cancelled.")
                    chunk = stream.read(1024 * 1024)
                    if not chunk:
                        break
                    digest.update(chunk)
        except OSError as error:
            raise SessionError(f"Cannot read saved WAV: {filename}") from error
        after = path.stat()
        if (after.st_size != metadata.st_size
                or after.st_mtime_ns != metadata.st_mtime_ns
                or digest.hexdigest() != expected_hash):
            raise SessionError(f"Track has changed or failed checksum: {filename}")
        restored.append({
            "filename": filename, "path": path, "role": role, "label": label,
            "sha256": expected_hash, "sample_rate": rate, "channels": channels,
            "frames": frames, "duration_seconds": frames / rate,
        })
    return {"directory": directory, "title": title.strip(),
            "tempo_bpm": bpm, "tracks": restored, "verified": True,
            "sample_rates": sorted({t["sample_rate"] for t in restored})}
