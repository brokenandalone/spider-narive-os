"""Local Spider OS shell appearance preferences.

Changes only The Web's own Qt stylesheet. It does not edit KDE/GTK themes,
wallpapers, desktop settings, accessibility preferences or user documents.
The default is the established dark violet Spider OS appearance.
"""
import json
import os
from pathlib import Path
import tempfile

VALID_THEMES = ('dark', 'light')
DEFAULT_THEME = 'dark'

def appearance_file(home=None):
    base = Path(home) if home is not None else Path(
        os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config')))
    return base / 'spider-os' / 'appearance.json'

def load_theme(path=None):
    location = Path(path) if path is not None else appearance_file()
    try:
        if location.is_symlink() or not location.is_file() or location.stat().st_size > 4096:
            return DEFAULT_THEME
        value = json.loads(location.read_text(encoding='utf-8'))
        if isinstance(value, dict) and value.get('theme') in VALID_THEMES:
            return value['theme']
    except (OSError, UnicodeError, ValueError, TypeError):
        pass
    return DEFAULT_THEME

def save_theme(theme, path=None):
    """Atomically save an explicit UI choice, excluding unsafe symlink paths."""
    if theme not in VALID_THEMES or not isinstance(theme, str):
        raise ValueError('Only dark and light appearance modes are supported')
    location = Path(path) if path is not None else appearance_file()
    if location.is_symlink() or location.parent.is_symlink():
        raise OSError('Refusing symlinked Spider OS appearance settings')
    location.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if location.exists() and not location.is_file():
        raise OSError('Appearance preferences are not a regular file')
    fd, temp = tempfile.mkstemp(dir=location.parent, prefix='.appearance-')
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as target:
            json.dump({'theme': theme, 'version': 1}, target)
            target.write('\n')
            target.flush()
            os.fsync(target.fileno())
        os.replace(temp, location)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)

# Main desktop chrome only; specific module theme styles are separate work.
# Explicit text, inputs, list/table selections and tooltips must remain legible.
LIGHT_STYLE = """
QWidget { color:#241332; font-family:'Sans Serif'; }
QWidget#root { background:transparent; }
QWidget#panel, QDialog, QTabWidget::pane { background:rgba(248,243,255,245); border:1px solid #9a75bd; border-radius:10px; }
QTabWidget#workspaceTabs[home='true']::pane { background:transparent; border:none; }
QPushButton { font-size:14px; background:#e9d8fd; border:1px solid #8447b8; border-radius:8px; padding:7px 12px; color:#241332; text-align:left; }
QPushButton:hover, QPushButton:checked { background:#d8b4fe; border-color:#6b21a8; }
QPushButton:disabled { background:#ece7f1; color:#71687c; border-color:#b5a8be; }
QLineEdit, QComboBox, QListWidget { background:#ffffff; color:#241332; border:1px solid #955ab8; border-radius:7px; padding:6px; selection-background-color:#d8b4fe; selection-color:#241332; }
QTextEdit, QTableWidget { background:white; alternate-background-color:#f3eafa; color:#241332; border:1px solid #955ab8; selection-background-color:#d8b4fe; selection-color:#241332; }
QHeaderView::section { background:#ebdcf7; color:#241332; padding:6px; border:1px solid #af8dc6; }
QMenu { background:#fbf8ff; color:#241332; border:1px solid #955ab8; }
QMenu::item { padding:8px 18px; }
QMenu::item:selected { background:#d8b4fe; color:#241332; }
QToolTip { background:#fbf8ff; color:#241332; border:1px solid #955ab8; }
QTabBar::tab { background:#f2e7fc; padding:10px 14px; color:#443455; }
QTabBar::tab:selected { background:#6b21a8; color:white; }
QScrollArea { background:transparent; border:none; }
"""
