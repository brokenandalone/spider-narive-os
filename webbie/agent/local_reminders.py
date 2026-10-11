"""Owner-created local reminders for Webbie on Spider OS.

All reminders are written by an explicit local GUI action. Transcribed speech,
website text, model output and camera observations NEVER create reminders.
Uses local wall-clock times so daily/weekly reminders track the user's clock.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import os
from pathlib import Path
import re
import uuid

from proactive_checks import _read_small_json, _store_private_json, quiet_now

DEFAULT_REMINDERS = Path.home() / ".local/state/spider-os/webbie-reminders.json"
MAX_REMINDERS = 50
MAX_TICK_ALERTS = 5
ALLOWED_REPEAT = frozenset({"once", "daily", "weekly"})
TITLE_LIMIT = 100


def _parse_due(value):
    if not isinstance(value, str) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d", value):
        raise ValueError("Reminder time must be YYYY-MM-DDTHH:MM (local time)")
    due = datetime.fromisoformat(value)
    if not 2000 <= due.year <= 2100:
        raise ValueError("Reminder date is outside the supported range")
    return due


def _valid_title(title):
    if not isinstance(title, str):
        raise ValueError("Reminder title is required")
    clean = re.sub(r"\s+", " ", title).strip()
    if not clean or len(clean) > TITLE_LIMIT or any(ord(ch) < 32 for ch in clean):
        raise ValueError("Reminder title must be 1 to 100 printable characters")
    return clean


def list_reminders(path=DEFAULT_REMINDERS):
    raw = _read_small_json(path)
    items = raw.get("items", [])
    if not isinstance(items, list):
        return []
    safe = []
    for item in items[:MAX_REMINDERS]:
        if not isinstance(item, dict):
            continue
        identifier = item.get("id")
        title = item.get("title")
        when = item.get("due")
        repeat = item.get("repeat")
        if (not isinstance(identifier, str)
                or re.fullmatch(r"[0-9a-f]{32}", identifier) is None
                or repeat not in ALLOWED_REPEAT):
            continue
        try:
            title = _valid_title(title)
            _parse_due(when)
        except ValueError:
            continue
        safe.append({"id": identifier, "title": title,
                     "due": when, "repeat": repeat})
    return safe


def add_reminder(title, due, repeat="once", *, path=DEFAULT_REMINDERS, now=None):
    """Trusted local UI only. No voice/LLM entrypoint is exposed."""
    name = _valid_title(title)
    date = _parse_due(due)
    if repeat not in ALLOWED_REPEAT:
        raise ValueError("Repeat must be once, daily or weekly")
    current = datetime.now() if now is None else now
    if not isinstance(current, datetime) or current.tzinfo is not None:
        raise ValueError("Expected local time without UTC offset")
    if date < current - timedelta(minutes=1):
        raise ValueError("Choose a future time for a new reminder")
    items = list_reminders(path)
    if len(items) >= MAX_REMINDERS:
        raise ValueError("Maximum 50 local reminders")
    identifier = uuid.uuid4().hex
    items.append({"id": identifier, "title": name,
                  "due": date.strftime("%Y-%m-%dT%H:%M"), "repeat": repeat})
    _store_private_json(path, {"version": 1, "items": items})
    return identifier


def delete_reminder(identifier, *, path=DEFAULT_REMINDERS):
    if not isinstance(identifier, str) or re.fullmatch(r"[0-9a-f]{32}", identifier) is None:
        raise ValueError("Invalid reminder ID")
    old = list_reminders(path)
    remaining = [item for item in old if item["id"] != identifier]
    if len(remaining) == len(old):
        return False
    _store_private_json(path, {"version": 1, "items": remaining})
    return True


def _occurrence(item, now):
    """Return occurrence date or None; avoid stale catch-up surprises."""
    start = _parse_due(item["due"])
    if now < start:
        return None
    if item["repeat"] == "once":
        return start.date().isoformat() if now - start <= timedelta(hours=24) else None
    if now.time().replace(second=0, microsecond=0) < start.time():
        return None
    if item["repeat"] == "daily":
        return now.date().isoformat()
    if item["repeat"] == "weekly" and now.weekday() == start.weekday():
        return now.date().isoformat()
    return None


class ReminderScheduler:
    def __init__(self, *, path=DEFAULT_REMINDERS, state_path=None,
                 clock=None, on_alert=None):
        self.path = Path(path)
        self.state_path = Path(state_path or str(self.path) + ".history")
        self.clock = clock
        self.on_alert = on_alert

    def tick(self, *, session_active=False, sleeping=False,
             quiet_start="22:00", quiet_end="08:00"):
        timestamp = float(self.clock() if self.clock is not None
                          else datetime.now().timestamp())
        now = datetime.fromtimestamp(timestamp)
        reminders = list_reminders(self.path)
        delivered = _read_small_json(self.state_path)
        done = delivered.get("delivered", {})
        if not isinstance(done, dict):
            done = {}
        known = {item["id"] for item in reminders}
        # Old/deleted reminders must not accumulate unbounded history.
        done = {k: v for k, v in done.items()
                if k in known and isinstance(v, str) and len(v) == 10}
        allowed = (session_active is True and sleeping is False
                   and not quiet_now(timestamp, quiet_start, quiet_end))
        due_count = 0
        sent = 0
        for item in reminders:
            occurrence = _occurrence(item, now)
            if occurrence is None or done.get(item["id"]) == occurrence:
                continue
            due_count += 1
            if not allowed or self.on_alert is None or sent >= MAX_TICK_ALERTS:
                continue
            try:
                self.on_alert("Reminder: " + item["title"])
            except Exception:
                continue
            done[item["id"]] = occurrence
            sent += 1
        if sent or done != delivered.get("delivered", {}):
            _store_private_json(
                self.state_path, {"version": 1, "delivered": done})
        return {"scheduled": len(reminders), "due": max(0, due_count - sent),
                "delivered": sent}
