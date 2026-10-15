#!/usr/bin/env python3
"""Audit Ubuntu Studio/Spider OS application menu entries before/after release.

Reads only available XDG .desktop file metadata. A missing menu entry does not
automatically mean the program package is removed. No apt/podman commands,
package changes, executable launches, network calls, or private file scans.
"""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "the-web/shell/app_catalog.py"


def catalog_module():
    spec = importlib.util.spec_from_file_location("spider_app_inventory_catalog", CATALOG)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def manifest(apps):
    output = []
    for app in apps:
        try:
            source_sha = hashlib.sha256(Path(app.path).read_bytes()).hexdigest()
        except OSError:
            source_sha = None
        output.append({
            "id": app.desktop_id,
            "name": app.name,
            "bay": app.workspace,
            "source_sha256": source_sha,
        })
    return {"format": "spider-os-xdg-v1",
            "entries": sorted(output, key=lambda item: item["id"])}


def compare(before, after):
    if before.get("format") != "spider-os-xdg-v1":
        raise ValueError("Unknown prior inventory format")
    old = {record["id"]: record for record in before.get("entries", [])}
    new = {record["id"]: record for record in after.get("entries", [])}
    return {
        "before": len(old),
        "after": len(new),
        "missing_menu_entries": sorted(set(old) - set(new)),
        "added_menu_entries": sorted(set(new) - set(old)),
        "reclassified_without_removal": sorted(
            key for key in old.keys() & new.keys()
            if old[key]["bay"] != new[key]["bay"]),
        "changed_desktop_metadata": sorted(
            key for key in old.keys() & new.keys()
            if old[key]["source_sha256"] != new[key]["source_sha256"]),
    }


def save_manifest(path, report):
    path = Path(path)
    for item in (path, *path.parents):
        if item.is_symlink():
            raise OSError("Refusing symlinked inventory destination")
        if item == item.parent:
            break
    if path.exists() and not path.is_file():
        raise OSError("Inventory destination is not a regular file")
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".xdg-apps-",
                                     dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path,
                        help="Write a PRIVATE pre-install manifest; never edit applications")
    parser.add_argument("--compare", type=Path,
                        help="Compare to a previous inventory manifest")
    parser.add_argument("--list", action="store_true",
                        help="List discovered menu applications and their recommended bays")
    parser.add_argument("--strict", action="store_true",
                        help="Exit nonzero when expected XDG menu entries vanish; never change packages")
    parser.add_argument("--json", action="store_true",
                        help="Print machine-readable inventory summary")
    args = parser.parse_args(argv)
    if args.strict and not args.compare:
        parser.error("--strict requires --compare and a saved baseline")
    app_catalog = catalog_module()
    apps = app_catalog.discover_apps(desktops="TheWeb:KDE")
    current = manifest(apps)
    if args.snapshot:
        save_manifest(args.snapshot, current)
    counts = Counter(app.workspace for app in apps)
    report = {
        "available_menu_apps": len(apps),
        "by_bay": dict(sorted(counts.items())),
        "note": ("This is a menu inventory, not a package database. "
                 "Apps with no .desktop entry or disabled menu entries are "
                 "not automatically represented. No app has been uninstalled."),
    }
    if args.compare:
        prior = json.loads(args.compare.read_text(encoding="utf-8"))
        report["comparison"] = compare(prior, current)
        report["comparison"]["changes"] = [
            {"id": old["id"], "name": old["name"], "before": old["bay"],
             "after": next(app["bay"] for app in current["entries"] if app["id"] == old["id"])}
            for old in prior.get("entries", [])
            if old["id"] in report["comparison"]["reclassified_without_removal"]
        ]
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("SPIDER OS | READ-ONLY INSTALLED APP INVENTORY")
        print("Available application menu entries:", len(apps))
        for bay, count in sorted(counts.items()):
            print("  {:<16} {}".format(bay, count))
        if args.snapshot:
            print("Private pre-install inventory:", args.snapshot)
        if args.compare:
            result = report["comparison"]
            print("Missing menu entries (check before install):",
                  len(result["missing_menu_entries"]))
            for entry in result["missing_menu_entries"]:
                print("  REVIEW:", entry)
            print("App category changes:",
                  len(result["reclassified_without_removal"]))
            for item in result["changes"]:
                print("  RELOCATE MENU ENTRY: {} | {} -> {} | {}".format(
                    item["name"], item["before"], item["after"], item["id"]))
            if result["changed_desktop_metadata"]:
                print("Modified desktop entries (review):",
                      ", ".join(result["changed_desktop_metadata"]))
        if args.list:
            for app in apps:
                print("{} | {} | {}".format(app.workspace, app.name, app.desktop_id))
        print(report["note"])
    if args.strict and args.compare:
        result = report["comparison"]
        if result["missing_menu_entries"]:
            print("PRESERVATION GATE: FAIL, missing application menu entries.")
            return 2
        print("PRESERVATION GATE: PASS, all baseline menu entries still available.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
