#!/usr/bin/env python3
"""Compare public Spider OS program files against an installed system.

Read-only: no package operations, network access, user files, or secret collection.
Only paths tracked in the repository's explicit Spider OS program directories
are examined. Run on the Spider OS PC from a local clone of the intended branch.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

COMPONENTS = (
    "spider-core", "webbie", "forage", "the-web", "kali-bay",
    "study", "media", "system", "studio", "author", "branding",
    "spider_max_source",
)


def tracked_paths(repository: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z", "--", *COMPONENTS],
        cwd=repository, check=True, capture_output=True,
    )
    return [
        Path(p.decode("utf-8", errors="surrogateescape"))
        for p in result.stdout.split(b"\x00") if p
    ]


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def audit(repository: Path, installed_root: Path) -> dict:
    """Report only already-public tracked paths, never unknown installed files."""
    expected = tracked_paths(repository)
    changed, absent, matching = [], [], 0
    counts = {name: {"matching": 0, "changed": 0, "missing": 0}
              for name in COMPONENTS}
    for relative in expected:
        name = relative.parts[0]
        if name not in counts:
            continue
        source = repository / relative
        destination = installed_root / relative
        # Do not follow a symlink out of the installed root.
        if destination.is_symlink() or not destination.is_file():
            absent.append(relative.as_posix())
            counts[name]["missing"] += 1
        elif not source.is_file() or digest(source) != digest(destination):
            changed.append(relative.as_posix())
            counts[name]["changed"] += 1
        else:
            matching += 1
            counts[name]["matching"] += 1
    return {
        "reference": "checked-out local Git revision, not automatically GitHub main",
        "total_tracked": len(expected),
        "matching": matching,
        "changed": changed,
        "missing": absent,
        "components": counts,
        "note": "Installed-only and untracked files are intentionally not enumerated; no data was uploaded.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path,
                        default=Path(__file__).resolve().parents[1])
    parser.add_argument("--installed-root", type=Path,
                        default=Path("/usr/local/lib/spider-os"))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true",
                        help="Return an error if tracked source differs from installed code")
    args = parser.parse_args(argv)
    repository = args.repository.resolve()
    root = args.installed_root.resolve()
    try:
        result = audit(repository, root)
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"Unable to complete read-only audit: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Tracked files: {result['total_tracked']}; "
              f"matching: {result['matching']}; "
              f"changed: {len(result['changed'])}; "
              f"missing: {len(result['missing'])}")
        for component, statuses in result["components"].items():
            if sum(statuses.values()):
                print(f"  {component}: {statuses}")
        for state in ("changed", "missing"):
            for relative in result[state]:
                print(f"  {state.upper()}: {relative}")
        print(result["note"])
    return 1 if args.strict and (result["changed"] or result["missing"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
