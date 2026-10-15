"""Bounded local SoundFont discovery for Spider's autonomous instruments.

Only a small set of known sound library locations is checked. No recursive
home scan, internet traffic, microphone, MIDI access or package installation.
Finding a big file does not prove its fidelity or distribution rights.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

try:
    from .soundfont_render import validate_soundfont
except ImportError:
    from soundfont_render import validate_soundfont

MAX_CANDIDATES = 96

def default_roots(home=None):
    h = Path.home() if home is None else Path(home)
    return [
        Path("/usr/share/sounds/sf2"),
        Path("/usr/share/sounds/sf3"),
        Path("/usr/local/share/sounds/sf2"),
        h / ".local/share/sounds/sf2",
        h / ".local/share/sounds/sf3",
        h / "Music/SoundFonts",
        h / "SoundFonts",
    ]

def discover_soundfonts(roots=None, max_items=MAX_CANDIDATES):
    """Return validated local SF2/SF3 paths, sorted by size then name.

    File size is only a practical starting point for auditioning sample banks.
    It is not a measure of sound quality and does not establish licensing.
    """
    if type(max_items) is not int or not 1 <= max_items <= MAX_CANDIDATES:
        raise ValueError("Invalid scan limit")
    library_roots = default_roots() if roots is None else [Path(root) for root in roots]
    found = []
    seen = set()
    examined = 0
    for root in library_roots[:12]:
        if root.is_symlink() or not root.is_dir():
            continue
        try:
            candidates = sorted(root.iterdir(), key=lambda p: p.name.casefold())
        except OSError:
            continue
        for path in candidates:
            if examined >= MAX_CANDIDATES or len(found) >= max_items:
                break
            if path.suffix.lower() not in (".sf2", ".sf3") or path.is_symlink():
                continue
            examined += 1
            try:
                validated = validate_soundfont(path).resolve()
                if validated not in seen:
                    seen.add(validated)
                    found.append(validated)
            except (ValueError, OSError):
                continue
        if examined >= MAX_CANDIDATES or len(found) >= max_items:
            break
    found.sort(key=lambda path: (-path.stat().st_size, path.name.casefold()))
    return found

def auto_soundfont(roots=None):
    banks = discover_soundfonts(roots=roots)
    return banks[0] if banks else None
