"""Private, versioned songwriting-to-release checkpoints for Spider Studio v10.

This is a workflow ledger of owner-selected WAV paths, not a DAW, AI model,
voice trainer or automatic stem separator. Saving never copies source audio.
"""
import argparse
import json
import os
from pathlib import Path
import re
import tempfile
import time
import uuid

if __package__:
    from .song_mix import valid_wav, MixError
else:
    from song_mix import valid_wav, MixError

ROOT = Path.home() / 'Documents/Spider Studio/Music/Production Sessions'
ROLES = (
    'reference_mix', 'backing', 'lead_vocal', 'guest_vocal',
    'rhythm_guitar', 'lead_guitar', 'bass', 'drums', 'keys', 'final_mix',
)
STEM_ROLES = ROLES[1:-1]
SESSION_RE = re.compile(r'^session-[0-9a-f]{32}$')
REVISION_RE = re.compile(r'^revision-[0-9a-f]{32}\.json$')
MAX_BYTES = 48 * 1024
MAX_SESSIONS = 100


class ProductionError(ValueError):
    pass


def _store(root=None):
    root = Path(root if root is not None else ROOT).expanduser()
    if root.is_symlink():
        raise ProductionError('Production session library cannot be a symlink.')
    return root


def _text(value, label, maximum):
    if not isinstance(value, str) or len(value.strip()) > maximum:
        raise ProductionError(f'{label} must be text of at most {maximum} characters.')
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ProductionError(f'{label} cannot include control characters.')
    return value.strip()


def _path(value, role, *, allow_missing):
    if not isinstance(value, str) or len(value) > 4096 or not value.strip():
        raise ProductionError('Select an existing absolute WAV for ' + role)
    path = Path(value).expanduser()
    if not path.is_absolute() or path.suffix.lower() != '.wav' or path.is_symlink():
        raise ProductionError('Only absolute, non-symlink WAV paths are supported.')
    if path.exists():
        try:
            return str(valid_wav(path, role))
        except (MixError, OSError) as exc:
            raise ProductionError('Invalid WAV for ' + role) from exc
    if not allow_missing:
        raise ProductionError('The WAV was moved or is missing: ' + role)
    return str(path)


def _validate(title, assets, verified, notes, *, allow_missing=False):
    title = _text(title, 'Song title', 120)
    notes = _text(notes, 'Production notes', 2000)
    if not title:
        raise ProductionError('Enter a song title.')
    if (not isinstance(assets, dict) or not isinstance(verified, dict)
            or set(assets) - set(ROLES) or set(verified) - set(STEM_ROLES)):
        raise ProductionError('Unrecognized Studio track roles.')
    selected = {}
    identities = set()
    for role in ROLES:
        if role not in assets:
            continue
        path = _path(assets[role], role, allow_missing=allow_missing)
        if Path(path).is_file():
            ident = (Path(path).stat().st_dev, Path(path).stat().st_ino)
            # Mixing a whole song as an independent guitar or vocal is not allowed.
            if ident in identities:
                raise ProductionError('Do not assign the same recording to multiple roles.')
            identities.add(ident)
        selected[role] = path
    flags = {}
    for role in STEM_ROLES:
        value = verified.get(role, False)
        if type(value) is not bool:
            raise ProductionError('Track review must be checked or unchecked.')
        if value and role not in selected:
            raise ProductionError('An unselected track cannot be marked reviewed.')
        flags[role] = value
    return {'schema': 1, 'title': title, 'notes': notes,
            'assets': selected, 'reviewed_stems': flags}


def create_session(title, *, notes='', root=None):
    store = _store(root)
    store.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(store, 0o700)
    ident = 'session-' + uuid.uuid4().hex
    session = store / ident
    session.mkdir(mode=0o700)
    try:
        save_revision(ident, title, {}, {}, notes=notes, root=store)
    except BaseException:
        session.rmdir()
        raise
    return ident


def _session_folder(session_id, root=None):
    if not isinstance(session_id, str) or not SESSION_RE.fullmatch(session_id):
        raise ProductionError('Invalid production session ID.')
    folder = _store(root) / session_id
    if folder.is_symlink() or not folder.is_dir():
        raise ProductionError('Production session is unavailable.')
    return folder


