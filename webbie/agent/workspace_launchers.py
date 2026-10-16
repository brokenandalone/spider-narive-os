"""Fixed, existence-checked Spider OS workspace entrypoints.

No user-supplied command strings or shell parsing. Reports launch requests,
not proof the target opened. Installed PC customizations always take priority.
"""
from pathlib import Path
import os
import shutil

BASE = Path("/usr/local/lib/spider-os")
SAFE = {
    "studio": (
        ("studio/bin/studio", "exec"),
        ("studio/main.py", "python"),
    ),
    "media": (
        ("/usr/local/bin/spider-media-center", "exec"),
        ("/usr/local/bin/spider-media-player", "exec"),
    ),
}

def workspace_command(name, *, root=BASE, exists=None, executable=None,
                      python_bin="python3"):
    """Resolve reviewed launchers only, never a caller-provided path or script."""
    if not isinstance(name, str) or name not in SAFE:
        return None
    root = Path(root).resolve()
    file_exists = exists or (lambda p: p.is_file())
    can_execute = executable or (lambda p: os.access(p, os.X_OK))
    for relative, mode in SAFE[name]:
        candidate = (Path(relative) if relative.startswith("/")
                     else root / relative)
        candidate = candidate.resolve()
        if mode == "python":
            if not candidate.is_relative_to(root) or not file_exists(candidate):
                continue
            interpreter = shutil.which(python_bin)
            if interpreter is not None:
                return [interpreter, str(candidate)]
        elif mode == "exec":
            # Only fixed allowlisted paths, no command arguments.
            if file_exists(candidate) and can_execute(candidate):
                return [str(candidate)]
    return None


# Exact native bay IDs from The Web's app_catalog.WORKSPACES.
# These are GUI TAB identifiers, never commands or executable names.
NATIVE_BAYS = frozenset((
    "default", "webbie", "forage", "deep-forage", "studio", "author",
    "art-lab", "dev-bay", "study", "media", "communications",
    "kali-bay", "system", "recovery", "games",
))
BAY_NAMES = {
    "home": "default", "the web": "default", "web": "default",
    "webbie": "webbie", "forage": "forage",
    "deep forage": "deep-forage", "studio": "studio",
    "audio studio": "studio", "author": "author", "author bay": "author",
    "art lab": "art-lab", "developer": "dev-bay", "dev bay": "dev-bay",
    "study": "study", "school": "study", "media": "media",
    "media center": "media", "communications": "communications",
    "kali": "kali-bay", "kali bay": "kali-bay",
    "system": "system", "recovery": "recovery", "games": "games",
}


def native_bay_request(utterance):
    """Only a literal, exact request for a known Spider OS native workspace.

    Never turns an LLM-generated suggestion or quoted text into an action:
    the resident calls this only on the actual user command after voice trust.
    """
    import re
    if not isinstance(utterance, str) or len(utterance) > 120 or "\n" in utterance:
        return None
    match = re.fullmatch(
        r"\s*(?:(?:hey\s+)?(?:webbie|webby)\s*[,.:]?\s+)?"
        r"(?:open|launch|switch\s+to|go\s+to|take\s+me\s+to|enter)\s+"
        r"(?:the\s+)?([a-z][a-z -]{0,40}?)(?:\s+bay)?\s*[.!]?\s*",
        utterance, flags=re.IGNORECASE,
    )
    if not match:
        return None
    label = " ".join(match.group(1).lower().split())
    return BAY_NAMES.get(label)


def request_native_bay(name, *, runtime=None, timeout=2.5):
    """Request a real tab switch from the owner-authorized The Web GUI.

    No X11 key injection, process spawning, root, shell or automatic grant.
    """
    import socket
    import stat
    if name not in NATIVE_BAYS:
        raise ValueError("Unknown native Spider OS workspace")
    folder = Path(runtime) if runtime is not None else (
        Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")) / "spider-os"
    )
    address = folder / "webbie-operator.sock"
    try:
        if folder.is_symlink() or address.is_symlink():
            return "Native workspace control is not available."
        if not address.exists() or not stat.S_ISSOCK(address.stat().st_mode):
            return ("Open The Web and enable Webbie's owner-approved safe "
                    "computer access to switch its native workspaces.")
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as peer:
            peer.settimeout(timeout)
            peer.connect(str(address))
            peer.sendall(("BAY:" + name).encode("ascii"))
            reply = peer.recv(401)
        if not reply or len(reply) > 400:
            return "The Web did not confirm the workspace change."
        return reply.decode("utf-8", "replace")
    except (OSError, TimeoutError, ValueError):
        return "The Web's native workspace control is unavailable."
