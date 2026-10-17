#!/usr/bin/env python3
"""Read-only audit of the three duplicate Spider OS control-center shortcuts.

Reports user Desktop icons separately from normal XDG application-menu
entries. NO deletions, chmod, unlink, remote access or package changes.
Every original Ubuntu Studio application remains fully installed.
"""
from __future__ import annotations

import argparse
import configparser
from pathlib import Path

KNOWN = {
    "spider-os-universal.desktop": "The Web Home native dashboard and individual bays",
    "spider-os-workspace-max.desktop": "Advanced tools & tasks inside the appropriate native bay",
    "spider-webbie-intelligence.desktop": "Webbie > Webbie controls",
}
NAMES = ("universal control center", "workspace max", "webbie intelligence center")


def inspect_entries(directory):
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        return []
    found = []
    for file in sorted(directory.glob("*.desktop")):
        if not file.is_file() or file.is_symlink():
            continue
        if file.stat().st_size > 150_000:
            continue
        parser = configparser.ConfigParser(interpolation=None, strict=False)
        parser.optionxform = str
        try:
            parser.read(file, encoding="utf-8")
            data = parser["Desktop Entry"]
            name = data.get("Name", "")
            if file.name not in KNOWN and not any(
                    label in name.casefold() for label in NAMES):
                continue
            found.append({
                "filename": file.name,
                "name": name,
                "location": str(directory),
                "replacement": KNOWN.get(file.name) or
                "Open its original native Webbie / MAX / Home bay",
            })
        except (OSError, ValueError, KeyError, configparser.Error):
            continue
    return found


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--desktop-directory", type=Path, default=Path.home() / "Desktop")
    args = parser.parse_args(argv)
    menu = Path.home() / ".local/share/applications"
    paths = (("Desktop icons", args.desktop_directory), ("User app menu", menu),
             ("System app menu", Path("/usr/share/applications")))
    print("SPIDER OS | LEGACY CONTROL-CENTER SHORTCUT AUDIT (READ ONLY)")
    count = 0
    for description, directory in paths:
        entries = inspect_entries(directory)
        print(description + ": " + str(len(entries)))
        if not directory.is_dir():
            print("  Folder not present:", str(directory))
        for item in entries:
            print("  {} | {}".format(item["name"], item["filename"]))
            print("    Suggested native replacement:", item["replacement"])
        count += len(entries)
    print("Found", count, "matching menu/icon entries. No files were changed.")
    print("Desktop icons and application-menu registration are different things.")
    print("Do not delete originals until a reconciled native build is installed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
