"""Private, revisioned Spider Studio mix projects and safe local render history.

Project files are settings/paths, not copies of audio. No cloud, AI or daemon.
"""
import json
import math
import os
from pathlib import Path
import tempfile
import time

if __package__:
    from .band_mix import ROLES, DEFAULT_OUTPUT
    from .song_mix import MixError, valid_wav
else:
    from band_mix import ROLES, DEFAULT_OUTPUT
    from song_mix import MixError, valid_wav

PROJECTS_ROOT = Path.home() / 'Documents/Spider Studio/Music/Band Projects'
MAX_JSON_BYTES = 64 * 1024
MAX_LIST = 100


def _root(folder):
    root = Path(folder).expanduser()
    if root.is_symlink():
        raise MixError('Project library cannot be a symlink.')
    return root


def _json_data(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_JSON_BYTES:
        raise MixError('Project or receipt is unavailable or unsafe to read.')
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise MixError('Project JSON is damaged or unsupported.') from exc
    if not isinstance(data, dict):
        raise MixError('Project JSON must contain a mapping.')
    return data


def validate_project(title, tracks):
    if (not isinstance(title, str) or not 1 <= len(title.strip()) <= 120
            or any(ord(ch) < 32 or ord(ch) == 127 for ch in title)):
        raise MixError('Project title must contain 1 to 120 printable characters.')
    if not isinstance(tracks, dict) or set(tracks) - set(ROLES):
        raise MixError('Only Spider Studio band roles can be saved.')
    clean = {}
    identities = set()
    for role in ROLES:
        if role not in tracks:
            continue
        item = tracks[role]
        if not isinstance(item, dict):
            raise MixError('Every track must contain named mixer controls.')
        if set(item) - {'path', 'gain', 'pan', 'muted', 'solo', 'offset_ms'}:
            raise MixError('Unknown mixer setting in saved project.')
        path = item.get('path', '')
        if not isinstance(path, str) or not path.strip() or len(path) > 4096:
            raise MixError('Each saved track needs an audio file path.')
        source = Path(path).expanduser()
        if not source.is_absolute() or source.suffix.lower() != '.wav' or source.is_symlink():
            raise MixError('Project audio must use regular absolute WAV paths.')
        # Saving does not copy any audio; a moved stem can be reselected after opening.
        if source.exists():
            source = valid_wav(source, role)
            identity = (source.stat().st_dev, source.stat().st_ino)
            if identity in identities:
                raise MixError('The same WAV cannot be assigned to two tracks.')
            identities.add(identity)
        gain, pan = item.get('gain', 1.0), item.get('pan', 0.0)
        muted, solo = item.get('muted', False), item.get('solo', False)
        offset = item.get('offset_ms', 0)
        if any(isinstance(val, bool) or not isinstance(val, (int, float))
               or not math.isfinite(val) for val in (gain, pan)):
            raise MixError('Levels and pans must be finite numbers.')
        if not 0 <= gain <= 2 or not -1 <= pan <= 1:
            raise MixError('Project level or pan is out of range.')
        if not isinstance(muted, bool) or not isinstance(solo, bool):
            raise MixError('Mute and solo settings must be true or false.')
        if isinstance(offset, bool) or not isinstance(offset, int) or not 0 <= offset <= 60000:
            raise MixError('Track offset must be 0 to 60000 milliseconds.')
        clean[role] = {
            'path': str(source), 'gain': float(gain), 'pan': float(pan),
            'muted': muted, 'solo': solo, 'offset_ms': offset,
        }
    return {'schema': 1, 'title': title.strip(), 'tracks': clean}


def save_project(title, tracks, *, root=None):
    """Save a new version into a private folder, never rewriting the previous revision."""
    data = validate_project(title, tracks)
    parent = _root(root if root is not None else PROJECTS_ROOT)
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(parent, 0o700)
    folder = Path(tempfile.mkdtemp(prefix='project-', dir=parent))
    os.chmod(folder, 0o700)
    path = folder / 'project.json'
    data['created_at_unix'] = int(time.time())
    try:
        with path.open('x', encoding='utf-8') as file:
            os.chmod(path, 0o600)
            json.dump(data, file, indent=2, allow_nan=False)
    except (OSError, ValueError):
        path.unlink(missing_ok=True)
        folder.rmdir()
        raise
    return path


def load_project(path, *, root=None):
    parent = _root(root if root is not None else PROJECTS_ROOT)
    file = Path(path).expanduser()
    if (file.name != 'project.json' or file.is_symlink()
            or file.parent.is_symlink() or not file.parent.name.startswith('project-')
            or file.parent.parent.resolve() != parent.resolve()):
        raise MixError('Only private saved Studio mix projects may be opened.')
    raw = _json_data(file)
    if raw.get('schema') != 1 or not isinstance(raw.get('tracks'), dict):
        raise MixError('Unsupported project revision format.')
    clean = validate_project(raw.get('title'), raw['tracks'])
    clean['path'] = str(file)
    clean['missing_sources'] = [
        role for role, item in clean['tracks'].items()
        if not Path(item['path']).is_file()
    ]
    return clean


def list_projects(*, root=None, limit=MAX_LIST):
    parent = _root(root if root is not None else PROJECTS_ROOT)
    if not parent.is_dir():
        return []
    items = []
    for folder in sorted(parent.glob('project-*'), reverse=True):
        if folder.is_symlink() or not folder.is_dir():
            continue
        file = folder / 'project.json'
        try:
            data = load_project(file, root=parent)
            items.append(data)
        except (MixError, OSError, ValueError):
            continue
        if len(items) >= min(max(limit, 1), MAX_LIST):
            break
    return items


def recent_mixes(*, root=None, limit=30):
    """Inspect only known local mix outputs, not arbitrary WAVs or remote URLs."""
    parent = _root(root if root is not None else DEFAULT_OUTPUT)
    if not parent.is_dir():
        return []
    results = []
    for folder in sorted(parent.glob('band-*'), reverse=True):
        if folder.is_symlink() or not folder.is_dir():
            continue
        receipt = folder / 'band-mix.json'
        audio = folder / 'band-mix.wav'
        try:
            data = _json_data(receipt)
            if (data.get('schema') != 1 or data.get('render') != audio.name
                    or not isinstance(data.get('independent_tracks'), list)):
                continue
            valid_wav(audio, 'saved band mix')
            results.append({
                'file': str(audio), 'created_at_unix': data.get('created_at_unix', 0),
                'track_count': len(data['independent_tracks']),
            })
        except (MixError, OSError, ValueError):
            continue
        if len(results) >= min(max(limit, 1), MAX_LIST):
            break
    return results
