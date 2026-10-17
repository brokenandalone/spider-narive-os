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