def save_revision(session_id, title, assets, verified, *, notes='', root=None):
    data = _validate(title, assets, verified, notes, allow_missing=False)
    folder = _session_folder(session_id, root)
    receipt = folder / ('revision-' + uuid.uuid4().hex + '.json')
    data['created_at_unix'] = int(time.time())
    try:
        with receipt.open('x', encoding='utf-8') as output:
            os.chmod(receipt, 0o600)
            json.dump(data, output, indent=2, ensure_ascii=True, allow_nan=False)
    except BaseException:
        receipt.unlink(missing_ok=True)
        raise
    return receipt


def _revision_data(file):
    if (file.is_symlink() or not REVISION_RE.fullmatch(file.name)
            or not file.is_file() or not 0 < file.stat().st_size <= MAX_BYTES):
        raise ProductionError('Invalid or unsupported production revision.')
    try:
        data = json.loads(file.read_text(encoding='utf-8'))
    except (ValueError, OSError, UnicodeError) as exc:
        raise ProductionError('Damaged production checkpoint.') from exc
    if not isinstance(data, dict) or data.get('schema') != 1:
        raise ProductionError('Unsupported production revision schema.')
    cleaned = _validate(data.get('title'), data.get('assets'),
                        data.get('reviewed_stems'), data.get('notes', ''),
                        allow_missing=True)
    cleaned['created_at_unix'] = data.get('created_at_unix', 0)
    cleaned['missing'] = [
        role for role, path in cleaned['assets'].items() if not Path(path).is_file()
    ]
    return cleaned


def _latest(folder):
    checked = sorted(
        (p for p in folder.glob('revision-*.json') if not p.is_symlink() and p.is_file()),
        key=lambda p: p.stat().st_mtime_ns, reverse=True,
    )
    for file in checked:
        try:
            return file, _revision_data(file)
        except (ProductionError, OSError):
            continue
    raise ProductionError('No readable production revisions found.')


def load_session(session_id, *, root=None):
    folder = _session_folder(session_id, root)
    file, data = _latest(folder)
    data['id'] = session_id
    data['revision'] = str(file)
    return data


def list_sessions(*, root=None, limit=MAX_SESSIONS):
    store = _store(root)
    if not store.is_dir():
        return []
    listing = []
    for folder in store.glob('session-*'):
        if folder.is_symlink() or not folder.is_dir():
            continue
        try:
            data = load_session(folder.name, root=store)
            data['sort_ns'] = Path(data['revision']).stat().st_mtime_ns
            listing.append(data)
        except (ProductionError, OSError):
            continue
    return sorted(listing, key=lambda item: item['sort_ns'], reverse=True)[:max(1, min(limit, MAX_SESSIONS))]


def next_action(data):
    """Never infer real isolated stems from a full mixed song reference."""
    assets = data['assets']
    reviewed = data['reviewed_stems']
    if 'reference_mix' not in assets and not any(role in assets for role in STEM_ROLES):
        return 'Develop a song in Studio AI or record individual WAV stems.'
    if not any(role in assets and reviewed.get(role) for role in STEM_ROLES):
        return 'Review separated or recorded WAV stems before assigning them to instruments.'
    if 'final_mix' not in assets:
        return 'Send two or more reviewed, distinct stems to Band Mixer; audition the result.'
    return 'Send the approved finished WAV to Release Desk and review the exported formats.'


def _public_progress(data):
    available = [
        role for role in STEM_ROLES if role in data['assets'] and
        data['reviewed_stems'].get(role) and role not in data['missing']
    ]
    # Voice output contains no file paths, lyrics, notes or other private content.
    if 'final_mix' in data['assets'] and 'final_mix' not in data['missing']:
        stage = 'finished WAV selected; release export is available'
    elif len(available) >= 2:
        stage = 'separate reviewed stems ready for the Band Mixer'
    elif 'reference_mix' in data['assets'] and 'reference_mix' not in data['missing']:
        stage = 'song reference available; review real stems'
    else:
        stage = 'arrangement and source recordings in progress'
    return f'Studio production: {stage}. {len(available)} reviewed WAV stem(s).'


def latest_status(*, root=None):
    entries = list_sessions(root=root, limit=1)
    if not entries:
        return 'No Studio Production Board sessions saved yet.'
    return _public_progress(entries[0])


def main():
    parser = argparse.ArgumentParser(description='Studio read-only production summary')
    parser.add_argument('--summary', action='store_true')
    args = parser.parse_args()
    if not args.summary:
        parser.error('Only the read-only --summary action is supported.')
    print(latest_status())


if __name__ == '__main__':
    main()
