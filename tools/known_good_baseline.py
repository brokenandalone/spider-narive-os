#!/usr/bin/env python3
"""Spider OS known-good fingerprint and ongoing anti-regression lock.

Capture ONLY after the owner has tested a WORKING PC. This does not back up
files (the transaction installer does that), authorize upgrades, or start
services. It records SHA-256 for fixed installed application paths and the
configured local Ollama chat-model name. Never stores code, chats, passwords,
transcripts, voiceprints, recordings, HOME files or service environments.
A subsequent release is blocked if installed code drifted since that snapshot
or would omit a previously working module. New source differences still need
independent owner review and full physical tests.
"""
from __future__ import annotations
import argparse
import ast
from datetime import datetime, timezone
import getpass
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import secrets
import stat
import sys

REPO = Path(__file__).resolve().parents[1]
INSTALLED = Path("/usr/local/lib/spider-os")
MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,99}$")
FILE_RE = re.compile(r"^known-good-\d{8}T\d{6}-[0-9a-f]{8}\.json$")
MAX_BYTES = 16 * 1024 * 1024
MAX_MANIFEST = 1000


def owner_home():
    user = os.environ.get("SUDO_USER") or getpass.getuser()
    return Path(pwd.getpwnam(user).pw_dir)


def default_snapshots():
    return owner_home() / ".local/state/spider-os/known-good"


def file_path(root, relative):
    if not isinstance(relative, str) or not relative or relative.startswith("/"):
        raise ValueError("Unsafe tracked path")
    chunks = relative.split("/")
    if any(x in ("", ".", "..") for x in chunks):
        raise ValueError("Unsafe tracked path")
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Untrusted Spider OS root")
    item = root
    for part in chunks:
        item = item / part
        if item.is_symlink():
            raise ValueError("Symlinked tracked path")
    if not item.is_file():
        return None
    st = item.stat()
    if not stat.S_ISREG(st.st_mode) or st.st_size > MAX_BYTES or st.st_size == 0:
        raise ValueError("Unsafe tracked file")
    return item


def sha256(file):
    h = hashlib.sha256()
    with file.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def installed_model(root):
    path = file_path(root, "webbie/config/default.json")
    if path is None or path.stat().st_size > 32768:
        raise ValueError("Installed Webbie model config cannot be verified")
    obj = json.loads(path.read_text(encoding="utf-8"))
    ollama = obj.get("ollama") if isinstance(obj, dict) else None
    model = ollama.get("model") if isinstance(ollama, dict) else None
    if not isinstance(model, str) or not MODEL_RE.fullmatch(model):
        raise ValueError("Selected installed chat model is not explicit")
    return model


def manifest(repo):
    path = file_path(repo, "system/release_batch.py")
    if path is None:
        raise ValueError("Central installer missing")
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "APP_FILES" for t in node.targets
        ):
            paths = ast.literal_eval(node.value)
            if (not isinstance(paths, (list, tuple)) or
                not 1 <= len(paths) <= MAX_MANIFEST or
                len(set(paths)) != len(paths)):
                raise ValueError("Invalid tracked installer paths")
            for relative in paths:
                if not isinstance(relative, str) or relative.startswith(("webbie/config/", "webbie/models/")):
                    raise ValueError("Protected or invalid installer entry")
                # Verify structure before filesystem checks.
                if relative.startswith("/") or any(p in ("", ".", "..") for p in relative.split("/")):
                    raise ValueError("Unsafe installer path")
            return tuple(paths)
    raise ValueError("No tracked installer manifest")


def _trusted_snapshot_dir(folder, *, create=False, uid=None):
    folder = Path(folder)
    if create:
        folder.mkdir(parents=True, mode=0o700, exist_ok=True)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("Known-good snapshot directory is missing or unsafe")
    st = folder.stat()
    uid = os.getuid() if uid is None else uid
    if st.st_uid != uid or st.st_mode & 0o077:
        raise ValueError("Snapshot directory must be owner-only")
    return folder


