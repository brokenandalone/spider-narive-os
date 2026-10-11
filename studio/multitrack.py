"""Private, non-destructive multitrack WAV handoff for existing Linux DAWs.

This copies REAL WAV tracks supplied by the user. It does not extract guitars
from a full song, synthesize independent singers, or verify stem independence.
All imported tracks are placed at timeline zero; the owner must check sync.
"""
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
import threading
import wave

ROLES = (
    "lead_vocal", "backing_vocal", "rhythm_guitar", "lead_guitar",
    "bass", "drums", "piano_keys", "other_instrument",
    "instrumental_bed", "reference_mix",
)
MAX_TRACKS = 24
MAX_TOTAL_BYTES = 8 * 1024 ** 3
DEFAULT_OUTPUT = Path.home() / "Documents/Spider Studio/Music/Multitrack Sessions"


class SessionError(ValueError):
    pass


def _clean_text(value, name, limit):
    if not isinstance(value, str) or not 0 < len(value.strip()) <= limit:
        raise SessionError(f"{name} must be 1 to {limit} characters.")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise SessionError(f"{name} cannot contain control characters.")
    return value.strip()


def _probe(path):
    source = Path(path).expanduser()
    if source.is_symlink() or source.suffix.lower() != ".wav" or not source.is_file():
        raise SessionError("Only regular, non-symlink WAV files can be imported.")
    original = source.stat()
    if not 44 <= original.st_size <= 2 * 1024 ** 3:
        raise SessionError("A WAV must be nonempty and no larger than 2 GiB.")
    try:
        with wave.open(str(source), "rb") as wav:
            if wav.getcomptype() != "NONE" or wav.getnframes() <= 0:
                raise SessionError("Only nonempty PCM WAV tracks are supported.")
            properties = {
                "sample_rate": wav.getframerate(),
                "channels": wav.getnchannels(),
                "sample_width_bytes": wav.getsampwidth(),
                "frames": wav.getnframes(),
                "duration_seconds": round(wav.getnframes() / wav.getframerate(), 4),
            }
        if (properties["sample_rate"] <= 0 or properties["channels"] not in (1, 2)
                or properties["sample_width_bytes"] not in (1, 2, 3, 4)):
            raise SessionError("Use a regular mono or stereo PCM WAV.")
    except (OSError, EOFError, ZeroDivisionError, wave.Error) as error:
        raise SessionError("This WAV is damaged or unsupported.") from error
    return source.resolve(), original, properties


