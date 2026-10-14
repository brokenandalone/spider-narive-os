"""Installed-code drift report and owner-chosen backup overview.

An SHA-256 fingerprint is NOT a signature of trust or an install permission.
No personal file content, package installs, configuration edits or service changes.
"""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
from pathlib import Path

from operations_services import DEFAULT_ROOT, SOURCES, system_status
from operations_wave8_core import json_file

MAX_BACKUPS = 250


def _hash(path):
    try:
        with Path(path).open("rb") as stream:
            h = hashlib.sha256()
            for chunk in iter(lambda: stream.read(131072), b""):
                h.update(chunk)
        return h.hexdigest()
    except (OSError, PermissionError):
        return None


def source_snapshot(root=DEFAULT_ROOT):
    installed = Path(root)
    fingerprints = {}
    for name, relative in SOURCES.items():
        path = installed / relative
        # Do not follow a modified symlink out of the approved install tree.
        fingerprints[name] = (
            _hash(path) if path.is_file() and not path.is_symlink() else None
        )
    data = system_status(installed)
    return {
        "schema": "spider-operations-source-fingerprint-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "read_only",
        "source_sha256": fingerprints,
        "source_present": data["installed_source_presence"],
        "user_services": data["user_services"],
        "disk_free_gib": data["disk_free_gib"],
        "note": "A point-in-time metadata snapshot, not an install receipt, "
                "content backup, signed release or safe-to-upgrade verdict.",
    }


def compare_source_snapshot(previous_json_path, root=DEFAULT_ROOT):
    previous = json_file(previous_json_path)
    if previous.get("schema") != "spider-operations-source-fingerprint-v1":
        raise ValueError("Choose a prior Spider Operations source snapshot JSON.")
    old = previous.get("source_sha256")
    if not isinstance(old, dict) or set(old) != set(SOURCES):
        raise ValueError("Snapshot has incompatible source keys.")
    current = source_snapshot(root)
    differences = {
        name: ("missing_now" if current["source_sha256"][name] is None
               else "missing_before" if old[name] is None else "changed")
        for name in SOURCES if old[name] != current["source_sha256"][name]
    }
    return {
        "workspace": "System",
        "operation": "installed_source_drift",
        "mode": "read_only",
        "source_files_compared": len(SOURCES),
        "changed_source_components": differences,
        "no_changes_detected": not differences,
        "note": "Hash differences can reflect intended upgrades or local edits. "
                "This is not a backup and never authorizes rollback or installation.",
    }


def backup_folder_inventory(folder):
    source = Path(folder).expanduser()
    if source.is_symlink() or not source.is_dir():
        raise ValueError("Choose an existing ordinary backup parent directory.")
    entries = []
    scanned = 0
    for child in source.iterdir():
        scanned += 1
        if scanned > 5000:
            raise ValueError("Backup parent contains too many entries.")
        if child.is_symlink() or not child.is_dir():
            continue
        if not (child.name.startswith("Spider_OS_") and "BACKUP" in child.name.upper()):
            continue
        entries.append(child)
        if len(entries) > MAX_BACKUPS:
            raise ValueError("Too many backup directories for a bounded inventory.")
    return {
        "workspace": "Recovery",
        "mode": "read_only",
        "operation": "backup_inventory",
        "matching_backup_directories": len(entries),
        "note": "Counts names only. No directory contents scanned or verified. "
                "Do not delete or trust a backup solely from this report.",
    }
