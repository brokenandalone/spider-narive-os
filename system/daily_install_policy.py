#!/usr/bin/env python3
"""Local one-install-per-day guard for the existing Spider OS batch installer.

Reconciled from the owner's installed policy. It only limits a NEW apply;
never limits preflight, backups inspection, or rollback. No daemon is added.
"""
from contextlib import contextmanager
from datetime import datetime
import fcntl
import os
from pathlib import Path

BACKUP_PREFIX = "spider-batch-"


def local_day(clock=None):
    value = clock() if clock is not None else datetime.now().astimezone()
    if value.tzinfo is None:
        raise ValueError("Daily release clock must be timezone aware")
    # The actual installed PC's local zone determines its single upgrade day.
    local_tz = datetime.now().astimezone().tzinfo
    return value.astimezone(local_tz).date()


def existing_batch_receipts(backup_root, day):
    """Treat any same-day or ambiguously current batch as a spent slot."""
    root = Path(backup_root)
    if root.is_symlink():
        raise RuntimeError("Daily backup directory cannot be a symlink")
    if not root.exists():
        return []
    if not root.is_dir():
        raise RuntimeError("Daily backup path is not a directory")
    items = []
    expected = BACKUP_PREFIX + day.strftime("%Y%m%d") + "-"
    for item in root.iterdir():
        if item.is_symlink():
            if item.name.startswith(BACKUP_PREFIX):
                raise RuntimeError("Untrusted batch receipt link requires owner review")
            continue
        if not item.is_dir() or not item.name.startswith(BACKUP_PREFIX):
            continue
        manifest = item / "manifest.json"
        if manifest.is_symlink():
            raise RuntimeError("Untrusted installation receipt")
        stamped = item.name.startswith(expected)
        if manifest.exists() and not manifest.is_file():
            raise RuntimeError("Malformed batch receipt requires review")
        observed = manifest if manifest.is_file() else item
        modified_today = datetime.fromtimestamp(
            observed.stat().st_mtime
        ).astimezone().date() == day
        if stamped or modified_today:
            items.append(item)
    return sorted(items)


@contextmanager
def daily_install_guard(backup_root, clock=None):
    """Serialize every new apply, and never permit a same-day second attempt."""
    root = Path(backup_root)
    if root.is_symlink():
        raise RuntimeError("Daily backup root must not be a symlink")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if root.is_symlink():
        raise RuntimeError("Daily backup root changed to a symlink")
    lock_path = root / ".spider-daily-install.lock"
    fd = os.open(
        lock_path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        os.fchmod(fd, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
        prior = existing_batch_receipts(root, local_day(clock))
        if prior:
            raise RuntimeError(
                "One Spider OS system installation per local day: a batch "
                "receipt already exists. Review it before a later upgrade. "
                "Rollback is still available."
            )
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)
