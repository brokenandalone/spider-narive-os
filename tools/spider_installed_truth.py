#!/usr/bin/env python3
"""Read-only installed-to-Git source audit. No file sync, no uploads, no installs.

The running Spider OS installation is the authority. This tool hashes selected
source files, skips secret/data directories, and writes only local reports.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

SOURCE_SUFFIXES = frozenset({
    ".py", ".sh", ".service", ".desktop", ".json", ".yaml", ".yml",
    ".toml", ".ini", ".conf", ".svg", ".qss", ".css", ".ui", ".qml",
})
SOURCE_EXACT = frozenset({"kali-bay", "spider-core", "webbie", "spider-guardian", "spider-vault"})
SKIP_DIRS = frozenset({
    ".git", "__pycache__", ".venv", "venv", "node_modules", "build",
    "dist", "backups", ".webbie-jarvis-recovery-backups",
    "music", "artwork", "recordings", "secrets",
    "credentials", "private", ".ollama", ".cache",
})
EXTRA_LOCAL_FILES = (
    "~/.config/systemd/user/webbie.service",
    "~/.config/systemd/user/webbie.service.d/audio-source.conf",
    "~/.config/systemd/user/webbie.service.d/ollama.conf",
    "~/.local/bin/webbie-wait-ollama",
    "/etc/systemd/system/webbie.service",
)
MAX_SOURCE_BYTES = 16 * 1024 * 1024


def source_like(path: Path) -> bool:
    return path.suffix.lower() in SOURCE_SUFFIXES or (
        path.name in SOURCE_EXACT and (
            "bin" in path.parts or "webbie" in path.parts
        )
    )


def digest(path: Path) -> dict | None:
    """Do not follow symlinks and do not read oversized or nonregular files."""
    try:
        meta = path.lstat()
        if not stat.S_ISREG(meta.st_mode) or meta.st_size > MAX_SOURCE_BYTES:
            return None
        h = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                h.update(chunk)
        return {"sha256": h.hexdigest(), "bytes": meta.st_size}
    except (OSError, PermissionError):
        return None


def installed_sources(installed_root: Path) -> tuple[dict, list]:
    entries: dict[str, dict] = {}
    skipped: list[str] = []
    if not installed_root.is_dir():
        raise FileNotFoundError(f"Installed Spider OS directory missing: {installed_root}")
    for base, dirs, files in os.walk(installed_root, followlinks=False):
        base_path = Path(base)
        dirs[:] = sorted(d for d in dirs
                         if d not in SKIP_DIRS and not (base_path / d).is_symlink())
        for filename in sorted(files):
            current = base_path / filename
            if not source_like(current):
                continue
            rel = current.relative_to(installed_root).as_posix()
            result = digest(current)
            if result is None:
                skipped.append(rel)
            else:
                entries[rel] = result
    return entries, skipped


def tracked_sources(repo: Path) -> dict[str, dict]:
    if not (repo / ".git").exists():
        # A worktree may have a .git file, hence exists rather than is_dir.
        raise RuntimeError(f"Not a Git checkout: {repo}")
    completed = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "-z"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
    )
    entries = {}
    for raw in completed.stdout.split(b"\0"):
        if not raw:
            continue
        rel = os.fsdecode(raw)
        path = Path(rel)
        if not source_like(path) or any(x in SKIP_DIRS for x in path.parts):
            continue
        result = digest(repo / path)
        if result is not None:
            entries[path.as_posix()] = result
    return entries


def compare(installed: dict, tracked: dict) -> dict[str, list[str]]:
    groups = {"identical": [], "different": [], "installed_only": [], "repo_only": []}
    for rel in sorted(set(installed) | set(tracked)):
        if rel not in tracked:
            groups["installed_only"].append(rel)
        elif rel not in installed:
            groups["repo_only"].append(rel)
        elif installed[rel]["sha256"] == tracked[rel]["sha256"]:
            groups["identical"].append(rel)
        else:
            groups["different"].append(rel)
    return groups


def local_service_fingerprints() -> dict:
    result = {}
    for name in EXTRA_LOCAL_FILES:
        path = Path(name).expanduser()
        result[name] = digest(path) if path.exists() else None
    return result


def make_report(installed_root: Path, repo: Path, out: Path) -> dict:
    installed, skipped = installed_sources(installed_root)
    tracked = tracked_sources(repo)
    groups = compare(installed, tracked)
    branch = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--abbrev-ref", "HEAD"],
        text=True, capture_output=True, check=True,
    ).stdout.strip()
    revision = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        text=True, capture_output=True, check=True,
    ).stdout.strip()

    result = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "repo_branch": branch,
        "repo_commit": revision,
        "installed_root": str(installed_root),
        "authoritative_source": "owner's currently installed Spider OS (not automatically uploaded)",
        "groups": groups,
        "installed_sha256": installed,
        "git_sha256": tracked,
        "skipped": skipped,
        "service_file_fingerprints": local_service_fingerprints(),
    }
    out.mkdir(parents=True, exist_ok=True)
    # Owner-only because even filename metadata may be sensitive.
    os.chmod(out, 0o700)
    manifest = out / "manifest.json"
    manifest.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    manifest.chmod(0o600)

    summary = [
        "# Spider OS installed-source reconciliation (LOCAL, NOT UPLOADED)",
        "",
        f"GitHub checkout branch: `{branch}`",
        f"Git commit: `{revision}`",
        "",
        "| Classification | Files |",
        "|---|---:|",
    ]
    for key in groups:
        summary.append(f"| {key} | {len(groups[key])} |")
    summary += [
        f"| skipped_symlinks_or_unreadable_or_oversized | {len(skipped)} |",
        "",
        "**IMPORTANT:** This is a comparison, not an installer, backup, or proof of runtime compatibility.",
        "Never push manifest.json or any private local files to the public GitHub repo.",
        "",
        "## First discrepancies by installed subsystem",
        "",
    ]
    for key in ("different", "installed_only", "repo_only"):
        summary += [f"### {key} ({len(groups[key])})"]
        counts = Counter(path.split("/", 1)[0] for path in groups[key])
        summary.append("By subsystem: " + (
            ", ".join(f"{name}={count}" for name, count in counts.most_common(30))
            if counts else "none"
        ))
        summary += ["", "First 25 paths:"]
        summary += [f"- `{name}`" for name in groups[key][:25]]
        summary.append("")
    summary += [
        "## Required next steps",
        "1. Inspect mismatches and installed-only source **locally**.",
        "2. Review actual private/secret/owner files before copying any source.",
        "3. Bring reviewed source into GitHub through separate commits, never overwrite installed code.",
        "4. Validate Webbie AI V2/Natasha, native bays, Kali and Nova on the PC before release.",
    ]
    p = out / "SUMMARY.md"
    p.write_text("\n".join(summary) + "\n", encoding="utf-8")
    p.chmod(0o600)
    return {"output": str(out), "branch": branch, "counts": {
        k: len(v) for k, v in groups.items()
    }, "skipped": len(skipped)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installed-root", type=Path,
                        default=Path("/usr/local/lib/spider-os"))
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=Path.home() / "Downloads" / "Spider_OS_Installed_Truth")
    args = parser.parse_args()
    try:
        result = make_report(args.installed_root, args.repo, args.output)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Audit failed safely: {error}", file=sys.stderr)
        return 1
    print("SPIDER OS INSTALLED-TRUTH AUDIT (READ ONLY)")
    print("Git branch:", result["branch"])
    for key, count in result["counts"].items():
        print(f"{key}: {count}")
    print("Skipped:", result["skipped"])
    print("Local report:", result["output"])
    print("No files installed, copied to GitHub, or changed on the PC.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
