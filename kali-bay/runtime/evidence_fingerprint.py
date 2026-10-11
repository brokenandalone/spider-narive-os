#!/usr/bin/env python3
"""Read-only, user-selected file fingerprinting for authorized Kali labs.

No file execution, network requests, automatic uploads or original-file edits.
"""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import stat

MAX_EVIDENCE_BYTES = 256 * 1024 * 1024
CHUNK = 1024 * 1024


class EvidenceError(ValueError):
    pass


def fingerprint(selected_path):
    """SHA-256 only for an explicitly chosen, ordinary file up to 256 MiB."""
    if not isinstance(selected_path, (str, os.PathLike)):
        raise EvidenceError("Select a regular evidence file first.")
    path = Path(selected_path)
    if not path.is_absolute() or path.is_symlink():
        raise EvidenceError("Evidence must be an absolute non-symlink file path.")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(path, flags)
    except OSError as error:
        raise EvidenceError("Could not open the selected evidence file.") from error
    try:
        first = os.fstat(fd)
        if not stat.S_ISREG(first.st_mode):
            raise EvidenceError("Only regular files are accepted.")
        if first.st_size < 0 or first.st_size > MAX_EVIDENCE_BYTES:
            raise EvidenceError("Files larger than 256 MiB are not accepted.")
        digest = hashlib.sha256()
        total = 0
        with os.fdopen(fd, "rb", closefd=False) as stream:
            while True:
                block = stream.read(min(CHUNK, MAX_EVIDENCE_BYTES + 1 - total))
                if not block:
                    break
                total += len(block)
                if total > MAX_EVIDENCE_BYTES:
                    raise EvidenceError("File grew past the 256 MiB limit.")
                digest.update(block)
        last = os.fstat(fd)
        if (
            last.st_dev != first.st_dev
            or last.st_ino != first.st_ino
            or last.st_size != first.st_size
            or last.st_mtime_ns != first.st_mtime_ns
            or total != first.st_size
        ):
            raise EvidenceError("Evidence changed while reading; fingerprint rejected.")
        return {
            "filename": path.name[:180],
            "size_bytes": total,
            "sha256": digest.hexdigest(),
            "checked_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
    except OSError as error:
        raise EvidenceError("Failed to read the evidence file.") from error
    finally:
        os.close(fd)


def note_entry(result):
    """Plain-text note, omitting local filesystem paths by design."""
    if not isinstance(result, dict):
        raise EvidenceError("Evidence metadata is missing.")
    name = result.get("filename")
    size = result.get("size_bytes")
    value = result.get("sha256")
    checked = result.get("checked_utc")
    if not isinstance(name, str) or not 1 <= len(name) <= 180:
        raise EvidenceError("Invalid evidence filename.")
    if any(not c.isprintable() for c in name):
        raise EvidenceError("Invalid characters in evidence filename.")
    if type(size) is not int or not 0 <= size <= MAX_EVIDENCE_BYTES:
        raise EvidenceError("Invalid evidence size.")
    if not isinstance(value, str) or len(value) != 64 or any(
        char not in "0123456789abcdef" for char in value
    ):
        raise EvidenceError("Invalid SHA-256 digest.")
    if not isinstance(checked, str) or not checked.endswith("+00:00"):
        raise EvidenceError("Invalid evidence timestamp.")
    return (
        "\nEVIDENCE FINGERPRINT (locally computed)\n"
        f"Name: {name}\n"
        f"Size: {size} bytes\n"
        f"SHA-256: {value}\n"
        f"Checked (UTC): {checked}\n"
        "Provenance and permission must be documented separately.\n"
    )
