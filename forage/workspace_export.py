"""User-approved research report handoff. Never modify Study/Author project files."""
import os
from pathlib import Path


def export_report(report_path, workspace, directory, *, research_root):
    """Copy a completed Markdown report into a user-selected folder, exclusively.

    This is a copy, NOT an assignment submission, manuscript edit, or ingestion
    into a private project. The user explicitly chooses the destination.
    """
    if workspace not in {"study", "author"}:
        raise ValueError("Choose either Study or Author")
    source = Path(report_path).expanduser()
    root = Path(research_root).expanduser().resolve(strict=True)
    if source.is_symlink() or not source.is_file() or source.suffix != ".md":
        raise ValueError("Select a saved Deep Forage Markdown report")
    if source.resolve(strict=True).parent != root:
        raise ValueError("Only Deep Forage saved reports may be exported")
    target_dir = Path(directory).expanduser()
    if not target_dir.is_dir() or target_dir.is_symlink():
        raise ValueError("Select an existing destination directory")
    target = target_dir / (workspace.upper() + "_RESEARCH_" + source.name)
    if target.is_symlink():
        raise ValueError("Destination is a symlink")
    if len(str(target)) > 4096:
        raise ValueError("Destination path too long")
    # Save without overwriting any notes/manuscripts/assignments.
    raw = source.read_bytes()
    if len(raw) > 8 * 1024 * 1024:
        raise ValueError("Research report exceeds export limit")
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb") as dest:
            dest.write(raw)
            dest.flush()
            os.fsync(dest.fileno())
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return str(target)
