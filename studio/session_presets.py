"""Private, non-overwriting mix presets tied to verified Studio session WAV hashes."""
import hashlib
import json
import os
from pathlib import Path
import re
import time
import uuid

try:
    from .multitrack import SessionError
    from .session_mix import mix_plan
except ImportError:
    from multitrack import SessionError
    from session_mix import mix_plan

PRESET_FILE = re.compile(r"^preset-[0-9a-f]{32}\.json$")
MAX_PRESET_BYTES = 64 * 1024


def session_fingerprint(session):
    if not isinstance(session, dict) or session.get("verified") is not True:
        raise SessionError("Verify the saved session before working with presets.")
    detail = {
        "title": session["title"], "tempo": session["tempo_bpm"],
        "tracks": [{"filename": t["filename"], "sha256": t["sha256"]}
                   for t in session["tracks"]],
    }
    return hashlib.sha256(json.dumps(detail, sort_keys=True).encode()).hexdigest()


def _directory(session, *, create=False):
    root = Path(session["directory"])
    folder = root / "mix-presets"
    if root.is_symlink() or folder.is_symlink():
        raise SessionError("Preset folder must not be a symlink.")
    if create:
        folder.mkdir(mode=0o700, exist_ok=True)
        os.chmod(folder, 0o700)
    if folder.exists() and not folder.is_dir():
        raise SessionError("Preset location is not a directory.")
    return folder


def _name(text):
    if not isinstance(text, str) or not 1 <= len(text.strip()) <= 80:
        raise SessionError("Mix preset name must be 1 to 80 characters.")
    text = text.strip()
    if any(ord(char) < 32 or ord(char) == 127 for char in text):
        raise SessionError("Mix preset name cannot contain control characters.")
    return text


def save_preset(session, controls, *, name, include_reference=False):
    """Create a new saved mix state; never rewrite any recording or prior preset."""
    title = _name(name)
    planned = mix_plan(session, controls, include_reference=include_reference)
    normalized = {
        t["filename"]: {key: t[key] for key in
                        ("gain", "pan", "mute", "solo", "delay_ms")}
        for t in planned["settings"]
    }
    entry = {
        "schema": 1, "name": title,
        "session_fingerprint": session_fingerprint(session),
        "created_at": int(time.time()),
        "include_reference": include_reference,
        "controls": normalized, "applies_no_audio_processing": True,
    }
    folder = _directory(session, create=True)
    path = folder / f"preset-{uuid.uuid4().hex}.json"
    with path.open("x", encoding="utf-8") as stream:
        os.chmod(path, 0o600)
        json.dump(entry, stream, indent=2)
    return path


def list_presets(session):
    """Return only valid local preset filenames and human-readable names."""
    session_fingerprint(session)
    folder = _directory(session)
    if not folder.exists():
        return []
    result = []
    for path in sorted(folder.iterdir(), reverse=True):
        if not PRESET_FILE.fullmatch(path.name) or path.is_symlink() or not path.is_file():
            continue
        try:
            if not 0 < path.stat().st_size <= MAX_PRESET_BYTES:
                continue
            with path.open("r", encoding="utf-8") as stream:
                raw = json.load(stream)
            if (not isinstance(raw, dict) or raw.get("schema") != 1
                    or not isinstance(raw.get("name"), str)):
                continue
            result.append((path, _name(raw["name"])))
        except (OSError, ValueError, UnicodeError, SessionError):
            continue
    return result


def load_preset(session, path):
    """Reject stale, external, redirected or tampered preset configuration."""
    expected = session_fingerprint(session)
    folder = _directory(session)
    path = Path(path)
    if (not PRESET_FILE.fullmatch(path.name) or path.parent.resolve() != folder.resolve()
            or path.is_symlink() or not path.is_file()
            or not 0 < path.stat().st_size <= MAX_PRESET_BYTES):
        raise SessionError("Select an existing local Spider Studio mix preset.")
    try:
        with path.open("r", encoding="utf-8") as stream:
            data = json.load(stream)
    except (OSError, ValueError, UnicodeError) as error:
        raise SessionError("Cannot read this mix preset.") from error
    if not isinstance(data, dict) or data.get("schema") != 1:
        raise SessionError("Unsupported mix preset.")
    _name(data.get("name"))
    if data.get("session_fingerprint") != expected:
        raise SessionError("Preset was saved for a different or changed set of WAV tracks.")
    if type(data.get("include_reference")) is not bool:
        raise SessionError("Invalid reference-mix setting in saved preset.")
    if not isinstance(data.get("controls"), dict):
        raise SessionError("Invalid mix preset track settings.")
    plan = mix_plan(session, data["controls"],
                    include_reference=data["include_reference"])
    if set(data["controls"]) != {t["filename"] for t in session["tracks"]}:
        raise SessionError("Mix preset must specify all saved tracks.")
    return {"name": data["name"],
            "include_reference": data["include_reference"],
            "controls": {t["filename"]: {key: t[key] for key in
                         ("gain", "pan", "mute", "solo", "delay_ms")}
                         for t in plan["settings"]}}
