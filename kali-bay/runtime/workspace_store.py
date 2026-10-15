#!/usr/bin/env python3
"""Local-only Kali Bay lab notebooks and explicitly saved favorite tools.

Never executes commands, writes to the Kali container, starts Webbie or
transmits notebook contents. The UI alone decides whether to share text.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import uuid

BASE = Path.home() / ".local" / "share" / "spider-os" / "kali-bay" / "projects"
FAVORITES = "favorites.json"
MAX_PROJECTS = 40
MAX_NOTE_CHARS = 40000
MAX_FAVORITES = 120
PROJECT_ID = re.compile(r"^[a-f0-9]{32}$")
APP_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,100}\.desktop$")
BUILTINS = frozenset({
    "wireshark", "nmap", "burpsuite", "zaproxy", "ghidra",
    "msfconsole", "suricata", "yara", "lynis", "clamtk",
})


class StorageError(ValueError):
    """A local file, size, or conflict check prevented a write."""


def _utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _private_base(create=False):
    """Reject symlinked user-store path components; mkdir only on user writes."""
    home = Path.home()
    try:
        parts = BASE.relative_to(home).parts
    except ValueError as error:
        raise StorageError("Lab store must remain inside the user home.") from error
    current = home
    for component in parts:
        current = current / component
        if current.is_symlink():
            raise StorageError("Refusing a linked Kali Bay storage directory.")
        if current.exists() and not current.is_dir():
            raise StorageError("A Kali Bay storage path is not a directory.")
        if create and not current.exists():
            current.mkdir(mode=0o700)
    return BASE


def _file(name):
    base = _private_base(False)
    if name != FAVORITES and not PROJECT_ID.fullmatch(str(name)):
        raise StorageError("Invalid lab identifier.")
    filename = name if name == FAVORITES else name + ".json"
    path = base / filename
    if path.is_symlink():
        raise StorageError("Refusing a linked Kali Bay storage file.")
    return path


def _read_json(path):
    if not path.is_file() or path.is_symlink():
        raise StorageError("Lab file is missing or invalid.")
    try:
        details = path.stat()
        if not stat.S_ISREG(details.st_mode) or details.st_uid != os.getuid():
            raise StorageError("Lab file does not belong to this user.")
        if details.st_size > 150000:
            raise StorageError("Lab file exceeds the safety limit.")
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise StorageError("Unable to read Kali Bay lab data.") from error


def _atomic_save(path, obj):
    _private_base(True)
    if path.is_symlink():
        raise StorageError("Refusing linked destination.")
    payload = json.dumps(obj, ensure_ascii=True, indent=2, sort_keys=True)
    if len(payload.encode("utf-8")) > 150000:
        raise StorageError("Lab content exceeds the size limit.")
    tmp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=BASE,
            prefix=".kali-bay-", delete=False,
        ) as stream:
            tmp_name = stream.name
            os.fchmod(stream.fileno(), 0o600)
            stream.write(payload + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp_name, path)
    except OSError as error:
        raise StorageError("Kali Bay could not save local lab data.") from error
    finally:
        if tmp_name:
            try:
                os.unlink(tmp_name)
            except FileNotFoundError:
                pass


def _project(obj):
    if not isinstance(obj, dict) or not PROJECT_ID.fullmatch(str(obj.get("id", ""))):
        raise StorageError("Invalid project data.")
    if not isinstance(obj.get("title"), str) or not isinstance(obj.get("notes"), str):
        raise StorageError("Invalid project fields.")
    if len(obj["notes"]) > MAX_NOTE_CHARS or len(obj["title"]) > 72:
        raise StorageError("Project content is too long.")
    if not isinstance(obj.get("revision"), int) or obj["revision"] < 1:
        raise StorageError("Project revision invalid.")
    return obj


def list_labs():
    directory = _private_base(False)
    if not directory.is_dir():
        return []
    found = []
    for path in directory.iterdir():
        if path.is_symlink() or not PROJECT_ID.fullmatch(path.stem) or path.suffix != ".json":
            continue
        try:
            obj = _project(_read_json(path))
            if obj["id"] != path.stem:
                continue
            found.append({
                "id": obj["id"], "title": obj["title"],
                "updated": str(obj.get("updated", "")),
                "revision": obj["revision"],
            })
        except StorageError:
            continue
    return sorted(found, key=lambda p: p["updated"], reverse=True)[:MAX_PROJECTS]


def get_lab(identifier):
    path = _file(identifier)
    obj = _project(_read_json(path))
    if obj["id"] != identifier:
        raise StorageError("Lab identifier mismatch.")
    return dict(obj)


def create_lab(title):
    if not isinstance(title, str):
        raise StorageError("Lab name must be text.")
    name = title.strip()
    if not 1 <= len(name) <= 72 or not all(c.isprintable() for c in name):
        raise StorageError("Lab name must be 1 to 72 printable characters.")
    if len(list_labs()) >= MAX_PROJECTS:
        raise StorageError("Lab notebook limit reached.")
    identifier = uuid.uuid4().hex
    now = _utc()
    obj = {
        "id": identifier, "title": name, "notes": "",
        "created": now, "updated": now, "revision": 1,
    }
    _atomic_save(_file(identifier), obj)
    return dict(obj)


def save_lab(identifier, notes, expected_revision):
    if not isinstance(notes, str) or len(notes) > MAX_NOTE_CHARS:
        raise StorageError("Lab notes must be under 40,000 characters.")
    obj = get_lab(identifier)
    if type(expected_revision) is not int or obj["revision"] != expected_revision:
        raise StorageError("Lab changed elsewhere. Reload before overwriting.")
    obj["notes"] = notes
    obj["updated"] = _utc()
    obj["revision"] += 1
    _atomic_save(_file(identifier), obj)
    return dict(obj)


def _favorite_key(key):
    if not isinstance(key, str) or len(key) > 115:
        raise StorageError("Invalid favorite identifier.")
    if key.startswith("builtin:") and key[8:] in BUILTINS:
        return key
    if key.startswith("app:") and APP_ID.fullmatch(key[4:]):
        return key
    raise StorageError("Favorite must be an approved tool or installed app ID.")


def get_favorites():
    path = _file(FAVORITES)
    if not path.exists():
        return set()
    data = _read_json(path)
    if not isinstance(data, dict) or not isinstance(data.get("favorites"), list):
        raise StorageError("Invalid favorites document.")
    if len(data["favorites"]) > MAX_FAVORITES:
        raise StorageError("Favorites list is too large.")
    values = set()
    for key in data["favorites"]:
        values.add(_favorite_key(key))
    return values


def set_favorite(key, enabled):
    selected = _favorite_key(key)
    if type(enabled) is not bool:
        raise StorageError("Favorite selection must be explicit.")
    values = get_favorites()
    if enabled:
        if len(values) >= MAX_FAVORITES and selected not in values:
            raise StorageError("Favorite limit reached.")
        values.add(selected)
    else:
        values.discard(selected)
    _atomic_save(_file(FAVORITES), {"version": 1, "favorites": sorted(values)})
    return values
