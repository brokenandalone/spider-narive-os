"""Small, defensive desktop tab state: bounded reads and atomic replacement."""
import json
import os
from pathlib import Path
import tempfile

MAX_OPEN_TABS = 30
MAX_STATE_BYTES = 16384


def clean_state(data, allowed):
    allowed = set(allowed)
    if not isinstance(data, dict):
        return {'version': 2, 'open': ['default'], 'active': 'default'}
    tabs = ['default']
    incoming = data.get('open', [])
    for item in incoming[:100] if isinstance(incoming, list) else ():
        if isinstance(item, str) and item in allowed and item not in tabs:
            tabs.append(item)
            if len(tabs) >= MAX_OPEN_TABS:
                break
    active = data.get('active', 'default')
    if active not in tabs:
        active = 'default'
    return {'version': 2, 'open': tabs, 'active': active}


def read_desktop_state(path, allowed):
    location = Path(path)
    if location.is_symlink():
        return clean_state({}, allowed)
    try:
        if not location.is_file() or location.stat().st_size > MAX_STATE_BYTES:
            return clean_state({}, allowed)
        raw = json.loads(location.read_text(encoding='utf-8'))
        return clean_state(raw, allowed)
    except (OSError, UnicodeError, ValueError, TypeError):
        return clean_state({}, allowed)


def write_desktop_state(path, data, allowed):
    location = Path(path)
    if location.is_symlink() or location.parent.is_symlink():
        raise OSError('Refusing symlinked desktop session settings')
    if location.exists() and not location.is_file():
        raise OSError('Desktop session settings must be a regular file')
    location.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    safe = clean_state(data, allowed)
    fd, temporary = tempfile.mkstemp(dir=location.parent, prefix='.desktop-')
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(safe, stream)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, location)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
