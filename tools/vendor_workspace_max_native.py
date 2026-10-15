#!/usr/bin/env python3
"""Vendor the exact reviewed Workspace MAX v4 engines into the Spider OS source.

Run this from a checked-out feature/native-immersive-bays-v8-20261015 branch.
It changes source files in that Git checkout only; it does not install Spider OS,
restart Webbie/Nova, push to GitHub, or modify the original ZIP.
"""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import zipfile

BRANCH = "feature/native-immersive-bays-v8-20261015"
ZIP_SHA256 = "ac9af96ea33201817a43190d4cc622621f386002bae79b493ac068625e1cf391"
MODULES = (
    "__init__.py", "security.py", "max_art.py", "max_author.py",
    "max_backups.py", "max_board.py", "max_catalog.py", "max_comms.py",
    "max_core.py", "max_dev.py", "max_forage.py", "max_gui.py",
    "max_kali.py", "max_media.py", "max_nova.py", "max_recovery.py",
    "max_studio.py", "max_study.py", "max_system.py", "max_theweb.py",
    "max_webbie.py",
)

def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as reader:
        for chunk in iter(lambda: reader.read(512*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def run():
    repo = Path(__file__).resolve().parents[1]
    actual = subprocess.run(["git", "-C", str(repo), "branch", "--show-current"],
                            check=True, text=True, capture_output=True).stdout.strip()
    if actual != BRANCH:
        raise RuntimeError("Checked-out Git branch must be " + BRANCH)
    if (repo / "spider_max_source").is_symlink():
        raise RuntimeError("Refusing symlinked source directory")
    options = [Path(p).expanduser() for p in sys.argv[1:]]
    options += [Path.home() / "Downloads/Spider_OS_2026_10_WORKSPACE_MAX_v4.zip"]
    package = next((p for p in options if p.is_file() and not p.is_symlink() and
                    digest(p) == ZIP_SHA256), None)
    if package is None:
        raise RuntimeError("Place the original reviewed Workspace MAX v4 ZIP in Downloads")
    destination = repo / "spider_max_source/spider_monster"
    if destination.exists() and destination.is_symlink():
        raise RuntimeError("Refusing a symlinked destination")
    with zipfile.ZipFile(package) as archive:
        for filename in MODULES:
            entry = archive.getinfo("spider_monster/" + filename)
            if entry.file_size > 100_000 or entry.is_dir():
                raise RuntimeError("Unexpected source entry " + filename)
            payload = archive.read(entry)
            output = destination / filename
            if output.is_symlink():
                raise RuntimeError("Refusing symlink " + str(output))
            if output.exists() and output.read_bytes() != payload:
                raise RuntimeError("Existing source differs: " + str(output))
        destination.mkdir(parents=True, exist_ok=True)
        for filename in MODULES:
            output = destination / filename
            if not output.exists():
                output.write_bytes(archive.read("spider_monster/" + filename))
    print("VENDORED: Reviewed source for all 137 MAX operations into native Spider OS Git checkout")
    print("PATH:", destination)
    print("NOT INSTALLED OR PUSHED. Review and commit the source on this feature branch.")

if __name__ == "__main__":
    try:
        run()
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError,
            zipfile.BadZipFile, KeyError) as exc:
        print("VENDORING BLOCKED:", exc, file=sys.stderr)
        raise SystemExit(2)
