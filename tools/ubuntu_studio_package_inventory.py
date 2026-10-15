#!/usr/bin/env python3
"""Read-only inventory of installed Ubuntu Studio Debian packages.

Unlike .desktop app-menu listings, package inventory includes CLI tools,
effects, audio/MIDI plugins and libraries. Does not install, remove, update,
hold, configure, execute package scripts, or require sudo.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

FORMAT = "spider-os-dpkg-installed-v1"
PACKAGE = re.compile(r"[a-z0-9][a-z0-9+.-]*(?::[a-z0-9_-]+)?\Z")


def parse_installed(output):
    if not isinstance(output, str) or len(output) > 12_000_000:
        raise ValueError("Unrecognized or oversized dpkg status output")
    result = {}
    for line in output.splitlines():
        fields = line.split("\t")
        if len(fields) != 3:
            continue
        name, version, status = fields
        if not PACKAGE.fullmatch(name):
            continue
        if status.strip().endswith("installed"):
            if not version or len(version) > 256:
                continue
            result[name] = version
    return result


def query_installed():
    # Fixed, read-only program invocation. No shell and no privilege change.
    result = subprocess.run(
        ["dpkg-query", "-W",
         "-f=${binary:Package}\\t${Version}\\t${Status}\\n"],
        check=True, capture_output=True, text=True, timeout=45,
    )
    return parse_installed(result.stdout)


def snapshot_document(installed):
    return {"format": FORMAT, "packages": dict(sorted(installed.items()))}


def compare(before, after):
    if not isinstance(before, dict) or before.get("format") != FORMAT:
        raise ValueError("Unrecognized baseline package inventory format")
    old, new = before.get("packages"), after.get("packages")
    if not isinstance(old, dict) or not isinstance(new, dict):
        raise ValueError("Package inventory is malformed")
    return {
        "before": len(old),
        "after": len(new),
        "missing_packages": sorted(set(old) - set(new)),
        "new_packages": sorted(set(new) - set(old)),
        "version_changes": sorted(
            name for name in set(old) & set(new) if old[name] != new[name]),
    }


def save(path, value):
    path = Path(path)
    for component in (path, *path.parents):
        if component.is_symlink():
            raise OSError("Refusing symlinked package inventory destination")
        if component == component.parent:
            break
    if path.exists() and not path.is_file():
        raise OSError("Package inventory destination must be a file")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".package-inventory-")
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--snapshot", type=Path, help="Save private installed package baseline")
    ap.add_argument("--compare", type=Path, help="Compare with previous baseline")
    ap.add_argument("--strict", action="store_true",
                    help="Flag any installed baseline package that has disappeared")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if args.strict and not args.compare:
        ap.error("--strict requires --compare")
    packages = snapshot_document(query_installed())
    if args.snapshot:
        save(args.snapshot, packages)
    changes = None
    if args.compare:
        baseline = json.loads(args.compare.read_text(encoding="utf-8"))
        changes = compare(baseline, packages)
    if args.json:
        print(json.dumps({"installed_packages": len(packages["packages"]),
                          "comparison": changes}, indent=2))
    else:
        print("SPIDER OS / UBUNTU STUDIO PACKAGE PRESERVATION")
        print("Installed dpkg packages:", len(packages["packages"]))
        if args.snapshot:
            print("Private pre-install baseline:", args.snapshot)
        if changes is not None:
            print("Missing baseline packages:", len(changes["missing_packages"]))
            for name in changes["missing_packages"]:
                print("  REVIEW PACKAGE:", name)
            print("New installed packages:", len(changes["new_packages"]))
            print("Version-only changes:", len(changes["version_changes"]))
        if args.strict:
            print("PACKAGE PRESERVATION: " + (
                "BLOCKED (missing installed baseline packages)"
                if changes["missing_packages"] else
                "PASS (every baseline installed package still present)"
            ))
        print("Read-only inventory. No packages changed.")
    return 2 if args.strict and changes["missing_packages"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
