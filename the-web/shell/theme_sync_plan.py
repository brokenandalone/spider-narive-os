"""Dry-run only Plasma / GTK appearance planning for Spider OS.

This module intentionally HAS NO apply function. KDE owns the actual Plasma
color-scheme transition and may sync GTK 3 Breeze colors via kde-gtk-config.
GTK 4 and libadwaita may use XDG desktop portals and app preferences. Never
force GTK_THEME, edit user GTK/KDE files or assume portal compatibility.
"""
import os
from pathlib import Path
import shutil

from gtk_compat import appearance_snapshot

SCHEMES = {'dark': 'BreezeDark', 'light': 'BreezeLight'}
DESKTOP_NAMES = {'dark': 'Breeze Dark', 'light': 'Breeze Light'}


def available_scheme(scheme, data_roots):
    """Only inspect known *.colors files; do not follow owner symlink overrides."""
    if scheme not in SCHEMES.values():
        return False
    for root in data_roots:
        path = Path(root) / 'color-schemes' / (scheme + '.colors')
        try:
            if (not path.is_symlink() and path.is_file()
                    and 0 < path.stat().st_size <= 262144):
                return True
        except OSError:
            pass
    return False


def default_data_roots(env):
    entries = []
    home = Path(env.get('XDG_DATA_HOME') or (Path.home() / '.local/share'))
    entries.append(home)
    for value in (env.get('XDG_DATA_DIRS') or '/usr/local/share:/usr/share').split(':'):
        if value.startswith('/'):
            entries.append(Path(value))
    return tuple(dict.fromkeys(entries))


def plan_theme(mode, *, env=None, data_roots=None, which=shutil.which,
               snapshot=appearance_snapshot):
    """Return a preview, not commands or permission to mutate appearance."""
    if mode not in SCHEMES or not isinstance(mode, str):
        raise ValueError('Unknown appearance mode')
    env = dict(os.environ if env is None else env)
    roots = tuple(default_data_roots(env) if data_roots is None else data_roots)
    target = SCHEMES[mode]
    settings = snapshot()
    present = available_scheme(target, roots)
    plasma_tool = which('plasma-apply-colorscheme')
    desktop = env.get('XDG_CURRENT_DESKTOP', '').strip()[:120]
    override = env.get('GTK_THEME', '')
    problems = []
    if not plasma_tool:
        problems.append('The Plasma color-scheme command was not found.')
    if not present:
        problems.append(target + '.colors was not found in the configured theme directories.')
    if override:
        problems.append('GTK_THEME is overridden in the environment; GTK apps may ignore desktop appearance.')
    if not ('KDE' in desktop.upper() or 'PLASMA' in desktop.upper()
            or 'THEWEB' in desktop.upper()):
        problems.append('The current desktop is not confirmed as KDE or The Web.')

    steps = [
        f'Plasma/Qt: after approval, use the installed native color-scheme tool to select {DESKTOP_NAMES[mode]} (if compatible).',
        'GTK 3: KDE GTK integration may synchronize Breeze colors; do not overwrite gtk-3.0/settings.ini or custom themes.',
        'GTK 4/libadwaita: first verify the desktop portal and each app\'s style preference. A GTK 3 setting is not sufficient.',
        'The Web: its own remembered violet appearance stays separate until the user explicitly coordinates the switch.',
    ]
    return {
        'mode': mode,
        'scheme': target,
        'desktop': desktop or 'unknown',
        'installed': present,
        'plasma_tool_present': bool(plasma_tool),
        'existing': settings,
        'blockers': problems,
        'steps': steps,
        'dry_run': True,
        'mutates_files': False,
        'requires_separate_approval': True,
    }


def render_plan(plan):
    lines = [
        'SPIDER OS  ·  KDE / GTK APPEARANCE PREVIEW',
        'Requested: ' + plan['mode'] + '  (' + plan['scheme'] + ')',
        'Desktop: ' + plan['desktop'],
        'Theme file: ' + ('found' if plan['installed'] else 'not found'),
        'Plasma colors tool: ' + ('found' if plan['plasma_tool_present'] else 'not found'),
        '',
        'CURRENT PREFERENCES (not guaranteed rendered appearance)',
    ]
    for label, setting in plan['existing'].items():
        lines.append('  ' + label + ': ' + str(setting)[:160])
    lines.extend(('', 'PROPOSED WORK (not executed):'))
    for index, step in enumerate(plan['steps'], 1):
        lines.append(f'  {index}. {step}')
    if plan['blockers']:
        lines.extend(('', 'BEFORE ANY SYSTEM-WIDE CHANGE:'))
        lines.extend('  • ' + reason for reason in plan['blockers'])
    lines.extend((
        '',
        'This is a READ-ONLY preview. No settings or app themes were changed.',
        'Actual KDE/GTK coordination needs a separately approved, backed-up installation session.',
    ))
    return '\n'.join(lines)
