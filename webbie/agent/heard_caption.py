"""Short-lived, owner-local speech captions for Webbie's floating face.

The speech agent publishes recognized text here. The Qt portrait reads it.
No microphone, model, camera, or desktop notification settings are changed.
"""
import json
import os
from pathlib import Path
import tempfile
import time

DISPLAY_SECONDS = 6
READY_SECONDS = 4
MAX_CHARS = 180


def runtime_dir():
    base = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
    return base / "spider-os"


def caption_path():
    return runtime_dir() / "webbie-heard-caption.json"


def ready_path():
    return runtime_dir() / "webbie-caption-overlay.ready"


def publish_heard(text):
    """Atomically replace the transient caption with a new recognition result."""
    words = " ".join(str(text or "").split())
    if not words:
        return False
    folder = runtime_dir()
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = caption_path()
    payload = {"text": words[:MAX_CHARS], "until": time.time() + DISPLAY_SECONDS}
    fd, temporary = tempfile.mkstemp(prefix=".webbie-caption-", dir=folder)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            json.dump(payload, output, ensure_ascii=False)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return True


def latest_heard(now=None):
    """Return only the current caption; never persist speech transcripts."""
    current = time.time() if now is None else now
    try:
        data = json.loads(caption_path().read_text(encoding="utf-8"))
        until = data.get("until")
        value = data.get("text")
        if (isinstance(until, (int, float)) and
                current <= until <= current + DISPLAY_SECONDS + 1 and
                isinstance(value, str)):
            return value[:MAX_CHARS]
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return ""


def pulse_overlay():
    """Signal that the visible, click-through portrait is alive."""
    folder = runtime_dir()
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = ready_path()
    path.touch(mode=0o600, exist_ok=True)


def overlay_ready(now=None):
    current = time.time() if now is None else now
    try:
        stat = ready_path().stat()
        return stat.st_uid == os.getuid() and 0 <= current - stat.st_mtime <= READY_SECONDS
    except OSError:
        return False
