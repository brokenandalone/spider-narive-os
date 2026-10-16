#!/usr/bin/env python3
"""Stage exact owner-installed Spider OS source inside a separate Git checkout.

Default is a read-only verified plan. --apply updates ONLY the source checkout:
no services, installation roots, git commits, pushes, or machine configuration.
Every replacement must still match its original audit SHA-256 and pass safety
checks. The public GitHub repository requires explicit owner review before push.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile

from installed_truth_triage import category

BRANCH = "rebuild/spider-os-installed-truth-20261016"
ALLOWED_UNTRACKED_SOURCE = frozenset({
    "branding/apply-spider-branding.sh",
    "studio/studio.py",
    "system/daily_install_policy.py",
    "webbie/agent/webbie_ai_isolation.py",
    "webbie/agent/webbie_ai_worker.py",
    "webbie/agent/webbie_brain_primary.py",
    "webbie/agent/webbie_ops.py",
    "webbie/voice/speaker_gate.py",
})
ALLOWED_EXTENSIONS = frozenset({
    ".py", ".sh", ".json", ".yaml", ".yml", ".toml", ".ini",
    ".conf", ".service", ".desktop", ".qss", ".css", ".qml",
})
# Reject obvious credentials before a source file enters a public repo checkout.
# Not a substitute for human review: semantic and hidden secrets are possible.
SENSITIVE_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"(?im)^\s*(?:password|api_key|secret_key|access_token|auth_token)\s*[:=]\s*['\"][^'\"]{12,}['\"]"),
)
MAX_BYTES = 16 * 1024 * 1024


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def checked_rel(rel: str) -> Path:
    p = PurePosixPath(rel)
    if (not rel or rel.startswith("/") or "\\" in rel or "\x00" in rel
            or any(s in ("..", ".") for s in p.parts)
            or any(":" in s for s in p.parts)):
        raise ValueError(f"Unsafe path: {rel!r}")
    return Path(*p.parts)


def read_regular(root: Path, rel: str, allow_missing: bool = False) -> bytes | None:
    p = checked_rel(rel)
    base = root.resolve(strict=True)
    current = base
    for part in p.parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"Symlinked directory refused: {rel}")
    dest = base / p
    if not dest.exists() and not dest.is_symlink():
        if allow_missing:
            return None
        raise ValueError(f"Missing required source: {rel}")
    meta = dest.lstat()
    if not stat.S_ISREG(meta.st_mode) or meta.st_size > MAX_BYTES:
        raise ValueError(f"Nonregular or oversized source: {rel}")
    contents = dest.read_bytes()
    if len(contents) != meta.st_size:
        raise ValueError(f"Source changed while reading: {rel}")
    return contents


def check_git(repo: Path) -> None:
    branch = subprocess.run(
        ["git", "-C", str(repo), "branch", "--show-current"],
        text=True, capture_output=True, check=True,
    ).stdout.strip()
    if branch != BRANCH:
        raise ValueError(f"Refusing to modify branch {branch!r}; expected {BRANCH}")
    status = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=all"],
        text=True, capture_output=True, check=True,
    ).stdout
    if status.strip():
        raise ValueError("Git source checkout is not clean; refusing an automatic overlay")


def validate_source(rel: str, contents: bytes) -> None:
    p = checked_rel(rel)
    if p.suffix.lower() not in ALLOWED_EXTENSIONS and p.name != "kali-bay":
        raise ValueError(f"Unexpected source file extension: {rel}")
    try:
        value = contents.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ValueError(f"Non-UTF-8 source excluded: {rel}") from e
    for pat in SENSITIVE_PATTERNS:
        if pat.search(value):
            raise ValueError(f"Potential embedded credential found; manual review required: {rel}")
    if p.suffix == ".py":
        try:
            compile(value, rel, "exec")
        except SyntaxError as error:
            raise ValueError(f"Python syntax failed for {rel}: {error}") from error
    elif p.suffix == ".json":
        try:
            json.loads(value)
        except ValueError as error:
            raise ValueError(f"JSON syntax failed for {rel}: {error}") from error


def get_manifest(path: Path) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    for field in ("groups", "installed_sha256", "git_sha256"):
        if not isinstance(raw.get(field), dict):
            raise ValueError(f"Malformed manifest field {field}")
    if len(raw["groups"].get("different", [])) > 200:
        raise ValueError("Unexpectedly large source change set; rerun audit")
    if len(raw["groups"].get("installed_only", [])) > 20000:
        raise ValueError("Unexpectedly large installed-only inventory")
    return raw


def select_paths(manifest: dict) -> tuple[list[str], list[str]]:
    changed = manifest["groups"]["different"]
    unique = manifest["groups"]["installed_only"]
    if len(changed) != len(set(changed)) or len(unique) != len(set(unique)):
        raise ValueError("Repeated filenames in audit manifest")
    chosen_changed = []
    for rel in changed:
        checked_rel(rel)
        if category(rel, "different") != "review_source":
            raise ValueError(f"Unexpected changed source category: {rel}")
        chosen_changed.append(rel)
    chosen_unique = []
    for rel in unique:
        checked_rel(rel)
        if rel in ALLOWED_UNTRACKED_SOURCE:
            chosen_unique.append(rel)
    return sorted(chosen_changed), sorted(chosen_unique)


def prepare(repo: Path, installed: Path, manifest: dict) -> list[tuple[str, bytes, int]]:
    different, unique = select_paths(manifest)
    entries = []
    for rel in different + unique:
        source = installed / checked_rel(rel)
        content = read_regular(installed, rel)
        assert content is not None
        expected = manifest["installed_sha256"].get(rel)
        if not isinstance(expected, dict) or sha(content) != expected.get("sha256"):
            raise ValueError(f"Installed source changed after original audit: {rel}")
        original = read_regular(repo, rel, allow_missing=rel in unique)
        if rel in different:
            baseline = manifest["git_sha256"].get(rel)
            if (not isinstance(baseline, dict) or original is None
                    or sha(original) != baseline.get("sha256")):
                raise ValueError(f"Git source changed after original audit: {rel}")
        elif original is not None:
            raise ValueError(f"Owner-only source path already exists in Git: {rel}")
        validate_source(rel, content)
        entries.append((rel, content, stat.S_IMODE(source.lstat().st_mode)))
    return entries


def install_checkout_only(repo: Path, entries: list[tuple[str, bytes, int]]) -> None:
    """Atomic per-file writes to clone, restoring prior checkout on error."""
    previous: list[tuple[Path, bytes | None, int | None]] = []
    try:
        for rel, data, mode in entries:
            target = repo / checked_rel(rel)
            before = read_regular(repo, rel, allow_missing=True)
            old_mode = stat.S_IMODE(target.lstat().st_mode) if before is not None else None
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.is_symlink():
                raise ValueError(f"Symlink destination refused: {rel}")
            fd, tmp = tempfile.mkstemp(prefix=".spider-reconcile-", dir=target.parent)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.chmod(tmp, 0o755 if (mode & 0o111) else 0o644)
                os.replace(tmp, target)
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)
            previous.append((target, before, old_mode))
    except Exception:
        for dest, old, old_mode in reversed(previous):
            if old is None:
                dest.unlink(missing_ok=True)
            else:
                fd, tmp = tempfile.mkstemp(prefix=".spider-restore-", dir=dest.parent)
                try:
                    with os.fdopen(fd, "wb") as stream:
                        stream.write(old)
                    os.chmod(tmp, old_mode or 0o644)
                    os.replace(tmp, dest)
                finally:
                    if os.path.exists(tmp):
                        os.unlink(tmp)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--installed-root", type=Path, default=Path("/usr/local/lib/spider-os"))
    parser.add_argument("--manifest", type=Path, default=Path.home() / "Downloads"
                        / "Spider_OS_Installed_Truth" / "manifest.json")
    parser.add_argument("--apply", action="store_true", help="Copy vetted source into the Git checkout ONLY")
    args = parser.parse_args()
    try:
        repo, installed = args.repo.resolve(strict=True), args.installed_root.resolve(strict=True)
        if repo == installed or repo.is_relative_to(installed) or installed.is_relative_to(repo):
            raise ValueError("Git checkout and installed source root must be separate")
        check_git(repo)
        manifest = get_manifest(args.manifest)
        entries = prepare(repo, installed, manifest)
        changed, unique = select_paths(manifest)
        print(f"Validated {len(entries)} owner source files: {len(changed)} changed, {len(unique)} owner-only")
        print("Installed root:", installed)
        print("Separate Git checkout:", repo)
        print("All selected hashes match the original audit; source checked for obvious credentials.")
        print("THIS IS NOT A COMPLETE SECRET SCAN. Manual review is required before public push.")
        if args.apply:
            install_checkout_only(repo, entries)
            print("STAGED INSIDE THE GIT WORKING TREE. Nothing installed, committed, or pushed.")
            print("Inspect: git diff --stat; git status --short; git diff --check")
        else:
            print("DRY RUN ONLY. Use --apply for a reviewed local checkout overlay.")
        return 0
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as error:
        print(f"SAFE STOP: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
