#!/usr/bin/env python3
"""Read a LOCAL installed-truth manifest and prioritize actual source drift.

No writes, file copying, Git staging, credentials, network, or service changes.
Labels are advisory: a path name cannot prove whether its contents are safe.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path, PurePosixPath
import sys

VENDORED_DEPENDENCY_ROOTS = ("webbie/vendor/numpy/", "webbie/vendor/sherpa_onnx/")
RECOVERY_PREFIXES = (
    "upgrade-backups", "backup-", "backups", "webbie.backup-",
    ".webbie-jarvis-recovery-backups", "previous-versions", "rollback-",
)
DEVELOPMENT_ROOTS = frozenset({
    ".github", "tests", "distro", "tools",
})
GENERATED_FILES = frozenset({
    "install-receipt.json", "manifest.json", "state.json",
    "status.json", "memory.json", "voice-profiles.json",
})
GENERATED_ROOTS = frozenset({
    "__pycache__", "cache", "logs", "log", "tmp", "temp",
    "state", "sessions", "recordings",
})


def category(path: str, group: str) -> str:
    parts = PurePosixPath(path).parts
    if (not parts or path.startswith("/") or ".." in parts
            or "\x00" in path or "\\" in path):
        return "unsafe_name"
    if any(path.startswith(root) for root in VENDORED_DEPENDENCY_ROOTS):
        return "third_party_vendor"
    if any(
        part.startswith(RECOVERY_PREFIXES)
        or part.endswith((".bak", ".orig", ".old", ".backup"))
        or ".backup-" in part
        for part in parts
    ):
        return "recovery_likely"
    if parts[-1].lower() in GENERATED_FILES or any(
        part.lower() in GENERATED_ROOTS for part in parts[:-1]
    ):
        return "runtime_or_sensitive_review"
    if group == "repo_only" and parts[0] in DEVELOPMENT_ROOTS:
        return "development_only"
    return "review_source"


def scopes(paths: list[str], depth: int) -> list[tuple[str, int]]:
    return Counter("/".join(PurePosixPath(p).parts[:depth])
                   for p in paths).most_common()


def display_group(group: str, paths: list[str], limit: int) -> None:
    classified = {p: category(p, group) for p in paths}
    counts = Counter(classified.values())
    print(f"\n## {group}: {len(paths)} paths")
    print("Categories (advisory, never auto-sync): " +
          ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    print("Top root folders: " +
          ", ".join(f"{p}={n}" for p, n in scopes(paths, 1)[:15]))
    review = [p for p in paths if classified[p] == "review_source"]
    print("Review-source folders, depth 3: " +
          ", ".join(f"{p}={n}" for p, n in scopes(review, 3)[:25]))
    print(f"Review-source paths (first {limit} of {len(review)}):")
    for path in review[:limit]:
        print(f"  {path}")
    if len(review) > limit:
        print(f"  ... {len(review) - limit} more are in the local manifest")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest", type=Path,
        default=Path.home() / "Downloads" / "Spider_OS_Installed_Truth" / "manifest.json",
    )
    parser.add_argument("--limit", type=int, default=55)
    args = parser.parse_args()
    if args.limit < 0 or args.limit > 200:
        parser.error("--limit must be between 0 and 200")
    try:
        raw = json.loads(args.manifest.read_text(encoding="utf-8"))
        groups = raw["groups"]
        if not isinstance(groups, dict):
            raise ValueError("Missing groups object")
        for k in ("identical", "different", "installed_only", "repo_only"):
            if not isinstance(groups.get(k), list) or not all(
                isinstance(p, str) for p in groups[k]
            ):
                raise ValueError(f"Invalid group {k}")
    except (OSError, ValueError, KeyError) as error:
        print(f"Unable to read local audit: {error}", file=sys.stderr)
        return 1

    print("SPIDER OS INSTALLED-TRUTH TRIAGE (READ-ONLY)")
    print("GitHub revision in the existing report:", raw.get("repo_commit", "unknown"))
    print("No new file inventory, code uploads, or installation actions.")
    for k in ("different", "installed_only", "repo_only"):
        display_group(k, groups[k], args.limit)
    print("\nNEXT: review and reconcile changed source; never promote backup")
    print("snapshots or private runtime files into a PUBLIC repository.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
