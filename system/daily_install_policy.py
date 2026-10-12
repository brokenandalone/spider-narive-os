#!/usr/bin/env python3
"""Local, fail-closed one-install-per-day lock for the guarded Spider OS batch.

Only the consolidated installer should use this guard. It does not touch user
files, boot, services, models, or any installed application source.
"""
from contextlib import contextmanager
from datetime import datetime
import fcntl
import os
from pathlib import Path
from zoneinfo import ZoneInfo

OWNER_TIMEZONE = ZoneInfo("America/Indiana/Indianapolis")
BACKUP_PREFIX = "spider-batch-"


def local_day(clock=None):
    value = clock() if clock is not None else datetime.now(OWNER_TIMEZONE)
    if value.tzinfo is None:
        raise ValueError("Daily release clock must be timezone aware")
    return value.astimezone(OWNER_TIMEZONE).date()


def existing_batch_receipts(backup_root, day):
    """Count any same-day backup manifest as a used/ambiguous install slot.

    A partially applied attempt can still have created a manifest. Treat it
    conservatively as a potential install until reviewed, not as permission
    to run the whole installer again.
    """
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
        # A crash can leave a *real* same-day batch backup directory before
        # manifest.json is written. That may already contain copied originals
        # or even partially applied source. Never take a second install slot
        # merely because the receipt has not reached the filesystem yet.
        stamped = item.name.startswith(expected)
        if manifest.exists() and not manifest.is_file():
            raise RuntimeError("Malformed batch receipt requires review")
        # A PC with an unusual timezone may have created the batch at a
        # different wall-clock day. Check the backup directory timestamp too.
        observed = manifest if manifest.is_file() else item
        modified_today = datetime.fromtimestamp(
            observed.stat().st_mtime, OWNER_TIMEZONE
        ).date() == day
        if stamped or modified_today:
            items.append(item)
    return sorted(items)


@contextmanager
def daily_install_guard(backup_root, clock=None):
    """Serialize the entire install and deny a second daily batch.

    Rollback is intentionally NOT restricted by this lock.
    No bypass, override, silent cleanup or second-install flag is supplied.
    """
    root = Path(backup_root)
    if root.is_symlink():
        raise RuntimeError("Daily backup root must not be a symlink")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if root.is_symlink():
        raise RuntimeError("Daily backup root changed to a symlink")
    lock_path = root / ".spider-daily-install.lock"
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(lock_path, flags, 0o600)
    try:
        os.fchmod(fd, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
        prior = existing_batch_receipts(root, local_day(clock))
        if prior:
            raise RuntimeError(
                "One Spider OS system installation per local day: a batch "
                "receipt already exists. Do not run another upgrade today. "
                "Use the separate rollback workflow if recovery is necessary."
            )
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)
