"""Wave 9: non-destructive The Web workspace/launcher continuity audit.

Does not open a second desktop shell, change XDG defaults, execute arbitrary
.desktop commands, change existing launchers or access private documents.
"""
from __future__ import annotations
import configparser
import os
from pathlib import Path

from operations_services import DEFAULT_ROOT, WORKSPACES

LAUNCHER_ROOT = Path("/usr/share/applications")
WANTED = ("studio", "author", "study", "forage", "deep-forage", "kali-bay")


def _parse_desktop(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 100_000:
        return None
    parser = configparser.RawConfigParser(strict=False, interpolation=None)
    parser.optionxform = str
    with path.open(encoding="utf-8", errors="replace") as stream:
        parser.read_file(stream)
    if not parser.has_section("Desktop Entry"):
        return None
    row = parser["Desktop Entry"]
    return {
        "label": row.get("Name", "")[:120],
        "exec": row.get("Exec", "")[:500],
        "hidden": row.get("Hidden", "").casefold() == "true",
    }


def desktop_continuity(root=DEFAULT_ROOT, applications_dir=LAUNCHER_ROOT):
    root = Path(root)
    applications_dir = Path(applications_dir)
    statuses = {}
    for name in WANTED:
        contract = WORKSPACES[{
            "deep-forage": "Deep Forage", "kali-bay": "Kali Bay",
        }.get(name, name.capitalize() if name != "studio" else "Studio")]
        launcher = root / contract[0]
        item = applications_dir / (name + ".desktop")
        try:
            parsed = _parse_desktop(item)
        except (OSError, configparser.Error, ValueError):
            parsed = None
        statuses[name] = {
            "app_source_present": launcher.is_file() and not launcher.is_symlink(),
            "installed_desktop_entry_found": parsed is not None,
            "entry_hidden": parsed["hidden"] if parsed else None,
            "entry_has_exec": bool(parsed and parsed["exec"]),
            "desktop_exec_mentions_approved_root": bool(
                parsed and (str(root) in parsed["exec"]
                            or (parsed["exec"].startswith("python3 ")
                                and str(root) in parsed["exec"]))
            ),
            "manual_review_needed": (parsed is None or not parsed["exec"]
                                     or parsed["hidden"]),
        }
    return {
        "workspace": "The Web",
        "operation": "workspace_launcher_continuity",
        "mode": "read_only",
        "desktop_session": os.environ.get("DESKTOP_SESSION", "unknown")[:80],
        "display_session": os.environ.get("XDG_SESSION_TYPE", "unknown")[:30],
        "shell_source_present": (root / "the-web/shell/main.py").is_file(),
        "operations_hub_launcher_present": (
            root / "system/bin/spider-operations"
        ).is_file(),
        "workspace_entries": statuses,
        "note": "This is a launcher-presence inventory, not a working-app "
                "check. Opening another The Web shell or editing KDE settings "
                "is intentionally prohibited.",
    }
