"""Safe, bounded local integrations for Spider Operations Hub.

Only fixed program paths are runnable, and only after a user GUI click.
No sudo, shell=True, package installs, service changes or background scans.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import subprocess

DEFAULT_ROOT = Path("/usr/local/lib/spider-os")
WORKSPACES = {
    "Studio": ("studio/bin/studio",),
    "Author": ("author/bin/author",),
    "Study": ("study/bin/study",),
    "Forage": ("forage/forage.py",),
    "Deep Forage": ("forage/deep-forage/deep_forage.py",),
    "Kali Bay": ("kali-bay/bin/kali-bay", "ui"),
}
SOURCES = {
    "Webbie": "webbie/agent/webbie.py",
    "The Web": "the-web/shell/main.py",
    "Studio": "studio/main.py",
    "Author": "author/main.py",
    "Study": "study/study.py",
    "Forage": "forage/engine.py",
    "Deep Forage": "forage/deep-forage/deep_forage.py",
    "Kali Bay": "kali-bay/ui/kali_bay.py",
}


def _command(program, *args, timeout=8):
    try:
        p = subprocess.run(
            [str(program), *[str(arg) for arg in args]], capture_output=True,
            text=True, check=False, timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return p.stdout.strip() if p.returncode == 0 else None


def workspace_command(name, root=DEFAULT_ROOT):
    """Return a fixed, reviewable launcher command; never an LLM-supplied shell."""
    if name not in WORKSPACES:
        raise ValueError("Unknown Spider workspace.")
    parts = WORKSPACES[name]
    script = Path(root) / parts[0]
    if not script.is_file() or script.is_symlink():
        raise FileNotFoundError(f"Installed {name} launcher not found.")
    if script.suffix == ".py":
        return ["python3", str(script), *parts[1:]]
    if not os.access(script, os.X_OK):
        raise PermissionError(f"{name} launcher is not executable.")
    return [str(script), *parts[1:]]


def launch_workspace(name, root=DEFAULT_ROOT):
    """Used only by clicked buttons, never called by status refresh."""
    if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        raise RuntimeError("Open this from an active graphical desktop session.")
    command = workspace_command(name, root)
    return subprocess.Popen(
        command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, start_new_session=True, close_fds=True,
    ).pid


def system_status(root=DEFAULT_ROOT):
    root = Path(root)
    try:
        disk = shutil.disk_usage(Path.home())
        free_gb = round(disk.free / (1024 ** 3), 1)
    except OSError:
        free_gb = None
    return {
        "workspace": "Spider OS",
        "mode": "read_only",
        "installed_source_presence": {
            label: (root / relative).is_file() for label, relative in SOURCES.items()
        },
        "user_services": {
            service: (_command("systemctl", "--user", "show", service, "--property=ActiveState", "--value") or "unavailable")
            for service in ("webbie.service", "pipewire.service", "wireplumber.service")
        },
        "graphical_session": bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")),
        "disk_free_gib": free_gb,
        "note": "Presence and service states only, not a functional application test.",
    }


def kali_status(root=DEFAULT_ROOT):
    launcher = Path(root) / "kali-bay/bin/kali-bay"
    if not launcher.is_file() or launcher.is_symlink():
        raise FileNotFoundError("Installed Kali Bay launcher not found.")
    result = {"workspace": "Kali Bay", "mode": "read_only"}
    for key, operation in (
        ("readiness", "readiness-json"), ("purple_tools", "purple-json")
    ):
        raw = _command(str(launcher), operation, timeout=10)
        if raw is None:
            result[key] = {"status": "unavailable"}
            continue
        try:
            result[key] = json.loads(raw)
        except (ValueError, TypeError):
            result[key] = {"status": "unreadable"}
    result["note"] = (
        "Inventory only. Does not start Kali, execute scans, provision tools "
        "or change permissions. Missing full metapackage is not proof of failure."
    )
    return result
