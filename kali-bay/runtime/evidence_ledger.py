#!/usr/bin/env python3
"""Private, tamper-evident Kali Bay evidence register.

A SHA-256 hash chain detects inadvertent or deliberate editing of saved
entries. It does NOT prove identity, authenticity, chronology or custody.
Only explicit user actions append events. Never reads evidence file contents,
executes an executable, sends packets or changes the Kali container.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat

import workspace_store as store

MAX_ENTRIES = 180
MAX_LEDGER_BYTES = 145000
MAX_NOTE = 500
KINDS = frozenset(("registered", "reviewed", "transferred", "verified", "note"))
HASH = re.compile(r"^[a-f0-9]{64}$")
GENESIS = "0" * 64


def _identifier(identifier):
    if not isinstance(identifier, str) or not store.PROJECT_ID.fullmatch(identifier):
        raise store.StorageError("Invalid Kali Bay lab identifier.")
    return identifier


def _ledger_path(identifier):
    _identifier(identifier)
    base = store._private_base(False)
    path = base / ("ledger-" + identifier + ".json")
    if path.is_symlink():
        raise store.StorageError("Linked evidence ledger is not allowed.")
    return path


def _lock_path(identifier):
    path = store._private_base(False) / (".ledger-" + _identifier(identifier) + ".lock")
    if path.is_symlink():
        raise store.StorageError("Linked ledger lock is not allowed.")
    return path


def _encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(value):
    return hashlib.sha256(_encoded(value).encode("utf-8")).hexdigest()


def _text(text, label, maximum=MAX_NOTE, required=True):
    if not isinstance(text, str):
        raise store.StorageError(label + " must be text.")
    normalized = text.strip()
    if (required and not normalized) or len(normalized) > maximum:
        raise store.StorageError(label + " is missing or too long.")
    if any(not (char.isprintable() or char in "\n\t") for char in normalized):
        raise store.StorageError(label + " has invalid control characters.")
    return normalized


def _sha(value):
    if not isinstance(value, str) or not HASH.fullmatch(value):
        raise store.StorageError("Evidence SHA-256 must be 64 lowercase hex characters.")
    return value


def _metadata(result):
    if not isinstance(result, dict):
        raise store.StorageError("Fingerprint result required.")
    name = _text(result.get("filename"), "Filename", 180)
    if "\n" in name or "\t" in name:
        raise store.StorageError("Evidence filename must be one line.")
    count = result.get("size_bytes")
    if type(count) is not int or not (0 <= count <= 256 * 1024 * 1024):
        raise store.StorageError("Invalid fingerprint size.")
    checked = _text(result.get("checked_utc"), "Fingerprint timestamp", 45)
    if not checked.endswith("+00:00"):
        raise store.StorageError("Fingerprint timestamp must be in UTC.")
    return {
        "name": name,
        "size_bytes": count,
        "sha256": _sha(result.get("sha256")),
        "checked_utc": checked,
    }


def _validate_chain(data, identifier):
    if not isinstance(data, dict) or data.get("version") != 1:
        raise store.StorageError("Evidence ledger version is invalid.")
    if data.get("lab_id") != identifier:
        raise store.StorageError("Evidence ledger is associated with another lab.")
    rows = data.get("events")
    if not isinstance(rows, list) or len(rows) > MAX_ENTRIES:
        raise store.StorageError("Evidence ledger entry count is invalid.")
    previous = GENESIS
    expected_sequence = 1
    for event in rows:
        if not isinstance(event, dict):
            raise store.StorageError("Evidence ledger contains a malformed event.")
        if set(event) != {
            "number", "time_utc", "kind", "fingerprint",
            "name", "size_bytes", "checked_utc", "note",
            "previous_hash", "entry_hash",
        }:
            raise store.StorageError("Evidence ledger event fields differ.")
        if type(event["number"]) is not int or event["number"] != expected_sequence:
            raise store.StorageError("Evidence ledger event ordering changed.")
        if not isinstance(event["kind"], str) or event["kind"] not in KINDS:
            raise store.StorageError("Unknown evidence ledger action.")
        _sha(event["fingerprint"])
        checked_name = _text(event["name"], "Evidence name", 180)
        if "\n" in checked_name or "\t" in checked_name:
            raise store.StorageError("Evidence name must be one line.")
        if (type(event["size_bytes"]) is not int or
                not 0 <= event["size_bytes"] <= 256 * 1024 * 1024):
            raise store.StorageError("Evidence size is invalid.")
        checked_time = _text(event["checked_utc"], "Timestamp", 45)
        event_time = _text(event["time_utc"], "Timestamp", 45)
        if not checked_time.endswith("+00:00") or not event_time.endswith("+00:00"):
            raise store.StorageError("Ledger timestamps must be UTC.")
        _text(event["note"], "Ledger entry note", MAX_NOTE)
        if event["previous_hash"] != previous:
            raise store.StorageError("Evidence ledger chain has been altered.")
        stored_hash = _sha(event["entry_hash"])
        if _digest({key: val for key, val in event.items()
                    if key != "entry_hash"}) != stored_hash:
            raise store.StorageError("Evidence ledger hash mismatch.")
        previous = stored_hash
        expected_sequence += 1
    return data


def read_ledger(identifier):
    path = _ledger_path(identifier)
    if not path.exists():
        return {"version": 1, "lab_id": identifier, "events": []}
    if not path.is_file():
        raise store.StorageError("Evidence ledger is not a regular file.")
    if path.stat().st_size > MAX_LEDGER_BYTES:
        raise store.StorageError("Evidence ledger exceeds size limit.")
    return _validate_chain(store._read_json(path), identifier)


@contextmanager
def _exclusive(identifier):
    """Separate lock file is stable across atomic ledger replacements."""
    store._private_base(True)
    path = _lock_path(identifier)
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    fd = None
    try:
        fd = os.open(path, flags, 0o600)
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise store.StorageError("Unsafe ledger lock owner or file type.")
        if info.st_mode & 0o077:
            raise store.StorageError("Ledger lock permissions are too broad.")
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    except OSError as error:
        raise store.StorageError("Could not lock private Kali evidence ledger.") from error
    finally:
        if fd is not None:
            os.close(fd)


def append_event(identifier, kind, fingerprint, note):
    """Append one explicitly requested event to the owner's existing lab."""
    _identifier(identifier)
    store.get_lab(identifier)
    if kind not in KINDS:
        raise store.StorageError("Unsupported evidence event type.")
    message = _text(note, "Evidence note")
    meta = _metadata(fingerprint)
    with _exclusive(identifier):
        ledger = read_ledger(identifier)
        entries = ledger["events"]
        if len(entries) >= MAX_ENTRIES:
            raise store.StorageError("Evidence ledger has reached its event limit.")
        prior = entries[-1]["entry_hash"] if entries else GENESIS
        event = {
            "number": len(entries) + 1,
            "time_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "kind": kind,
            "fingerprint": meta["sha256"],
            "name": meta["name"],
            "size_bytes": meta["size_bytes"],
            "checked_utc": meta["checked_utc"],
            "note": message,
            "previous_hash": prior,
        }
        event["entry_hash"] = _digest(event)
        updated = {
            "version": 1, "lab_id": identifier, "events": entries + [event]
        }
        if len(_encoded(updated)) > MAX_LEDGER_BYTES:
            raise store.StorageError("Evidence ledger is full.")
        store._atomic_save(_ledger_path(identifier), updated)
        return dict(event)


def verify_ledger(identifier):
    ledger = read_ledger(identifier)
    return {
        "lab_id": identifier,
        "count": len(ledger["events"]),
        "head": ledger["events"][-1]["entry_hash"]
        if ledger["events"] else GENESIS,
        "verified": True,
    }


def ledger_summary(identifier):
    """Text-only preview without file paths or evidence contents."""
    ledger = read_ledger(identifier)
    verified = verify_ledger(identifier)
    lines = [
        f"Chain integrity: VALID against local saved records ({verified['count']} events)",
        f"Latest chain hash: {verified['head']}",
        "Caution: local hash integrity does not establish authenticity or custody.",
    ]
    for event in ledger["events"][-30:]:
        lines.append(
            f"#{event['number']} {event['time_utc']} "
            f"{event['kind'].upper()} {event['name']} "
            f"SHA-256 {event['fingerprint'][:16]}… : {event['note'][:100]}"
        )
    return "\n".join(lines)
