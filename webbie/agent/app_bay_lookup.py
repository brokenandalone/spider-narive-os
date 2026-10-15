"""Webbie answers 'which native bay has this installed application?'.

This does not execute a command, contact a service or authorize a launch.
Results are derived from currently discoverable XDG application menu entries.
Never claim that a package is uninstalled simply because it is absent from
the visible app menu.
"""
from __future__ import annotations

from pathlib import Path
import re
import sys

MAX_QUERY = 100
SHELL = Path(__file__).resolve().parents[2] / "the-web/shell"


def requested_program(message):
    if not isinstance(message, str) or len(message) > 180:
        return None
    clean = re.sub(r"^\s*(?:(?:hey\s+)?webbie[,.:]?\s+)?",
                   "", message.strip(), flags=re.I)
    patterns = (
        r"which (?:bay|workspace) (?:has|contains) (?:the )?(?:app )?(.+?)",
        r"where can i find (?:the )?(?:installed )?(?:app(?:lication)? )?(.+?)",
        r"where is (?:the )?(?:installed )?app(?:lication)? (.+?)",
        r"find (?:the )?(?:installed )?app(?:lication)? (.+?)",
        r"what (?:bay|workspace) is (?:the )?(?:app )?(.+?) in",
    )
    for pattern in patterns:
        found = re.fullmatch(pattern + r"[?.!]*", clean, re.I)
        if found:
            result = found.group(1).strip(" \"'.!?")
            if result and len(result) <= MAX_QUERY:
                return result
    return None


def app_answer(name, apps, workspaces, explain):
    query = str(name).casefold().strip()
    if not query:
        return "Please name an application."
    exact = [app for app in apps if app.name.casefold() == query
             or app.desktop_id.casefold().removesuffix(".desktop") == query]
    matching = exact or [
        app for app in apps
        if query in app.name.casefold()
        or query in app.desktop_id.casefold()
    ]
    if not matching:
        return (f"I couldn't find a visible application-menu entry matching "
                f"{name}. That does not mean it was uninstalled. "
                "Open The Web's installed-app inventory or KDE's application menu "
                "to inspect other entries.")
    if len(matching) > 1:
        choices = "; ".join(
            app.name + " (" + workspaces.get(app.workspace, "System") + ")"
            for app in matching[:5])
        return ("Several available apps matched: " + choices +
                ". Specify the program name to identify its exact bay.")
    app = matching[0]
    bay = workspaces.get(app.workspace, "System")
    purpose = explain(app)
    return (f"{app.name} is available in {bay}. Use The Web > {bay} > "
            f"Optional installed tools. {purpose} "
            "You can change its bay assignment without moving or uninstalling it.")


def lookup_installed_app(message, *, discover=None, labels=None, explain=None):
    name = requested_program(message)
    if name is None:
        return None
    if discover is None or labels is None or explain is None:
        if str(SHELL) not in sys.path:
            sys.path.insert(0, str(SHELL))
        from app_catalog import discover_apps, WORKSPACES, app_purpose
        discover = discover if discover is not None else (
            lambda: discover_apps(desktops="TheWeb:KDE"))
        labels = labels if labels is not None else WORKSPACES
        explain = explain if explain is not None else app_purpose
    try:
        return app_answer(name, discover(), labels, explain)
    except (OSError, ValueError, RuntimeError):
        return "I couldn't inspect installed application entries right now."
