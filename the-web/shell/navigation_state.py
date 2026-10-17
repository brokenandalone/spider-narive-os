"""Private local launcher favorites and history with bounded, atomic storage."""
import json
import os
from pathlib import Path
import re
import tempfile

MAX_FAVORITES = 24
MAX_RECENT = 24
DEFAULT_FAVORITES = ('studio', 'author', 'study', 'webbie', 'forage', 'kali-bay')
VALID_APP_ID = re.compile(r'[A-Za-z0-9_.+@-]{1,160}\Z')


def navigation_file(home=None):
    base = Path(home) if home is not None else Path(
        os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config')))
    return base / 'spider-os' / 'navigation.json'


def _valid(kind, ident, workspaces):
    if not isinstance(kind, str) or not isinstance(ident, str):
        return False
    if kind == 'workspace':
        return ident in workspaces and ident != 'default'
    return kind == 'app' and VALID_APP_ID.fullmatch(ident) is not None


def initial_state(workspaces):
    return {'version': 1,
            'favorites': [['workspace', ident] for ident in DEFAULT_FAVORITES if ident in workspaces],
            'recent': []}


def _sanitize(rows, workspaces, limit):
    result = []
    for row in rows[:256] if isinstance(rows, list) else ():
        if not isinstance(row, (list, tuple)) or len(row) != 2:
            continue
        kind, ident = row
        if _valid(kind, ident, workspaces) and [kind, ident] not in result:
            result.append([kind, ident])
            if len(result) == limit:
                break
    return result


def load_navigation(path, workspaces):
    location = Path(path)
    defaults = initial_state(workspaces)
    try:
        if location.is_symlink() or not location.is_file() or location.stat().st_size > 32768:
            return defaults
        data = json.loads(location.read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            return defaults
        return {'version': 1,
                'favorites': _sanitize(data.get('favorites'), workspaces, MAX_FAVORITES),
                'recent': _sanitize(data.get('recent'), workspaces, MAX_RECENT)}
    except (OSError, UnicodeError, ValueError, TypeError):
        return defaults


def record_recent(state, kind, ident, workspaces):
    if not _valid(kind, ident, workspaces):
        return False
    entry = [kind, ident]
    state['recent'] = [entry] + [item for item in state.get('recent', [])
                                  if item != entry][:MAX_RECENT - 1]
    return True


def toggle_favorite(state, kind, ident, workspaces):
    if not _valid(kind, ident, workspaces):
        return False
    entry = [kind, ident]
    favorites = state.setdefault('favorites', [])
    if entry in favorites:
        favorites.remove(entry)
    else:
        if len(favorites) >= MAX_FAVORITES:
            return False
        favorites.append(entry)
    return True


def save_navigation(path, state, workspaces):
    location = Path(path)
    if location.is_symlink() or location.parent.is_symlink():
        raise OSError('Refusing symlinked launcher settings')
    if location.exists() and not location.is_file():
        raise OSError('Launcher settings must be a regular file')
    location.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    safe = {'version': 1,
            'favorites': _sanitize(state.get('favorites'), workspaces, MAX_FAVORITES),
            'recent': _sanitize(state.get('recent'), workspaces, MAX_RECENT)}
    fd, temporary = tempfile.mkstemp(dir=location.parent, prefix='.navigation-')
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(safe, stream, ensure_ascii=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, location)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
