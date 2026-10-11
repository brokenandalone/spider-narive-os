"""Non-destructive local drafts for Study's Webbie Homework assistant.

Only saves into the current course's Drafts directory. No cloud operations.
Snapshots always create new files; neither AI revisions nor saves overwrite
an earlier draft. A read operation is explicitly initiated by the user.
"""
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import secrets


def drafts_folder(course_folder):
    folder = Path(course_folder) / "Assignments" / "Drafts"
    if folder.is_symlink():
        raise ValueError("Drafts directory cannot be a symbolic link.")
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    return folder


def label_part(title):
    safe = re.sub(r"[^A-Za-z0-9]+", "-", str(title).strip()).strip("-")
    return safe[:64] or "homework"


def save_snapshot(course_folder, assignment, content):
    text = str(content)
    if not text.strip():
        raise ValueError("There is no draft text to save.")
    if len(text) > 500000:
        raise ValueError("The draft exceeds the local snapshot limit.")
    folder = drafts_folder(course_folder)
    moment = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = folder / (label_part(assignment) + "-" + moment + "-" +
                     secrets.token_hex(4) + ".txt")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return path


def read_snapshot(path, course_folder):
    """Never read outside the selected course's Drafts directory."""
    folder = drafts_folder(course_folder).resolve()
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.suffix.lower() != ".txt":
        raise ValueError("Select a saved Study draft text file.")
    if path.resolve().parent != folder:
        raise ValueError("The selected draft is outside this course.")
    if path.stat().st_size > 2_000_000:
        raise ValueError("The draft file is too large.")
    return path.read_text(encoding="utf-8")
