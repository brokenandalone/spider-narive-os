"""Private-session preference for Webbie. Owner GUI toggles; default OFF.

A private session suppresses reading and writing stored conversation and
long-term memory from the resident chat engine. It does not erase stored
records, the process logs, Ollama internal cache, or protect other apps.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import stat
import tempfile
import threading
import time

DEFAULT_PATH = Path.home() / ".local/state/spider-os/webbie-privacy.json"
_LOCK = threading.RLock()


def private_session_active(path=DEFAULT_PATH):
    target=Path(path)
    try:
        if target.is_symlink():
            return False
        info=target.stat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077 or info.st_size>2048):
            return False
        data=json.loads(target.read_text(encoding="utf-8"))
        return isinstance(data,dict) and data.get("private_session") is True
    except (OSError,ValueError,UnicodeError,TypeError):
        return False


def set_private_session(enabled, *, path=DEFAULT_PATH, clock=None):
    """Explicit owner-click action only. No speech/model adapter."""
    if type(enabled) is not bool:
        raise ValueError("Choose private session on or off")
    target=Path(path)
    parent=target.parent
    with _LOCK:
        if parent.is_symlink():
            raise PermissionError("Unsafe private-session folder")
        parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        info=parent.stat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid()
                or info.st_mode & 0o022 or target.is_symlink()):
            raise PermissionError("Private-session folder must be owned and private")
        data=json.dumps({
            "version":1,"private_session":enabled,
            "updated":float((clock or time.time)()),
        },separators=(",",":")).encode()
        fd,tmp=tempfile.mkstemp(prefix=".webbie-privacy-",dir=parent)
        try:
            os.fchmod(fd,0o600)
            with os.fdopen(fd,"wb") as stream:
                stream.write(data); stream.flush(); os.fsync(stream.fileno())
            os.replace(tmp,target)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)


def privacy_explanation(path=DEFAULT_PATH):
    if private_session_active(path):
        return ("Private session is ON. Webbie will avoid using and storing "
                "recent conversation and long-term memories in her local brain. "
                "This does not erase existing records or external app logs.")
    return ("Private session is OFF. Webbie uses her existing local "
            "conversation and memory behavior. You control the switch.")
