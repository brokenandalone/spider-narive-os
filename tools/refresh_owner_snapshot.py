#!/usr/bin/env python3
"""Capture a NEW private owner source snapshot when the running PC has changed.

Existing archive is immutable and never replaced. Read-only against the
installed Spider OS. Reports only relative filenames/hashes/sizes, not code.
The caller must STILL review all changed files before proposing updates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import zipfile

from build_owner_preserving_stage import (
    INSTALLED, OWNER_FILES, MAX_EACH, MAX_TOTAL,
    checked_path, load_owner_zip, parse_only, digest,
)


def collect(originals: dict[str,bytes], root: Path) -> tuple[dict, dict[str,bytes]]:
    root = Path(root).resolve()
    if set(originals) != set(OWNER_FILES):
        raise ValueError("Archive is not the reviewed 31-file owner snapshot")
    current: dict[str, bytes] = {}
    changes = []
    total = 0
    for name in OWNER_FILES:
        target = checked_path(root, name)
        data = target.read_bytes()
        if not data or len(data) > MAX_EACH:
            raise ValueError("Owner source empty or too large: " + name)
        total += len(data)
        if total > MAX_TOTAL:
            raise ValueError("Owner source exceeds review safety size")
        parse_only(name,data)
        current[name] = data
        before = originals[name]
        if before != data:
            changes.append({
                "path": name,
                "previous_sha256": digest(before),
                "current_sha256": digest(data),
                "previous_bytes": len(before),
                "current_bytes": len(data),
                "status": "CHANGED_SINCE_OLD_ZIP_REVIEW_REQUIRED",
            })
    report = {
        "status": "FRESH_OWNER_SNAPSHOT_REVIEW_ONLY",
        "scope": "NATIVE_SPIDER_OS_ONLY",
        "previous_archive_preserved": True,
        "installed_files_modified": False,
        "source_code_in_report": False,
        "expected_review_file_count": len(OWNER_FILES),
        "changed_file_count": len(changes),
        "changed_files": changes,
        "notes": [
            "This is new owner source, NOT an approved release or known-good baseline.",
            "Previous ZIP remains available for comparing owner changes.",
            "All modified installed files must be reconciled before any OS installation.",
            "Spider Media Center and BCN website are separate and not captured.",
        ],
    }
    return report,current


def make_snapshot(previous: Path, installed: Path, destination: Path) -> dict:
    previous = Path(previous).resolve()
    installed = Path(installed).resolve()
    destination = Path(destination).expanduser().absolute()
    source = Path(__file__).resolve().parents[1]
    if (destination.exists() or destination.is_symlink()
            or destination == installed or installed in destination.parents
            or destination == source or source in destination.parents):
        raise ValueError("New review directory required outside installed OS and Git checkout")
    # Source is validated entirely before ANY new output is created.
    original = load_owner_zip(previous)
    report,current = collect(original, installed)
    destination.mkdir(mode=0o700,parents=True)
    try:
        archive = destination / "Spider_OS_Current_31_Source.zip"
        fd = os.open(archive, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "wb") as output:
                with zipfile.ZipFile(output,"w",compression=zipfile.ZIP_DEFLATED) as z:
                    for name,data in current.items():
                        z.writestr("installed/" + name,data)
        except BaseException:
            archive.unlink(missing_ok=True)
            raise
        info = destination / "owner-source-drift.json"
        fd = os.open(info,os.O_WRONLY | os.O_CREAT | os.O_EXCL,0o600)
        try:
            with os.fdopen(fd,"w",encoding="utf-8") as output:
                json.dump(report,output,indent=2)
                output.write("\n")
        except BaseException:
            info.unlink(missing_ok=True)
            raise
        # Verify what we wrote and ensure no file changed during capture.
        written = load_owner_zip(archive)
        if any(written[name] != current[name] for name in OWNER_FILES):
            raise ValueError("New snapshot verification failed")
        for name,data in current.items():
            if checked_path(installed,name).read_bytes() != data:
                raise ValueError("Live PC changed during snapshot: " + name)
    except BaseException:
        shutil.rmtree(destination)
        raise
    return report


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--previous-archive",type=Path,required=True)
    p.add_argument("--installed-root",type=Path,default=INSTALLED)
    p.add_argument("--output-dir",type=Path,required=True)
    args=p.parse_args(argv)
    try:
        result=make_snapshot(args.previous_archive,args.installed_root,args.output_dir)
    except (ValueError,OSError,TypeError,UnicodeError,SyntaxError,
            zipfile.BadZipFile) as e:
        print("OWNER SNAPSHOT BLOCKED:",type(e).__name__,str(e)[:250],
              file=sys.stderr)
        return 3
    print("CURRENT 31-FILE OWNER SNAPSHOT CREATED (PRIVATE, NOT INSTALLED)")
    print("Changed installed source files:",result["changed_file_count"])
    for x in result["changed_files"]:
        print("  CHANGED:",x["path"])
    print("NEW ZIP:",args.output_dir/"Spider_OS_Current_31_Source.zip")
    print("SHAREABLE HASH-ONLY REPORT:",args.output_dir/"owner-source-drift.json")
    print("OLD ZIP RETAINED. WEBBIE AND NOVA NOT RESTARTED. NO INSTALL.")
    return 0


if __name__=="__main__":
    sys.exit(main())
