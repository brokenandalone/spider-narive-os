#!/usr/bin/env python3
"""Read-only inventory of system-installed Kali .desktop application launchers.

Runs inside the existing Kali Distrobox from stdin. Lists only system-owned
/usr/share/applications/*.desktop entries, never arbitrary host executables.
The user must select an app explicitly; this file never starts anything.
"""
import configparser
import json
from pathlib import Path

SYSTEM_APPS = Path("/usr/share/applications")
LIMIT = 1500
IGNORED = {"Application", "GTK", "Qt", "X-GNOME", "X-XFCE", "Utility"}


def safe_label(text, limit=95):
    return "".join(c for c in str(text) if c.isprintable()).strip()[:limit]


def catalog():
    entries = []
    if not SYSTEM_APPS.is_dir():
        return entries
    for path in sorted(SYSTEM_APPS.glob("*.desktop"))[:LIMIT]:
        if path.is_symlink() or not path.is_file():
            continue
        identifier = path.name
        if len(identifier) > 108 or not all(
            char.isascii() and (char.isalnum() or char in "._+-")
            for char in identifier
        ):
            continue
        if not identifier[0].isalnum():
            continue
        cfg = configparser.RawConfigParser(strict=False, interpolation=None)
        cfg.optionxform = str
        try:
            with path.open("r", encoding="utf-8", errors="replace") as stream:
                cfg.read_file(stream)
            if not cfg.has_section("Desktop Entry"):
                continue
            entry = cfg["Desktop Entry"]
            if entry.get("Type", "") != "Application":
                continue
            if entry.get("Hidden", "").casefold() == "true":
                continue
            if entry.get("NoDisplay", "").casefold() == "true":
                continue
            if not entry.get("Exec", "").strip():
                continue
            title = safe_label(entry.get("Name", ""))
            if not title:
                continue
            categories = [
                safe_label(item, 55)
                for item in entry.get("Categories", "").split(";")
                if item and item not in IGNORED
            ]
            kali = next(
                (c for c in categories if c.lower().startswith("x-kali")),
                None,
            )
            group = kali or (categories[0] if categories else "Other")
            description = safe_label(entry.get("Comment", ""), 200)
            entries.append({
                "id": identifier,
                "name": title,
                "category": group,
                "description": description,
            })
        except (OSError, configparser.Error, UnicodeError, ValueError):
            continue
    return entries


if __name__ == "__main__":
    print(json.dumps({"applications": catalog()}, ensure_ascii=True))
