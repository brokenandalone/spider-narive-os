#!/usr/bin/env python3
"""Stage a PRIVATE, NON-INSTALLING Spider OS source reconciliation review.

The owner's local program files and the incoming GitHub candidate remain
unchanged. This prepares paired copies and diffs for a small named bay group,
not a merged executable build. Neither stage nor review authorizes apply.
It does not enumerate personal documents, models, music or credentials.

IMPORTANT: staged copies include local source code; keep them PRIVATE.
"""
from __future__ import annotations

import argparse
import ast
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

FOCI = {
    # Existing native-bay integration files only. No standalone Studio project
    # source; this compares owner-installed files without installing anything.
    "native-bays": (
        "the-web/shell/home_dashboard.py",
        "the-web/shell/bay_missions.py",
        "the-web/shell/bay_mission_panel.py",
        "the-web/shell/native_utility_bays.py",
        "the-web/shell/art_workbench.py",
        "the-web/shell/webbie_research_panel.py",
        "the-web/shell/immersive_bays.py",
    ),
    "desktop": (
        "the-web/shell/main.py",
        "the-web/shell/app_catalog.py",
        "the-web/shell/workspace_files.py",
        "the-web/shell/webbie_panel.py",
        "the-web/shell/webbie_cognitive_center.py",
    ),
    "webbie": (
        "webbie/agent/webbie.py",
        "webbie/brain/brain.py",
        "webbie/voice/whisper_listener.py",
        "webbie/voice/interruptible_speech.py",
        "the-web/shell/webbie_computer_panel.py",
        "the-web/shell/webbie_operator_bridge.py",
        "the-web/shell/webbie_camera.py",
    ),
    "creative": (
        "studio/main.py", "studio/ai_panel.py",
        "author/main.py", "author/web_features.py",
        "study/study.py", "study/homework_ui.py",
        "forage/engine.py", "forage/forage.py",
        "forage/deep-forage/deep_forage.py",
    ),
    "services": (
        "media/ai-dj/service.py", "media/ai-dj/spider-ai-dj.service",
        "kali-bay/bin/kali-bay", "kali-bay/ui/kali_bay.py",
        "webbie/actions/task_grants.py",
    ),
}
APPROVED_BRANCH = "feature/native-monster-bays-20261015"
MAX_SOURCE_SIZE = 1_000_000

# Binding names inside the candidate's native shell, used for an informative
# integration gap audit. These are NOT patches or inferred merge decisions.
INTEGRATIONS = {
    "the-web/shell/main.py": (
        "from immersive_bays import", "from workspace_max_native import",
        "from home_dashboard import", "from bay_mission_panel import",
        "from webbie_native_operations import", "from webbie_research_panel import",
        "from art_workbench import", "from instrument_panel import",
        "from native_utility_bays import", "from legacy_control_centers import",
    ),
    "studio/main.py": ("from instrument_panel import",),
    "webbie/agent/webbie.py": ("from app_bay_lookup import",),
}


def safe_leaf(root: Path, relative: str) -> Path | None:
    if not relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
        return None
    root = root.resolve()
    candidate = root
    for part in Path(relative).parts:
        candidate = candidate / part
        if candidate.is_symlink():
            return None
    return candidate


def limited_file(path: Path):
    try:
        meta = path.stat()
        if not stat.S_ISREG(meta.st_mode) or meta.st_nlink != 1 or meta.st_size > MAX_SOURCE_SIZE:
            return None
        return path.read_bytes()
    except (OSError, PermissionError):
        return None


def managed_paths(candidate_root: Path):
    release = safe_leaf(candidate_root, "system/release_batch.py")
    if release is None:
        raise ValueError("Unsafe source release path")
    tree = ast.parse(release.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "APP_FILES"
            for target in node.targets
        ):
            paths = ast.literal_eval(node.value)
            if not isinstance(paths, (list, tuple)) or any(
                not isinstance(p, str) or safe_leaf(candidate_root, p) is None
                for p in paths
            ):
                raise ValueError("Unrecognized or unsafe managed release catalog")
            return set(paths)
    raise ValueError("Release manifest lacks APP_FILES")


