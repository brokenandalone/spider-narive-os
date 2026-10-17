#!/usr/bin/env python3
"""Explicit, conservative uninstall of ONE installed Spider Audio Studio beta.

No sudo, no broad home deletion, no removal of other versions or music.
Refuses to remove modified installations or unexpected user files, including
files that may have accidentally been stored inside the app directory.
"""
from __future__ import annotations
import argparse
import fcntl
import os
from pathlib import Path
import re
import shutil
import sys
try:
    from .install_for_user import (DESKTOP_ID,VERSION_RE,_safe_under,verify)
except ImportError:
    from install_for_user import (DESKTOP_ID,VERSION_RE,_safe_under,verify)


_PYC=re.compile(r"^([A-Za-z0-9_]+)\.cpython-\d{2,3}(?:\.opt-[012])?\.pyc$")

def _paths(version,home=None):
    if type(version) is not str or VERSION_RE.fullmatch(version) is None:
        raise ValueError("Specify exactly one valid installed beta version.")
    home=Path(home or Path.home()).expanduser().absolute()
    versions=_safe_under(home,home/".local"/"share"/"spider-audio-studio"/"versions")
    location=_safe_under(home,versions/version)
    desktop=_safe_under(
        home,home/".local"/"share"/"applications"/
        (DESKTOP_ID+version.replace(".","_")+".desktop"))
    return home,versions,location,desktop

def installed_versions(home=None):
    home=Path(home or Path.home()).expanduser().absolute()
    versions=_safe_under(home,home/".local"/"share"/"spider-audio-studio"/"versions")
    if not versions.is_dir():
        return []
    result=[]
    for child in versions.iterdir():
        try:
            if (not child.is_symlink() and child.is_dir() and
                    VERSION_RE.fullmatch(child.name)):
                result.append(child.name)
        except OSError:
            continue
    return sorted(result)

def _only_known_files(location,manifest):
    expected={
        "manifest.json","run_spider_audio_studio.py",
        *(("app/"+name) for name in manifest["files"]),
        *(name for name in manifest["extras"]),
    }
    for item in location.rglob("*"):
        if item.is_symlink():
            raise ValueError("Cannot uninstall a linked app file or directory.")
        if item.is_dir():
            continue
        if not item.is_file():
            raise ValueError("Unsupported file inside the app installation.")
        name=item.relative_to(location).as_posix()
        if name in expected:
            continue
        parent=item.parent
        match=_PYC.fullmatch(item.name)
        if (parent.name=="__pycache__" and match is not None):
            origin=(parent.parent/(match.group(1)+".py")).relative_to(location).as_posix()
            if origin in expected:
                continue
        raise ValueError(
            "Unexpected file inside installed Studio: "+name+
            ". Preserve it before manually removing the beta.")

def remove_version(version,home=None):
    """Remove only a verified version and exactly matching app-menu shortcut."""
    home,versions,location,desktop=_paths(version,home)
    if (location.is_symlink() or not location.is_dir() or
            desktop.is_symlink() or not desktop.is_file()):
        raise ValueError("Only fully installed regular betas may be removed.")
    lock=_safe_under(home,versions/".install.lock")
    if lock.is_symlink() or not lock.is_file():
        raise ValueError("The owner installer lock is missing or linked.")
    with lock.open("a+b") as lockfile:
        fcntl.flock(lockfile.fileno(),fcntl.LOCK_EX)
        info=verify(location)
        if info["version"]!=version:
            raise ValueError("Installed package version does not match removal request.")
        expected_launcher=str(location/"run_spider_audio_studio.py")
        # Guard any owner-edited or replaced .desktop file. It is never okay
        # to delete arbitrary desktop entries, even if their name looks right.
        desktop_text=desktop.read_text(encoding="utf-8")
        if (len(desktop_text)>16_000 or
                "X-SpiderStudio-PrivateBeta=true" not in desktop_text or
                expected_launcher not in desktop_text or
                f"Beta {version})" not in desktop_text):
            raise ValueError("The versioned desktop shortcut has been customized; refusing removal.")
        _only_known_files(location,info)
        # Every app source checksum and installed extra was already verified.
        # No symbolic links or unknown personal files are admitted.
        shutil.rmtree(location)
        desktop.unlink()
    return location,desktop

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list-versions",action="store_true")
    group.add_argument("--remove",metavar="VERSION")
    args=parser.parse_args(argv)
    if hasattr(os,"geteuid") and os.geteuid()==0:
        parser.exit(2,"The beta uninstaller must not run as root.\n")
    try:
        if args.list_versions:
            for version in installed_versions():
                print(version)
        else:
            remove_version(args.remove)
            print("Removed only Spider Audio Studio beta:",args.remove)
            print("Original recordings, mixes, other versions and Spider OS are untouched.")
    except (OSError,ValueError) as error:
        parser.exit(2,"Uninstall safely blocked: "+str(error)+"\n")

if __name__=="__main__":
    raise SystemExit(main())
