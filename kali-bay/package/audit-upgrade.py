#!/usr/bin/env python3
"""Strict, read-only Kali Bay source/installed continuity audit.

This tool never installs files, talks to Podman/Distrobox, restarts services,
or creates directories. A changed owner-PC source must be manually reconciled.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import stat

KALI_CORE = (
    "kali-bay/bin/kali-bay",
    "kali-bay/ui/kali_bay.py",
)
NEW_MODULES = (
    "kali-bay/runtime/kali_apps.py",
    "kali-bay/runtime/workspace_store.py",
    "kali-bay/runtime/lab_reports.py",
    "kali-bay/runtime/evidence_fingerprint.py",
    "kali-bay/runtime/evidence_ledger.py",
)
WEBBIE_BRIDGE = ("webbie/agent/kali_assistant.py",)
FILES = KALI_CORE + NEW_MODULES + WEBBIE_BRIDGE


def _file_sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            block = stream.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def _has_link(path, stop):
    """Check all components between stop and path, including target itself."""
    try:
        components = path.relative_to(stop).parts
    except ValueError:
        return True
    parent = stop
    if parent.is_symlink():
        return True
    for name in components:
        parent = parent / name
        if parent.is_symlink():
            return True
    return False


def _kind(path):
    if not path.exists():
        return "missing"
    info = path.stat()
    if stat.S_ISREG(info.st_mode):
        return "file"
    return "not_regular"


def audit(source_root, installed_root):
    source_root = Path(source_root).absolute()
    installed_root = Path(installed_root).absolute()
    rows = []
    blocked = False
    for relative in FILES:
        source = source_root / relative
        target = installed_root / relative
        group = (
            "core" if relative in KALI_CORE
            else "webbie" if relative in WEBBIE_BRIDGE else "module"
        )
        entry = {"file": relative, "group": group}
        if _has_link(source, source_root) or _kind(source) != "file":
            entry["status"] = "blocked_source"
            blocked = True
        elif _has_link(target, installed_root):
            entry["status"] = "blocked_symlink"
            blocked = True
        elif _kind(target) == "missing":
            entry["status"] = (
                "blocked_missing_core" if group == "core" else "new_module"
            )
            blocked |= group == "core"
        elif _kind(target) != "file":
            entry["status"] = "blocked_nonfile"
            blocked = True
        else:
            try:
                entry["source_sha256"] = _file_sha(source)
                entry["installed_sha256"] = _file_sha(target)
            except OSError:
                entry["status"] = "blocked_unreadable"
                blocked = True
            else:
                if entry["source_sha256"] == entry["installed_sha256"]:
                    entry["status"] = "identical"
                else:
                    entry["status"] = "blocked_customized"
                    blocked = True
        rows.append(entry)
    return {
        "safe_for_automatic_replacement": not blocked,
        "source_root": str(source_root),
        "installed_root": str(installed_root),
        "files": rows,
        "note": (
            "Read-only SHA-256 comparison only. A pass does not authorize install, "
            "merge, container setup, service changes or replacing owner files."
        ),
        "webbie_bridge_in_combined_release": True,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Read-only Kali Bay integration audit; no changes performed."
    )
    parser.add_argument("--source-root", type=Path, default=Path(__file__).parents[2])
    parser.add_argument("--installed-root", type=Path,
                        default=Path("/usr/local/lib/spider-os"))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = audit(args.source_root, args.installed_root)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        for item in result["files"]:
            print(f"{item['status'].upper():24s} {item['file']}")
        print(
            "PREFLIGHT " + (
                "SOURCE COMPARISON PASS (installation still gated)"
                if result["safe_for_automatic_replacement"]
                else "BLOCKED: preserve customized/missing files"
            )
        )
    return 0 if result["safe_for_automatic_replacement"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
