"""Persistent private missions shared by Spider OS native workspaces.

No network access, command execution or automatic access to project files.
Stores only user-entered titles, status and optional directory paths. Projects
remain in the user's local data directory, not in the public OS repository.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import uuid

MAX_BYTES = 1024 * 1024
MAX_ITEMS = 400
MAX_TEXT = 280
STATUSES = ("next", "active", "blocked", "done")
BAYS = (
    "default", "webbie", "forage", "deep-forage", "studio", "author",
    "art-lab", "dev-bay", "study", "media", "communications",
    "kali-bay", "system", "productivity", "devices",
)

BLUEPRINTS = {
    "default": ("The Web", ("Review today's priorities", "Check the bays", "Prepare release checkpoint")),
    "webbie": ("Webbie", ("Investigate a question", "Review sources and uncertainty", "Test voice conversation")),
    "forage": ("Forage", ("Collect trustworthy sources", "Verify evidence", "Organize citations")),
    "deep-forage": ("Deep Forage", ("Frame research question", "Compare competing explanations", "Record follow-up inquiry")),
    "studio": ("Studio", ("Capture a multitrack take", "Review audio quality", "Prepare session master")),
    "author": ("Author", ("Write or revise a chapter", "Check Broken World continuity", "Review case evidence")),
    "art-lab": ("Art Lab", ("Organize artwork", "Prepare asset variations", "Approve a final export")),
    "dev-bay": ("Dev Bay", ("Review code changes", "Run local tests", "Prepare a verified build")),
    "study": ("Study", ("Review a rubric", "Work on coursework", "Check APA and sources")),
    "media": ("Media Center", ("Audit the media library", "Check BCN/Nova schedule", "Verify radio and playback")),
    "communications": ("Communications", ("Draft a message", "Review correspondence", "Prepare a follow-up")),
    "kali-bay": ("Kali Bay", ("Prepare an authorized lab", "Review defensive findings", "Document evidence")),
    "system": ("System", ("Inspect service health", "Verify backups", "Prepare rollback checkpoint")),
    "productivity": ("Productivity", ("Plan today's priorities", "Organize projects", "Review completed work")),
    "devices": ("Devices", ("Inspect available devices", "Review connection status", "Plan a safe transfer")),
}


def default_location(home: Path | None = None) -> Path:
    base = home if home is not None else Path.home()
    return base / ".local/share/spider-os/native-bays/missions.json"


def _clean_text(value: object, limit: int = MAX_TEXT) -> str:
    return " ".join(str(value or "").split())[:limit]


def _safe_entry(entry: object) -> dict | None:
    if not isinstance(entry, dict):
        return None
    ident = entry.get("id")
    if not isinstance(ident, str) or len(ident) != 32:
        return None
    try:
        if uuid.UUID(hex=ident).hex != ident:
            return None
    except ValueError:
        return None
    bay = entry.get("bay")
    if bay not in BAYS:
        return None
    title = _clean_text(entry.get("title"))
    if not title:
        return None
    status = entry.get("status")
    if status not in STATUSES:
        status = "next"
    folder = entry.get("folder") or ""
    if not isinstance(folder, str):
        folder = ""
    # A recorded folder is a bookmark, not permission to traverse it.
    folder = folder[:1024]
    return {"id": ident, "bay": bay, "title": title,
            "status": status, "folder": folder}


def _validate_path(location: Path):
    for item in (location, *location.parents):
        if item.is_symlink():
            raise OSError("Refusing symlinked mission storage")
        if item == item.parent:
            break
    if location.exists() and not location.is_file():
        raise OSError("Mission store is not a regular file")


class MissionStore:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path is not None else default_location()

    def read(self) -> list[dict]:
        _validate_path(self.path)
        if not self.path.exists():
            return []
        if self.path.stat().st_size > MAX_BYTES:
            raise ValueError("Mission file is over its size limit")
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or raw.get("version") != 1:
            raise ValueError("Unrecognized mission file version")
        incoming = raw.get("missions")
        if not isinstance(incoming, list) or len(incoming) > MAX_ITEMS:
            raise ValueError("Invalid mission collection")
        result = []
        seen = set()
        for item in incoming:
            clean = _safe_entry(item)
            if clean and clean["id"] not in seen:
                result.append(clean)
                seen.add(clean["id"])
        return result

    def write(self, missions: list[dict]):
        if len(missions) > MAX_ITEMS:
            raise ValueError("Mission limit reached")
        cleaned = [_safe_entry(item) for item in missions]
        if any(item is None for item in cleaned):
            raise ValueError("Invalid mission entry")
        if len({item["id"] for item in cleaned}) != len(cleaned):
            raise ValueError("Duplicate mission ID")
        payload = json.dumps({"version": 1, "missions": cleaned},
                             ensure_ascii=False, indent=2) + "\n"
        if len(payload.encode("utf-8")) > MAX_BYTES:
            raise ValueError("Mission file is too large")
        _validate_path(self.path)
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        _validate_path(self.path)
        fd, temporary = tempfile.mkstemp(prefix=".spider-missions-",
                                        dir=self.path.parent)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def add(self, bay: str, title: str, folder: str = "") -> dict:
        if bay not in BAYS:
            raise ValueError("Unknown workspace")
        title = _clean_text(title)
        if not title:
            raise ValueError("A mission needs a title")
        if len(str(folder)) > 1024:
            raise ValueError("Project path is too long")
        if folder:
            path = Path(folder)
            if not path.is_absolute() or path.is_symlink() or not path.is_dir():
                raise ValueError("Select an existing non-symlinked project directory")
            folder = str(path)
        missions = self.read()
        mission = {"id": uuid.uuid4().hex, "bay": bay, "title": title,
                   "status": "next", "folder": folder}
        missions.append(mission)
        self.write(missions)
        return mission

    def update(self, ident: str, *, status: str | None = None,
               destination: str | None = None) -> dict:
        if status is not None and status not in STATUSES:
            raise ValueError("Unknown mission status")
        if destination is not None and destination not in BAYS:
            raise ValueError("Unknown destination bay")
        missions = self.read()
        for mission in missions:
            if mission["id"] == ident:
                if status is not None:
                    mission["status"] = status
                if destination is not None:
                    mission["bay"] = destination
                self.write(missions)
                return mission
        raise KeyError("Mission not found")

    def remove(self, ident: str):
        missions = self.read()
        remaining = [item for item in missions if item["id"] != ident]
        if len(remaining) == len(missions):
            raise KeyError("Mission not found")
        self.write(remaining)

    def for_bay(self, bay: str) -> list[dict]:
        if bay not in BAYS:
            raise ValueError("Unknown workspace")
        return [item for item in self.read() if item["bay"] == bay]
