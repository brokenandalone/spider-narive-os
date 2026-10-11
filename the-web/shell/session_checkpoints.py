"""Manual Spider OS session checkpoint; does not restore editor documents.

The saved layout contains only workspace IDs and the active workspace.
Checkpoints never contain application text, screen, clipboard or user files.
"""
import json
import os
from pathlib import Path
import tempfile
from desktop_state import clean_state

LIMIT_BYTES = 16384

def checkpoint_path(home=None):
    base = Path(home) if home is not None else Path(
        os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config')))
    return base / 'spider-os' / 'desktop-checkpoint.json'

def save_checkpoint(path, session, allowed):
    location = Path(path)
    if location.is_symlink() or location.parent.is_symlink():
        raise OSError('Refusing symlinked desktop checkpoint')
    if location.exists() and not location.is_file():
        raise OSError('Desktop checkpoint is not a regular file')
    location.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    safe = clean_state(session, allowed)
    fd, temporary = tempfile.mkstemp(dir=location.parent, prefix='.session-checkpoint-')
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump({'version': 1, 'session': safe}, stream)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, location)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return safe

def read_checkpoint(path, allowed):
    location = Path(path)
    try:
        if (location.is_symlink() or not location.is_file() or
                location.stat().st_size > LIMIT_BYTES):
            return None
        data = json.loads(location.read_text(encoding='utf-8'))
        if not isinstance(data, dict) or data.get('version') != 1:
            return None
        session = data.get('session')
        if not isinstance(session, dict) or not isinstance(session.get('open'), list):
            return None
        return clean_state(session, allowed)
    except (OSError, UnicodeError, TypeError, ValueError):
        return None