def summary(local: bytes, incoming: bytes, relative: str):
    report = {
        "component": relative,
        "state": "identical" if local == incoming else "manual_merge_required",
        "installed_sha256": hashlib.sha256(local).hexdigest(),
        "candidate_sha256": hashlib.sha256(incoming).hexdigest(),
        "installed_lines": local.count(b"\n"),
        "candidate_lines": incoming.count(b"\n"),
    }
    if relative.endswith(".py"):
        try:
            old = ast.parse(local.decode("utf-8"))
            new = ast.parse(incoming.decode("utf-8"))
            def topnames(tree):
                return {node.name for node in tree.body
                        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))}
            report["local_only_definitions"] = sorted(topnames(old) - topnames(new))
            report["candidate_only_definitions"] = sorted(topnames(new) - topnames(old))
        except (SyntaxError, UnicodeError):
            report["python_structure"] = "unparseable: inspect locally"
    report["integration_gaps"] = [
        marker for marker in INTEGRATIONS.get(relative, ())
        if marker.encode("utf-8") in incoming and marker.encode("utf-8") not in local
    ]
    return report


def _private_folder(target: Path, *, home: Path, source: Path, installed: Path):
    # Require a new, visible, owner-home destination. Never stage in a Git
    # checkout, system directory or inside the installed native program tree.
    if (not target.is_absolute() or ".." in target.parts or
            target != target.resolve(strict=False)):
        raise ValueError("Review directory must be a normalized absolute path")
    home = home.resolve()
    if target.exists() or target.is_symlink() or home not in target.parents:
        raise ValueError("Choose a NEW review directory inside your home")
    if any(part.startswith(".") for part in target.relative_to(home).parts):
        raise ValueError("Use a visible review directory inside your home")
    if source.resolve() in target.parents or installed.resolve() in target.parents:
        raise ValueError("Review cannot live inside installed or candidate tree")
    item = home
    for part in target.relative_to(home).parts[:-1]:
        item = item / part
        if item.is_symlink():
            raise ValueError("Review parent must not be symlinked")
    parent = target.parent
    if not parent.is_dir() or parent.stat().st_uid != os.getuid():
        raise ValueError("Review parent must be an owner-managed directory")
    target.mkdir(mode=0o700)


