"""Read-only GTK and KDE appearance compatibility inventory.

A GTK 3/4 settings.ini is a hint, not proof of rendered theme. In particular,
GTK 4/libadwaita apps may consult the desktop color-scheme portal rather than
gtk-theme-name. No settings are changed, no subprocess or network calls.
"""
import configparser
import os
from pathlib import Path
import re

MAX_SETTINGS = 16384
SAFE_VALUE = re.compile(r'[a-zA-Z0-9._+ -]{1,70}\Z')


def config_root(home=None):
    if home is not None:
        return Path(home)
    return Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config')))


def read_ini(path, section, keys):
    """Read only a few public preference names; refuse symlinks/large files."""
    path = Path(path)
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_SETTINGS:
            return {}
        parser = configparser.ConfigParser(interpolation=None, strict=False)
        parser.read_string(path.read_text(encoding='utf-8'))
        if not parser.has_section(section):
            return {}
        found = {}
        for key in keys:
            value = parser.get(section, key, fallback='').strip()
            if SAFE_VALUE.fullmatch(value):
                found[key] = value
        return found
    except (OSError, UnicodeError, ValueError, configparser.Error):
        return {}


def appearance_snapshot(config_home=None):
    """Display configured preferences only, without claiming all apps obey."""
    root = config_root(config_home)
    gtk3 = read_ini(root / 'gtk-3.0/settings.ini', 'Settings',
                    ('gtk-theme-name', 'gtk-application-prefer-dark-theme'))
    gtk4 = read_ini(root / 'gtk-4.0/settings.ini', 'Settings',
                    ('gtk-theme-name', 'gtk-application-prefer-dark-theme'))
    kde = read_ini(root / 'kdeglobals', 'General', ('ColorScheme',))

    def gtk_summary(settings):
        theme = settings.get('gtk-theme-name', 'not specified')
        prefer = settings.get('gtk-application-prefer-dark-theme', 'not specified')
        if prefer == '1':
            dark = 'dark requested'
        elif prefer == '0':
            dark = 'light requested'
        else:
            dark = 'dark preference not specified'
        return f'{theme} · {dark}'

    return {
        'GTK 3': gtk_summary(gtk3),
        'GTK 4': gtk_summary(gtk4) + ' (not authoritative for libadwaita)',
        'KDE colors': kde.get('colorscheme', 'not specified'),
    }
