#!/usr/bin/env python3
"""One reviewed Webbie fix on a PRIVATE copy of the owner's installed source.

Never edits /usr/local/lib/spider-os, the checked-out Git repo, the user's
archive, Media Center, BCN website, or any app service. This proposed owner-code
integration only adjusts Webbie's session detection and stays uninstalled.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import os
from pathlib import Path
import subprocess
import sys

from build_owner_preserving_stage import checked_path, load_owner_zip

NAME = "webbie/agent/webbie.py"
# These are from the actual October 12 owner-submitted file, never repo source.
OWNER_SHA256 = "08673fb0080d2974a0310e462a9f8d29a19d798a0f0cb74ff699dd271e67258c"
OLD_FUNC_SHA256 = "4b02719150b6227dc3c125229d0a6fa4529ebd1894fb8db4f4037ecbbb19e948"

REPLACEMENT = '''def session_is_active():
    """Return true only for an active unlocked *local* GUI session for this user.

    Unlike the original installed implementation, check every matching user
    session instead of returning after the first inactive TTY. Query all flags
    together with bounded subprocess times. Inability to verify means false.
    """
    try:
        import pwd
        owner = pwd.getpwuid(os.getuid()).pw_name
        sessions = subprocess.check_output(
            ["loginctl", "list-sessions", "--no-legend", "--no-pager"],
            text=True, stderr=subprocess.DEVNULL, timeout=4,
        )
        for line in sessions.splitlines():
            parts = line.split()
            if len(parts) < 3 or parts[2] != owner:
                continue
            details = subprocess.check_output(
                ["loginctl", "show-session", parts[0], "-p", "Active",
                 "-p", "IdleHint", "-p", "LockedHint", "-p", "Remote",
                 "-p", "Type", "--no-pager"],
                text=True, stderr=subprocess.DEVNULL, timeout=4,
            )
            flags = dict(row.split("=", 1) for row in details.splitlines()
                         if "=" in row)
            if (flags.get("Active") == "yes"
                    and flags.get("IdleHint") == "no"
                    and flags.get("LockedHint") == "no"
                    and flags.get("Remote") == "no"
                    and flags.get("Type") in ("x11", "wayland")):
                return True
    except (OSError, subprocess.SubprocessError, ValueError, KeyError):
        return False
    return False
'''


def function_node(raw: bytes, name: str = "session_is_active"):
    tree = ast.parse(raw.decode("utf-8"), filename=NAME)
    nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
             and n.name == name]
    if len(nodes) != 1:
        raise ValueError("Owner session function missing or duplicated")
    return nodes[0]


def patch_source(raw: bytes, *, expected_source_sha: str = OWNER_SHA256,
                 expected_func_sha: str = OLD_FUNC_SHA256) -> bytes:
    if hashlib.sha256(raw).hexdigest() != expected_source_sha:
        raise ValueError("Owner source has changed. Do not apply old patch")
    original = function_node(raw)
    original_ast_sha = hashlib.sha256(
        ast.dump(original, annotate_fields=True, include_attributes=False).encode()
    ).hexdigest()
    if original_ast_sha != expected_func_sha:
        raise ValueError("Original Webbie session logic does not match reviewed code")
    rows = raw.decode("utf-8").splitlines(keepends=True)
    result = "".join(rows[:original.lineno - 1]) + REPLACEMENT + "".join(rows[original.end_lineno:])
    patched = result.encode("utf-8")
    ast.parse(result, filename=NAME)
    # Prove all code outside exactly this one reviewed function is unchanged.
    new_node = function_node(patched)
    fresh = patched.decode("utf-8").splitlines(keepends=True)
    if (rows[:original.lineno - 1] != fresh[:new_node.lineno - 1]
            or rows[original.end_lineno:] != fresh[new_node.end_lineno:]):
        raise ValueError("Patch changed code outside the targeted function")
    return patched


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--owner-archive", type=Path, required=True)
    p.add_argument("--installed-root", type=Path, default=Path("/usr/local/lib/spider-os"))
    p.add_argument("--output", type=Path, required=True,
                   help="New private proposed webbie.py file OUTSIDE installed/source dirs")
    args = p.parse_args(argv)
    try:
        archive = args.owner_archive.expanduser().resolve()
        live_root = args.installed_root.expanduser().resolve()
        output = args.output.expanduser().absolute()
        cwd_repo = Path(__file__).resolve().parents[1]
        if (output == cwd_repo or cwd_repo in output.parents or
                output == live_root or live_root in output.parents or
                output.exists() or output.is_symlink()):
            raise ValueError("Output must be a NEW file outside live PC and Git repo")
        raw = load_owner_zip(archive)[NAME]
        live = checked_path(live_root, NAME).read_bytes()
        if live != raw:
            raise ValueError("Installed Webbie changed since uploaded owner ZIP")
        proposed = patch_source(raw)
        output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(proposed)
        except BaseException:
            output.unlink(missing_ok=True)
            raise
    except (OSError, ValueError, TypeError, UnicodeError, SyntaxError,
            subprocess.TimeoutExpired) as exc:
        print("OWNER CODE PATCH BLOCKED:", type(exc).__name__, str(exc)[:180],
              file=sys.stderr)
        return 3
    print("ONE LOCAL SOURCE-ONLY PROPOSAL CREATED:", output)
    print("Live Webbie source unchanged. No services stopped or restarted.")
    print("Session detection amended; voice, Firefox and research code retained.")
    print("NOT APPROVED FOR INSTALL. Other 30 file conflicts still need integration.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