def _private_write(root, name, body):
    output = root / name
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    for item in (output, *output.parents):
        if item == root.parent:
            break
        if item.is_symlink():
            raise ValueError("Symlinked review path rejected")
    if isinstance(body, str):
        body = body.encode("utf-8")
    fd = os.open(str(output), os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(body)
        handle.flush()
        os.fsync(handle.fileno())


def stage(source: Path, installed: Path, output: Path, *,
          focus="desktop", home=None, scope=None):
    if focus not in FOCI:
        raise ValueError("Unknown merge focus")
    source = source.resolve()
    installed = installed.resolve()
    if source == installed:
        raise ValueError("Source and installed trees must be different")
    all_paths = managed_paths(source) if scope is None else set(scope)
    result = []
    pairs = []
    for relative in FOCI[focus]:
        if relative not in all_paths:
            raise ValueError("Requested merge file isn't part of guarded release: " + relative)
        candidate = safe_leaf(source, relative)
        live = safe_leaf(installed, relative)
        if candidate is None or live is None:
            raise ValueError("Symlinked source or local file; review separately: " + relative)
        theirs = limited_file(candidate)
        if theirs is None:
            raise ValueError("Missing, oversize or unsafe candidate file: " + relative)
        # New additive modules legitimately have no installed counterpart.
        # Only genuinely absent paths are allowed; unsafe existing files
        # (directories, hardlinks, oversize data) still block staging.
        if not live.exists():
            if live.is_symlink():
                raise ValueError("Symlinked installed file: " + relative)
            result.append({
                "component": relative, "state": "new_candidate_only",
                "installed_sha256": None,
                "candidate_sha256": hashlib.sha256(theirs).hexdigest(),
                "requires_owner_review": True,
            })
            pairs.append((relative, None, theirs))
            continue
        ours = limited_file(live)
        if ours is None:
            raise ValueError("Unsafe existing owner file: " + relative)
        result.append(summary(ours, theirs, relative))
        pairs.append((relative, ours, theirs))
    _private_folder(output, home=Path.home() if home is None else Path(home),
                    source=source, installed=installed)
    for relative, ours, theirs in pairs:
        if ours is not None:
            _private_write(output, "installed/" + relative, ours)
        _private_write(output, "candidate/" + relative, theirs)
        old = (ours or b"").decode("utf-8", "replace").splitlines(keepends=True)
        new = theirs.decode("utf-8", "replace").splitlines(keepends=True)
        patch = "".join(difflib.unified_diff(
            old, new, fromfile="INSTALLED/" + relative,
            tofile="CANDIDATE/" + relative, n=3))
        if len(patch.encode("utf-8")) > 2 * MAX_SOURCE_SIZE:
            patch = "Diff too large; inspect paired copies with Meld locally.\n"
        _private_write(output, "diffs/" + relative + ".diff", patch)
    report = {
        "format": "spider-native-private-merge-stage-v1",
        "focus": focus, "release_installable": False,
        "installed_files_modified": False,
        "contains_private_owner_source": True,
        "warning": "Private LOCAL REVIEW ONLY. Never upload or apply unreviewed patches.",
        "files": result,
    }
    _private_write(output, "manifest.json", json.dumps(report, indent=2) + "\n")
    _private_write(output, "README.txt", (
        "SPIDER OS PRIVATE CODE REVIEW\n"
        "This directory contains copies of the owner's current installed code.\n"
        "KEEP PRIVATE. Do not upload this directory to GitHub or ChatGPT.\n"
        "Compare pairs with Meld, preserving all local behavior.\n"
        "Nothing has been merged or installed; no services were restarted.\n"
        "The guarded release remains BLOCKED until all customized files have\n"
        "been reconciled, source tested and rollback validated.\n"))
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--installed-root", type=Path, default=Path("/usr/local/lib/spider-os"))
    p.add_argument("--focus", choices=sorted(FOCI), default="desktop")
    p.add_argument("--output", type=Path, required=True,
                   help="NEW private visible directory in owner HOME (local only)")
    args = p.parse_args(argv)
    source = args.source.resolve()
    branch = subprocess.run(
        ["git", "-C", str(source), "branch", "--show-current"],
        capture_output=True, text=True, check=True, timeout=8,
    ).stdout.strip()
    if branch != APPROVED_BRANCH:
        p.error("Refusing unapproved branch: " + (branch or "detached"))
    try:
        report = stage(source, args.installed_root, args.output.expanduser(),
                       focus=args.focus)
    except (OSError, ValueError, SyntaxError) as error:
        print("Private reconciliation staging stopped: " + str(error), file=sys.stderr)
        return 3
    print("SPIDER OS PRIVATE NATIVE MERGE STAGING / " + args.focus.upper())
    print("Paired files:", len(report["files"]))
    for entry in report["files"]:
        print("REVIEW:", entry["component"], "|", entry["state"])
        print("  Local-only definitions:",
              ", ".join(entry.get("local_only_definitions", [])[:8]) or "none")
        print("  Candidate-only definitions:",
              ", ".join(entry.get("candidate_only_definitions", [])[:8]) or "none")
        print("  Missing native imports:", len(entry.get("integration_gaps", [])))
        for marker in entry["integration_gaps"]:
            print("    NEEDS MERGE:", marker)
    print("Private folder:", args.output)
    print("Local installed files untouched; no automatic merge performed.")
    print("GUARDED INSTALL REMAINS BLOCKED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
