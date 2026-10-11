"""Accessible menus for The Web, without changing KDE or native app themes.

This preference governs the desktop shell's menus, combo-box drop-downs,
search lists and tooltips. Wallpapers, Plasma, GTK and application contents
are deliberately left alone.
"""
import json
import os
from pathlib import Path
import tempfile

MENU_SIZES = {'comfortable': 16, 'large': 19, 'extra-large': 22}
DEFAULT_MENU_SIZE = 'large'


def menu_size_file(home=None):
    base = Path(home) if home is not None else Path(
        os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config')))
    return base / 'spider-os' / 'readability.json'


def load_menu_size(path=None):
    location = Path(path) if path is not None else menu_size_file()
    try:
        if location.is_symlink() or not location.is_file() or location.stat().st_size > 4096:
            return DEFAULT_MENU_SIZE
        data = json.loads(location.read_text(encoding='utf-8'))
        if isinstance(data, dict) and data.get('menu_size') in MENU_SIZES:
            return data['menu_size']
    except (OSError, UnicodeError, ValueError, TypeError):
        pass
    return DEFAULT_MENU_SIZE


def save_menu_size(value, path=None):
    if not isinstance(value, str) or value not in MENU_SIZES:
        raise ValueError('Unsupported menu text size')
    location = Path(path) if path is not None else menu_size_file()
    if location.is_symlink() or location.parent.is_symlink():
        raise OSError('Refusing symlinked Spider OS readability settings')
    location.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if location.exists() and not location.is_file():
        raise OSError('Readability settings are not a regular file')
    fd, temporary = tempfile.mkstemp(dir=location.parent, prefix='.readability-')
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump({'version': 1, 'menu_size': value}, stream)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, location)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def readability_css(theme, size):
    """A solid, legible foreground/background for all native Qt popups.

    Qt popup lists can be top-level windows and inherit the host's KDE palette,
    so stylesheet rules must name the popup view explicitly. Color selections
    are paired in both themes to avoid pale-on-pale or violet-on-violet text.
    """
    if theme not in ('dark', 'light'):
        raise ValueError('Invalid appearance mode')
    if size not in MENU_SIZES:
        raise ValueError('Invalid menu size')
    px = MENU_SIZES[size]
    if theme == 'dark':
        bg, fg, border, hover, hover_fg, muted = (
            '#130d1b', '#fffaff', '#a97bd4', '#50306e', '#ffffff', '#c9b4dd')
    else:
        bg, fg, border, hover, hover_fg, muted = (
            '#fffcff', '#241332', '#8144b1', '#e3cafa', '#241332', '#5a4c66')
    return f"""
QMenu, QComboBox QAbstractItemView {{
    background-color: {bg};
    color: {fg};
    border: 2px solid {border};
    selection-background-color: {hover};
    selection-color: {hover_fg};
    font-size: {px}px;
}}
QMenu::item {{
    padding: 10px 22px;
    color: {fg};
    min-height: 26px;
}}
QMenu::item:selected {{
    color: {hover_fg};
    background-color: {hover};
}}
QMenu::item:disabled {{ color: {muted}; }}
QMenu::separator {{ height: 1px; background: {border}; margin: 6px 12px; }}
QComboBox {{
    color: {fg};
    background-color: {bg};
    border: 2px solid {border};
    min-height: 32px;
    font-size: {px}px;
}}
QComboBox::drop-down {{ background-color: {hover}; border-left: 1px solid {border}; width: 28px; }}
QComboBox QAbstractItemView::item {{
    padding: 8px 12px;
    min-height: 30px;
    color: {fg};
}}
QComboBox QAbstractItemView::item:selected {{
    color: {hover_fg};
    background-color: {hover};
}}
QListWidget {{
    font-size: {px}px;
    selection-background-color: {hover};
    selection-color: {hover_fg};
}}
QListWidget::item {{ padding: 8px 12px; min-height: 28px; }}
QListWidget::item:selected {{
    color: {hover_fg};
    background-color: {hover};
}}
QToolTip {{
    background-color: {bg};
    color: {fg};
    border: 2px solid {border};
    font-size: {px}px;
    padding: 7px 10px;
}}
"""
