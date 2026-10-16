"""Private in-memory, content-free Jarvis operator activity timeline.

No user messages, URL paths, page text, coordinates, window titles, voice,
screenshots, secrets or files are recorded. A local GUI owns this bounded log.
"""
from __future__ import annotations
from collections import deque
from datetime import datetime

MAX_EVENTS = 30
EVENTS = {
    "grant_started": "Desktop task authorization started",
    "grant_expired": "Desktop task authorization ended",
    "stopped": "Desktop control stopped",
    "mission_staged": "Navigation plan staged for review",
    "mission_denied": "Navigation plan denied",
    "mission_step": "Reviewed navigation step requested",
    "mission_failed": "Navigation step failed; plan canceled",
    "mission_done": "Navigation plan finished",
    "mission_canceled": "Navigation plan canceled",
    "website_requested": "Approved website opening requested",
    "website_denied": "Website opening denied",
    "app_requested": "Approved application launch requested",
    "native_workspace_requested": "Authorized native Spider OS tab switch requested",
    "app_denied": "Application launch denied",
    "window_bound": "Window selected for desktop task",
    "window_observed": "One consented window snapshot captured",
    "review_approved": "Sensitive action approved in local dialog",
    "review_denied": "Sensitive action rejected in local dialog",
}

class ActionJournal:
    def __init__(self, *, clock=None):
        self._clock = clock or datetime.now
        self._events = deque(maxlen=MAX_EVENTS)

    def record(self, event):
        if not isinstance(event, str) or event not in EVENTS:
            raise ValueError("Only fixed, redacted Jarvis events are accepted")
        when = self._clock()
        stamp = when.strftime("%H:%M:%S")
        self._events.append((stamp, event))
        return len(self._events)

    def latest(self):
        return list(self._events)

    def display(self):
        if not self._events:
            return "No desktop activity yet. This session only."
        return "\n".join(f"{stamp}  {EVENTS[key]}" for stamp,key in reversed(self._events))

    def clear(self):
        self._events.clear()