def capture(*, repo=REPO, installed=INSTALLED, folder=None,
            confirmed=False, clock=None):
    if confirmed is not True:
        raise ValueError("Owner must confirm real PC works before recording golden state")
    if os.geteuid() == 0:
        raise ValueError("Run snapshot capture as the normal desktop user, without sudo")
    paths = manifest(repo)
    model = installed_model(installed)
    contents = {}
    for relative in paths:
        existing = file_path(installed, relative)
        contents[relative] = sha256(existing) if existing is not None else None
    if not any(v for v in contents.values()):
        raise ValueError("No installed source matched the expected Spider OS system")
    folder = _trusted_snapshot_dir(default_snapshots() if folder is None else folder, create=True)
    moment = (clock or (lambda: datetime.now(timezone.utc)))()
    if moment.tzinfo is None:
        raise ValueError("Snapshot clock must include timezone")
    filename = "known-good-" + moment.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + secrets.token_hex(4) + ".json"
    payload = {"schema": 1, "created_utc": moment.isoformat(),
               "chat_model": model, "files": contents,
               "manual_working_state_confirmed": True,
               "notes": "Manual owner sign-off only; not proof of live voice/model quality."}
    fd = os.open(folder / filename, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as dest:
            json.dump(payload, dest, sort_keys=True, indent=2)
            dest.write("\n")
            dest.flush()
            os.fsync(dest.fileno())
    except Exception:
        (folder / filename).unlink(missing_ok=True)
        raise
    return {"status": "CAPTURED_AFTER_MANUAL_CONFIRMATION",
            "snapshot": filename, "installed_chat_model": model,
            "tracked_files": len(contents)}


def latest_snapshot(folder, *, uid=None):
    folder = _trusted_snapshot_dir(folder, uid=uid)
    entries = sorted(p for p in folder.iterdir() if FILE_RE.fullmatch(p.name))
    if not entries:
        raise ValueError("No owner-confirmed working PC snapshot exists")
    path = entries[-1]
    if path.is_symlink() or not path.is_file():
        raise ValueError("Untrusted known-good snapshot")
    st = path.stat()
    uid = os.getuid() if uid is None else uid
    if st.st_uid != uid or st.st_mode & 0o077 or not 0 < st.st_size <= 150000:
        raise ValueError("Known-good snapshot permissions/content unsafe")
    data = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(data, dict) or data.get("schema") != 1 or
        data.get("manual_working_state_confirmed") is not True or
        not isinstance(data.get("files"), dict) or
        not isinstance(data.get("chat_model"), str) or
        not MODEL_RE.fullmatch(data["chat_model"])):
        raise ValueError("Unrecognized known-good snapshot format")
    values = data["files"]
    if not values or len(values) > MAX_MANIFEST or any(
        not isinstance(k, str) or
        (v is not None and (not isinstance(v, str) or not re.fullmatch("[a-f0-9]{64}", v)))
        for k, v in values.items()
    ):
        raise ValueError("Corrupt known-good path inventory")
    return data


def verify(*, repo=REPO, installed=INSTALLED, folder=None, uid=None):
    """Fail closed if the PC changed since its last manually approved state."""
    problems, changes = [], []
    try:
        expected = latest_snapshot(default_snapshots() if folder is None else folder, uid=uid)
        paths = manifest(repo)
        model = installed_model(installed)
    except (OSError, ValueError, UnicodeError, TypeError, json.JSONDecodeError) as error:
        return {"status": "BLOCKED", "blockers": ["Known-good state unavailable: " + type(error).__name__],
                "candidate_changes": [], "model_preserved": False}
    baseline = expected["files"]
    if model != expected["chat_model"]:
        problems.append("Installed Webbie chat model changed since last known-good state")
    for relative in baseline:
        if relative not in paths:
            problems.append("Candidate omitted working module: " + relative)
    for relative in paths:
        try:
            current = file_path(installed, relative)
            current_hash = sha256(current) if current is not None else None
            if relative not in baseline:
                if current_hash is not None:
                    problems.append("Newly installed module not in known-good record: " + relative)
                else:
                    changes.append(relative)
                continue
            if current_hash != baseline[relative]:
                problems.append("Live PC source drifted since last known-good: " + relative)
                continue
            candidate = file_path(repo, relative)
            if candidate is None:
                problems.append("Candidate source missing: " + relative)
            elif sha256(candidate) != current_hash:
                changes.append(relative)
        except (OSError, ValueError, TypeError):
            problems.append("Unsafe installed or candidate module: " + relative)
    return {
        "status": "BLOCKED" if problems else "REVIEW_REQUIRED",
        "blockers": sorted(set(problems)), "candidate_changes": sorted(set(changes)),
        "model_preserved": model == expected["chat_model"],
        "captured_model": expected["chat_model"],
        "live_model": model,
        "tracked_modules": len(paths),
        "explanation": ("This is a continuity lock, not approval of changes. "
                        "Review every candidate difference and physically test voice/GUI before install.")
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    cmd = p.add_mutually_exclusive_group(required=True)
    cmd.add_argument("--capture", action="store_true")
    cmd.add_argument("--verify", action="store_true")
    p.add_argument("--confirmed-working", action="store_true",
                   help="Owner confirms real voice, chat, apps and Nova work before recording snapshot")
    p.add_argument("--source", type=Path, default=REPO)
    p.add_argument("--installed", type=Path, default=INSTALLED)
    p.add_argument("--snapshots", type=Path)
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    try:
        report = (capture(repo=args.source, installed=args.installed, folder=args.snapshots,
                          confirmed=args.confirmed_working) if args.capture else
                  verify(repo=args.source, installed=args.installed, folder=args.snapshots))
    except (OSError, ValueError, UnicodeError, TypeError) as exc:
        report = {"status": "BLOCKED", "blockers": [str(exc)[:250]]}
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("SPIDER KNOWN-GOOD LOCK: " + report["status"])
        for item in report.get("blockers", []):
            print("BLOCKED:", item)
        if report.get("candidate_changes"):
            print("Proposed changes requiring review:", len(report["candidate_changes"]))
    return 3 if report["status"] == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