def export_session(tracks, *, title, tempo_bpm=None, output_root=None, stop=None):
    """Copy 1..24 unique PCM WAVs into a new private, import-ready project folder.

    Each independently supplied file is classified by the owner's chosen role.
    No source is modified and no existing project is overwritten.
    """
    stop = stop if stop is not None else threading.Event()
    if not isinstance(tracks, (list, tuple)) or not 1 <= len(tracks) <= MAX_TRACKS:
        raise SessionError("Choose between 1 and 24 audio tracks.")
    project = _clean_text(title, "Project title", 120)
    if tempo_bpm is not None and (type(tempo_bpm) is not int or not 30 <= tempo_bpm <= 300):
        raise SessionError("Tempo must be unspecified or 30 to 300 BPM.")
    planned, seen, total = [], set(), 0
    for entry in tracks:
        if not isinstance(entry, dict) or entry.get("role") not in ROLES:
            raise SessionError("Choose a supported track role.")
        label = _clean_text(entry.get("label", ""), "Track label", 100)
        source, before, properties = _probe(entry.get("path", ""))
        if source in seen:
            raise SessionError("The same WAV cannot be presented as two independent tracks.")
        seen.add(source)
        total += before.st_size
        if total > MAX_TOTAL_BYTES:
            raise SessionError("The session exceeds the 8 GiB copy limit.")
        planned.append((entry["role"], label, source, before, properties))
    root = Path(output_root).expanduser() if output_root is not None else DEFAULT_OUTPUT
    if root.is_symlink() or (root.exists() and not root.is_dir()):
        raise SessionError("Choose a real, non-symlink session folder.")
    if stop.is_set():
        raise SessionError("Export cancelled before copying.")
    try:
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if shutil.disk_usage(root).free < total + 1024 * 1024:
            raise SessionError("Not enough free disk space to preserve all tracks.")
        destination = Path(tempfile.mkdtemp(prefix="session-", dir=root))
        os.chmod(destination, 0o700)
        output_rows = []
        try:
            for index, (role, label, source, before, properties) in enumerate(planned, 1):
                if stop.is_set():
                    raise SessionError("Session export cancelled; original files preserved.")
                filename = f"{index:02d}-{role}.wav"
                target = destination / filename
                digest = hashlib.sha256()
                flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                fd = os.open(source, flags)
                with os.fdopen(fd, "rb") as input_file:
                    fresh = os.fstat(input_file.fileno())
                    if (not stat.S_ISREG(fresh.st_mode) or fresh.st_ino != before.st_ino
                            or fresh.st_dev != before.st_dev
                            or fresh.st_size != before.st_size
                            or fresh.st_mtime_ns != before.st_mtime_ns):
                        raise SessionError("A source recording changed during session preparation.")
                    with target.open("xb") as output_file:
                        os.chmod(target, 0o600)
                        while True:
                            if stop.is_set():
                                raise SessionError("Session export cancelled; originals preserved.")
                            chunk = input_file.read(1024 * 1024)
                            if not chunk:
                                break
                            output_file.write(chunk)
                            digest.update(chunk)
                    after = os.fstat(input_file.fileno())
                    if (fresh.st_size != after.st_size
                            or fresh.st_mtime_ns != after.st_mtime_ns):
                        raise SessionError("A source WAV changed during export; discard the copy.")
                output_rows.append({
                    "filename": filename, "role": role, "label": label,
                    "start_seconds": 0.0, "sha256": digest.hexdigest(),
                    "source_path": str(source), **properties,
                })
            manifest = {
                "schema": 1, "project_title": project, "tempo_bpm": tempo_bpm,
                "timeline_alignment": "all_files_start_at_zero_no_sync_verified",
                "source_tracks_preserved": True,
                "independence_verified": False,
                "reference_mix_is_not_isolated_stems": True,
                "tracks": output_rows,
            }
            with (destination / "session.json").open("x", encoding="utf-8") as stream:
                os.chmod(destination / "session.json", 0o600)
                json.dump(manifest, stream, indent=2)
            with (destination / "tracks.csv").open("x", newline="", encoding="utf-8") as stream:
                os.chmod(destination / "tracks.csv", 0o600)
                writer = csv.DictWriter(stream, fieldnames=[
                    "filename", "role", "label", "start_seconds", "sample_rate",
                    "channels", "duration_seconds", "sha256",
                ], extrasaction="ignore")
                writer.writeheader()
                writer.writerows(output_rows)
            instructions = (
                f"SPIDER STUDIO MULTITRACK SESSION: {project}\n\n"
                "In Ardour, Qtractor, Audacity or another DAW, create an empty project.\n"
                "Import the WAV files as separate tracks, all starting at time zero.\n"
                "Do not stretch, automatically align, or re-time parts without listening.\n"
                "The listed roles are your own labels, not verified AI-generated stems.\n"
                "A reference_mix WAV remains one composite song, not isolated guitars.\n"
                "Original source recordings have NOT been changed or deleted.\n"
                "Check timing, bleed, licenses, clipping and singer consent before release.\n"
                "session.json and tracks.csv contain original local file paths: keep private.\n"
            )
            (destination / "README.txt").write_text(instructions, encoding="utf-8")
            os.chmod(destination / "README.txt", 0o600)
            return destination
        except Exception:
            shutil.rmtree(destination, ignore_errors=True)
            raise
    except OSError as error:
        raise SessionError("Could not prepare the private multitrack session.") from error
