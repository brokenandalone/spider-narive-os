"""Pure, bounded launcher search shared by The Web palette and its tests.

Results are suggestions only. This module never executes text or shell commands.
Only keys present in the installed XDG catalog or the fixed internal action
registry can be activated by the GUI.
"""
from dataclasses import dataclass
import re
import unicodedata

INTERNAL_ACTIONS = (
    ('windows', 'Open Windows', 'Switch, minimize, or close a running window'),
    ('home', 'Workspace Home', 'Return to The Web without closing open tabs'),
    ('webbie', 'Ask Webbie', 'Open your existing Webbie assistant'),
    ('quick-settings', 'Quick Settings', 'Network, appearance, and desktop controls'),
    ('notifications', 'Notifications', 'Review recent desktop alerts'),
    ('tray', 'Background Apps', 'View the background application tray'),
    ('refresh-apps', 'Refresh Applications', 'Rescan installed applications'),
    ('desktop', 'The Web Home', 'Return to the desktop home screen'),
    ('system-settings', 'KDE System Settings', 'Open the existing KDE settings app'),
    ('lock', 'Lock Screen', 'Use the secure KDE screen locker'),
)


@dataclass(frozen=True)
class Result:
    kind: str
    ident: str
    label: str
    detail: str
    score: int


def normalized(text):
    value = unicodedata.normalize('NFKD', str(text or '')).casefold()
    return ''.join(character for character in value if not unicodedata.combining(character))


def _score(query, label, detail):
    words = normalized(query).split()
    if not words:
        return 1
    name = normalized(label)
    extra = normalized(detail)
    if not all(word in name or word in extra for word in words):
        return 0
    score = 10
    if name == ' '.join(words):
        score += 140
    if name.startswith(' '.join(words)):
        score += 85
    if all(word in name for word in words):
        score += 35
    for word in words:
        if name.startswith(word):
            score += 22
        elif re.search(r'\b' + re.escape(word), name):
            score += 15
        elif word in name:
            score += 6
        else:
            score += 1
    return score


def find_items(query, workspaces, applications=(), favorites=(), recents=(), limit=60, windows=()):
    """Rank known choices, never arbitrary user-supplied executable strings."""
    text = str(query or '').strip()[:120]
    favorite_keys = set(favorites)
    recent_keys = list(recents)[:30]
    results = []

    for key, label in workspaces.items():
        if key == 'default':
            continue
        score = _score(text, label, 'workspace ' + key)
        if score:
            identity = ('workspace', key)
            bonus = (55 if identity in favorite_keys else 0) + (
                max(0, 35 - 2 * recent_keys.index(identity)) if identity in recent_keys else 0)
            results.append(Result('workspace', key, str(label), 'Workspace', score + bonus))

    for app in applications:
        score = _score(text, app.name, (app.comment or '') + ' ' + app.desktop_id)
        if score:
            identity = ('app', app.desktop_id)
            bonus = (45 if identity in favorite_keys else 0) + (
                max(0, 30 - 2 * recent_keys.index(identity)) if identity in recent_keys else 0)
            results.append(Result('app', app.desktop_id, app.name,
                                  'Installed app · ' + workspaces.get(app.workspace, app.workspace),
                                  score + bonus))

    for task in windows:
        ident = getattr(task, 'ident', None)
        title = str(getattr(task, 'title', '') or '')[:180]
        if not valid_window_id(ident) or not title:
            continue
        score = _score(text, title, 'open window running program')
        if score:
            results.append(Result('window', ident.lower(), title, 'Open window', score + 12))

    for key, label, detail in INTERNAL_ACTIONS:
        score = _score(text, label, detail + ' ' + key.replace('-', ' '))
        if score:
            results.append(Result('action', key, label, detail, score - (15 if not text else 0)))

    return sorted(results, key=lambda item: (-item.score, item.label.casefold(), item.ident))[:max(0, min(int(limit), 120))]


def valid_window_id(ident):
    return (isinstance(ident, str) and
            re.fullmatch(r'0x[0-9a-fA-F]{1,16}', ident) is not None and
            int(ident, 16) != 0)


def display_text(result, is_favorite=False):
    marker = '★  ' if is_favorite else ''
    return marker + result.label + '    ·    ' + result.detail
