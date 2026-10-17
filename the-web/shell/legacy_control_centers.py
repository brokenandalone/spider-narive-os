"""Legacy Spider OS control center adapters: integrate, do not delete.

Yesterday's three development control centers have native replacements.
Keep real .desktop menu entries, installed binaries, saved settings, and
their original commands untouched until owner-authorized retirement.
Normal Ubuntu Studio apps are never included here.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NativeDestination:
    workspace: str
    tab_title: str
    message: str


LEGACY_DESTINATIONS = {
    "spider-os-universal.desktop": NativeDestination(
        "default", "Advanced tools & tasks",
        "Universal Control Center functions are distributed into native Spider OS bays. "
        "Open Studio, Author, Study, Webbie, Kali, Media or another real bay to work."
    ),
    "spider-os-workspace-max.desktop": NativeDestination(
        "default", "Advanced tools & tasks",
        "Workspace MAX analysis is embedded in the Advanced tools tab of each "
        "native bay, including BCN / Nova and System backups."
    ),
    "spider-webbie-intelligence.desktop": NativeDestination(
        "webbie", "Webbie controls",
        "Webbie model, privacy, voice and mission controls now belong inside "
        "the resident Webbie bay."
    ),
}


def destination(desktop_id):
    if not isinstance(desktop_id, str):
        return None
    return LEGACY_DESTINATIONS.get(desktop_id)


def notice(desktop_id):
    item = destination(desktop_id)
    return item.message if item else None
