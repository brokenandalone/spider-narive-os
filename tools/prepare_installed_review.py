#!/usr/bin/env python3
"""Prepare a PRIVATE review archive of staged owner code. Nothing is uploaded.

The archive is NOT a safe-to-publish artifact: inspect it before sharing.
Uses Git diff plus eight explicitly inventoried extra source files.
Does not copy or modify the installed operating system, commit, or push.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import zipfile

from stage_installed_source import ALLOWED_UNTRACKED_SOURCE, BRANCH, sha

BLOCK_PATTERNS = [
    re.compile(rb"-----BEGIN (?:RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(rb"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(rb"\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}\b"),
    re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
]
MAX_ZIP_INPUT = 4 * 1024 * 1024

def git(repo: Path, *cmd: str) -> bytes:
    return subprocess.check_output(
        ["git", "-C", str(repo), *cmd], stderr=subprocess.PIPE
    )

def make_archive(repo: Path, manifest_path: Path, output: Path) -> dict:
    repo = repo.resolve(strict=True)
    if git(repo, "branch", "--show-current").decode().strip() != BRANCH:
        raise ValueError("Not on the installed-truth rebuild branch")
    if git(repo, "diff", "--check"):
        raise ValueError("Unexpected diff --check output")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    changed = set(manifest["groups"]["different"])
    extra = set(manifest["groups"]["installed_only"]) & ALLOWED_UNTRACKED_SOURCE
    modified = set(filter(None, git(repo, "diff", "--name-only", "-z", "HEAD").decode().split("\0")))
    untracked = set(filter(None, git(repo, "ls-files", "--others", "--exclude-standard", "-z").decode().split("\0")))
    if changed != modified:
        raise ValueError("Staged tracked paths differ from installed-source audit")
    if extra != untracked:
        raise ValueError("Untracked paths differ from eight approved installed files")
    if len(changed) != 39 or len(extra) != 8:
        raise ValueError("Unexpected staging counts (expected 39 changed and 8 extra)")
    patch = git(repo, "diff", "--binary", "--no-ext-diff", "HEAD", "--", *sorted(changed))
    package = {"installed-source.patch": patch}
    for name in sorted(extra):
        dest = repo / name
        if dest.is_symlink() or not dest.is_file():
            raise ValueError(f"Refusing nonregular file: {name}")
        payload = dest.read_bytes()
        expected = manifest["installed_sha256"].get(name, {})
        if sha(payload) != expected.get("sha256"):
            raise ValueError(f"Owner source changed since audit: {name}")
        package[f"new-source/{name}"] = payload
    for key, value in package.items():
        if len(value) > MAX_ZIP_INPUT:
            raise ValueError(f"Review content too large: {key}")
        if any(regex.search(value) for regex in BLOCK_PATTERNS):
            raise ValueError(f"Potential credential in {key}; remove it before packaging")
    if output.is_relative_to(repo):
        raise ValueError("Refusing to generate owner-source archive inside public Git checkout")
    if output.exists():
        raise ValueError(f"Output already exists, refusing overwrite: {output}")
    description = (
        "# SPIDER OS OWNER SOURCE REVIEW (PRIVATE)\n\n"
        "This contains source diff from an owner PC, not a release or a public upload.\n"
        "Review ALL content for tokens, private paths, personal information, embedded\n"
        "configuration and copyright restrictions before sharing or committing.\n"
        "Simple token-pattern screening is incomplete.\n\n"
        f"Changed source paths: {len(changed)}\n"
        f"Additional owner source files: {len(extra)}\n"
        f"Git branch: {BRANCH}\n"
        f"Original audit revision: {manifest['repo_commit']}\n"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    old_umask = os.umask(0o077)
    try:
        with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr("REVIEW_FIRST.txt", description)
            for name, value in package.items():
                z.writestr(name, value)
        output.chmod(0o600)
    finally:
        os.umask(old_umask)
    return {"path": str(output), "changed": len(changed), "extra": len(extra),
            "size": output.stat().st_size, "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--manifest", type=Path,
                        default=Path.home() / "Downloads" / "Spider_OS_Installed_Truth" / "manifest.json")
    parser.add_argument("--output", type=Path,
                        default=Path.home() / "Downloads" / "Spider_OS_Owner_Source_Review_20261016.zip")
    args = parser.parse_args()
    try:
        summary = make_archive(args.repo, args.manifest, args.output)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print(f"SAFE STOP: {exc}", file=sys.stderr)
        return 1
    print("CREATED PRIVATE LOCAL SOURCE REVIEW ARCHIVE")
    print(json.dumps(summary, indent=2))
    print("NOT UPLOADED OR PUSHED. REVIEW FOR SECRETS BEFORE SHARING.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
