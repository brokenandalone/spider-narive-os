"""Webbie's owner-controlled evidence research agenda.

Questions, follow-ups, uncertainty and source references are persisted locally.
A source URL is not treated as verified simply because somebody entered it.
Nothing runs autonomously or executes arbitrary host actions in this module.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from urllib.parse import urlparse
import uuid

MAX_FILE = 1024 * 1024
MAX_QUESTIONS = 150
STATES = ("queued", "investigating", "needs-review", "reviewed")


def default_path():
    return Path.home() / ".local/share/spider-os/webbie/research-agenda.json"


def clean(value, limit):
    return " ".join(str(value or "").split())[:limit]


def safe_url(value):
    if not isinstance(value, str) or len(value) > 1200:
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username and not parsed.password


def validate(record):
    if not isinstance(record, dict):
        raise ValueError("Invalid research entry")
    question = clean(record.get("question"), 360)
    status = record.get("status")
    if not question or status not in STATES:
        raise ValueError("Invalid research question or state")
    ident = record.get("id")
    if not isinstance(ident, str) or len(ident) != 32:
        raise ValueError("Invalid research identifier")
    try:
        if uuid.UUID(hex=ident).hex != ident:
            raise ValueError("Invalid identifier")
    except ValueError as error:
        raise ValueError("Invalid research identifier") from error
    sources = record.get("sources", [])
    followups = record.get("followups", [])
    if not isinstance(sources, list) or len(sources) > 12:
        raise ValueError("Too many research sources")
    if not isinstance(followups, list) or len(followups) > 12:
        raise ValueError("Too many follow-up questions")
    checked = []
    for item in sources:
        if not isinstance(item, dict) or not safe_url(item.get("url")):
            raise ValueError("Source references require HTTPS without credentials")
        checked.append({"url": item["url"], "title": clean(item.get("title"), 140),
                        "reviewed": bool(item.get("reviewed", False))})
    return {
        "id": ident,
        "question": question,
        "status": status,
        "finding": clean(record.get("finding"), 2500),
        "uncertainty": clean(record.get("uncertainty"), 800),
        "followups": [clean(item, 360) for item in followups if clean(item, 360)],
        "sources": checked,
    }


class ResearchAgenda:
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else default_path()

    def _safe(self):
        for part in (self.path, *self.path.parents):
            if part.is_symlink():
                raise OSError("Refusing symlinked research agenda")
            if part == part.parent:
                break
        if self.path.exists() and not self.path.is_file():
            raise OSError("Research agenda is not a regular file")

    def read(self):
        self._safe()
        if not self.path.exists():
            return []
        if self.path.stat().st_size > MAX_FILE:
            raise ValueError("Research agenda too large")
        document = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(document, dict) or document.get("version") != 1:
            raise ValueError("Unknown research agenda format")
        entries = document.get("entries")
        if not isinstance(entries, list) or len(entries) > MAX_QUESTIONS:
            raise ValueError("Invalid research entry count")
        result = [validate(entry) for entry in entries]
        if len(set(item["id"] for item in result)) != len(result):
            raise ValueError("Duplicate research identifier")
        return result

    def write(self, entries):
        if len(entries) > MAX_QUESTIONS:
            raise ValueError("Research agenda full")
        entries = [validate(item) for item in entries]
        payload = json.dumps({"version": 1, "entries": entries}, indent=2,
                             ensure_ascii=False) + "\n"
        if len(payload.encode("utf-8")) > MAX_FILE:
            raise ValueError("Research agenda over size limit")
        self._safe()
        self.path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        self._safe()
        fd, temp = tempfile.mkstemp(dir=self.path.parent,
                                    prefix=".webbie-research-")
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, self.path)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)

    def add(self, question):
        question = clean(question, 360)
        if not question:
            raise ValueError("Enter a question to research")
        entries = self.read()
        entry = {"id": uuid.uuid4().hex, "question": question,
                 "status": "queued", "finding": "", "uncertainty": "",
                 "followups": [], "sources": []}
        entries.append(entry)
        self.write(entries)
        return entry

    def edit(self, ident, **changes):
        allowed = {"status", "finding", "uncertainty"}
        if any(name not in allowed for name in changes):
            raise ValueError("Unsupported research change")
        entries = self.read()
        for entry in entries:
            if entry["id"] == ident:
                entry.update(changes)
                clean_entry = validate(entry)
                entries[entries.index(entry)] = clean_entry
                self.write(entries)
                return clean_entry
        raise KeyError("Research question missing")

    def add_source(self, ident, url, title=""):
        if not safe_url(url):
            raise ValueError("Add a valid public HTTPS source, without credentials")
        entries = self.read()
        for entry in entries:
            if entry["id"] == ident:
                if any(item["url"] == url for item in entry["sources"]):
                    return
                entry["sources"].append({"url": url, "title": title, "reviewed": False})
                self.write(entries)
                return
        raise KeyError("Research question missing")

    def add_followup(self, ident, question):
        question = clean(question, 360)
        if not question:
            raise ValueError("Follow-up needs a question")
        entries = self.read()
        for entry in entries:
            if entry["id"] == ident:
                entry["followups"].append(question)
                self.write(entries)
                return
        raise KeyError("Research question missing")

    def next_question(self):
        return next((entry for entry in self.read()
                     if entry["status"] in ("queued", "investigating")), None)
