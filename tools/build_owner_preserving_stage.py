#!/usr/bin/env python3
"""Stage a LOCAL, owner-first Spider OS candidate without modifying the installed PC.

The 31 unknown/custom files are copied byte-for-byte from an owner-supplied
archive into a separate candidate tree. Every other candidate file comes from
the exact, clean Git commit. This is NOT a semantic merge, executable release,
backup, or installation approval. New features requiring changes to the 31
retained entrypoints remain pending explicit integration and hardware tests.

No owner source is published to GitHub by this program.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import zipfile

REPO = Path(__file__).resolve().parents[1]
INSTALLED = Path("/usr/local/lib/spider-os")
OWNER_FILES = (
    "author/main.py", "author/store.py", "author/web_features.py",
    "the-web/shell/main.py", "the-web/shell/quick_settings.py",
    "the-web/shell/webbie_panel.py", "the-web/shell/webbie_computer_panel.py",
    "the-web/shell/webbie_operator_bridge.py", "the-web/shell/webbie_camera.py",
    "the-web/overlay/webbie_face.py", "webbie/agent/webbie.py",
    "webbie/agent/app_open_route.py", "webbie/voice/interruptible_speech.py",
    "webbie/voice/whisper_listener.py", "webbie/actions/desktop_control.py",
    "webbie/actions/task_grants.py", "webbie/brain/brain.py",
    "author/commands.py", "author/control_socket.py", "forage/engine.py",
    "kali-bay/bin/kali-bay", "kali-bay/ui/kali_bay.py",
    "media/ai-dj/service.py", "studio/ai_panel.py", "studio/main.py",
    "study/course_materials.py", "study/homework_ui.py", "study/study.py",
    "webbie/agent/kali_assistant.py", "the-web/package/reconcile-native.py",
    "kali-bay/package/install-kali-bay.sh",
)
MAX_EACH = 2_000_000
MAX_TOTAL = 16_000_000
SHA_RE = re.compile(r"^[a-f0-9]{40}$")
IMPORTANT = (
    "webbie/agent/webbie.py", "webbie/voice/whisper_listener.py",
    "webbie/brain/brain.py", "media/ai-dj/service.py", "the-web/shell/main.py",
)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def checked_path(root: Path, name: str, *, existing=True) -> Path:
    if not isinstance(name, str) or name.startswith("/"):
        raise ValueError("Unsafe relative file name")
    parts = PurePosixPath(name).parts
    if not parts or any(p in (".", "..", "") for p in name.split("/")):
        raise ValueError("Unsafe relative file name")
    path = Path(root)
    if path.is_symlink():
        raise ValueError("Symlinked source root")
    for part in parts:
        path = path / part
        if path.is_symlink():
            raise ValueError("Symlinked file or parent")
    if existing and not path.is_file():
        raise ValueError("Missing expected source file: " + name)
    return path


def parse_only(name: str, data: bytes):
    if name.endswith(".py"):
        ast.parse(data.decode("utf-8"), filename=name)
    elif name.endswith(".sh") or name == "kali-bay/bin/kali-bay":
        result = subprocess.run(["bash", "-n"], input=data, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=10, check=False)
        if result.returncode:
            raise ValueError("Bash syntax invalid: " + name)
    else:
        raise ValueError("Unsupported owner source type")


def named_api(raw: bytes, name: str) -> list[str]:
    if not name.endswith(".py"):
        return []
    tree = ast.parse(raw.decode("utf-8"), filename=name)
    results = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            results.append(node.name)
        elif isinstance(node, ast.ClassDef):
            results.append(node.name)
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    results.append(node.name + "." + child.name)
    return sorted(set(results))


def load_owner_zip(archive_path: Path) -> dict[str, bytes]:
    expected = set(OWNER_FILES)
    found = {}
    with zipfile.ZipFile(archive_path) as bundle:
        if len(bundle.infolist()) != len(expected):
            raise ValueError("Owner ZIP must contain exactly the 31 reviewed source files")
        total = 0
        for item in bundle.infolist():
            name = item.filename
            if not name.startswith("installed/"):
                raise ValueError("Unexpected ZIP entry")
            relative = name[len("installed/"):]
            if relative not in expected or relative in found:
                raise ValueError("Unrecognized or duplicate owner file")
            # Reject links, directories and special modes. ZIPs from Python's
            # zipfile may omit type bits, so zero type is permitted.
            mode = item.external_attr >> 16
            kind = stat.S_IFMT(mode)
            if item.is_dir() or kind not in (0, stat.S_IFREG):
                raise ValueError("Unsafe ZIP entry type")
            if item.file_size <= 0 or item.file_size > MAX_EACH:
                raise ValueError("Invalid owner source size")
            total += item.file_size
            if total > MAX_TOTAL:
                raise ValueError("Owner archive unexpectedly large")
            raw = bundle.read(item)
            if len(raw) != item.file_size:
                raise ValueError("Truncated owner source")
            parse_only(relative, raw)
            found[relative] = raw
    if set(found) != expected:
        raise ValueError("Missing owner source file")
    return found


def verified_head(source: Path, expected_sha: str) -> list[str]:
    if not SHA_RE.fullmatch(expected_sha):
        raise ValueError("Must provide an exact 40-character expected Git commit")
    def git(*args):
        r = subprocess.run(["git", "-C", str(source), *args], capture_output=True,
                           timeout=20, check=False)
        if r.returncode:
            raise ValueError("Git source verification failed")
        return r.stdout
    actual = git("rev-parse", "--verify", "HEAD").decode().strip()
    if actual != expected_sha:
        raise ValueError("Working checkout does not match the tested SHA")
    if git("status", "--porcelain", "--untracked-files=no").strip():
        raise ValueError("Candidate has modified tracked source")
    names = git("ls-files", "-z").decode("utf-8").split("\0")
    names = [n for n in names if n and not n.startswith(".git/")]
    if not names or len(names) > 10000:
        raise ValueError("Unexpected source inventory")
    if len(names) != len(set(names)):
        raise ValueError("Duplicate source inventory")
    return names


def stage(source: Path, archive: Path, output: Path, expected_sha: str,
          *, installed: Path = INSTALLED, source_names=None) -> dict:
    """Writes only a NEW review directory; no installed or GitHub files changed."""
    source, archive, output, installed = map(lambda p: Path(p).resolve(),
                                              (source, archive, output, installed))
    # Not allowed inside the Git checkout, installed root or archive folder.
    if output == source or source in output.parents or output == installed or installed in output.parents:
        raise ValueError("Staging must be outside both live PC and source checkout")
    if output.exists() or output.is_symlink():
        raise ValueError("Refusing to overwrite an existing review directory")
    sources = verified_head(source, expected_sha) if source_names is None else source_names
    if len(set(sources)) != len(sources):
        raise ValueError("Duplicate tracked source names")
    owners = load_owner_zip(archive)
    differences = []
    for name, raw in owners.items():
        path = checked_path(source, name)
        candidate = path.read_bytes()
        parse_only(name, candidate)
        live = checked_path(installed, name)
        if digest(live.read_bytes()) != digest(raw):
            raise ValueError("Installed PC changed since submitted ZIP: " + name)
        local = set(named_api(raw, name))
        remote = set(named_api(candidate, name))
        differences.append({
            "path": name, "owner_sha256": digest(raw),
            "candidate_sha256": digest(candidate),
            "owner_symbols_absent_in_candidate": sorted(local - remote),
            "candidate_symbols_absent_in_owner": sorted(remote - local),
            "retained": "owner_source_exact_bytes",
            "requires_semantic_review": digest(raw) != digest(candidate),
        })
    # Review not approval. The builder NEVER invokes the central installer.
    output.mkdir(parents=True, mode=0o700)
    target = output / "staged-source"
    try:
        target.mkdir(mode=0o700)
        for name in sources:
            src = checked_path(source, name)
            dest = checked_path(target, name, existing=False)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)
            shutil.copymode(src, dest)
        for name, data in owners.items():
            dest = checked_path(target, name)
            dest.write_bytes(data)
        report = {
            "status": "REVIEW_ONLY_NOT_INSTALLABLE",
            "candidate_commit": expected_sha,
            "preserved_owner_files": len(owners),
            "owner_sources_uploaded_to_github": False,
            "files": sorted(differences, key=lambda x: x["path"]),
            "integration_pending": [
                "Review candidate-only API and class imports before enabling new GUI workflows",
                "Merge missing owner-only functionality selectively, do not replace Webbie",
                "Keep installed qwen3:8b settings and test model service + microphone",
                "Run full source and on-PC app tests on the FINAL combined commit",
                "Owner-confirmed known-good snapshot, rollback, daily receipt and approval required",
            ],
            "result": "31 installed files preserved byte-for-byte only in staging. "
                      "New candidate modules remain available, but features depending on "
                      "candidate replacements are NOT assumed integrated.",
        }
        with (output / "reconciliation.json").open("x", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
            f.write("\n")
    except BaseException:
        shutil.rmtree(output)
        raise
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, default=REPO)
    p.add_argument("--owner-archive", type=Path, required=True)
    p.add_argument("--installed-root", type=Path, default=INSTALLED)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--expected-commit", required=True)
    args = p.parse_args(argv)
    try:
        report = stage(args.source, args.owner_archive, args.output,
                       args.expected_commit, installed=args.installed_root)
    except (OSError, ValueError, SyntaxError, UnicodeError, zipfile.BadZipFile,
            subprocess.TimeoutExpired) as exc:
        print("RECONCILIATION STAGING BLOCKED:", type(exc).__name__, str(exc)[:300],
              file=sys.stderr)
        return 3
    print("STAGED REVIEW ONLY:", args.output)
    print("Owner files preserved:", report["preserved_owner_files"])
    print("NO INSTALL, NO SERVICE RESTART, NO GITHUB UPLOAD; NOT RELEASE APPROVED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
