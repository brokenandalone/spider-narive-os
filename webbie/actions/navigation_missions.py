"""Jarvis owner-reviewed navigation missions for ONE selected desktop window.

This parser only accepts literal user-typed navigation requests. No model,
screen image, webpage, microphone transcript, or remote connection may grant
an action. The GUI must confirm each individual step, an active task grant,
and its exact bound window before calling the existing confined operator.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
import time

MAX_STEPS = 6
MAX_TEXT = 220
MAX_SECONDS = 120
WAKE = re.compile(r"^(?:hey\s+)?(?:webbie|webby|web)[\s,.:]+", re.I)

# Key names are restricted to static reviewed X11 desktop commands.
CONTROLS = {
    "scroll down": ("Page_Down", False),
    "scroll up": ("Page_Up", False),
    "page down": ("Page_Down", False),
    "page up": ("Page_Up", False),
    "go back": ("alt+Left", True),
    "back": ("alt+Left", True),
    "go forward": ("alt+Right", True),
    "forward": ("alt+Right", True),
    "refresh page": ("ctrl+r", True),
    "reload page": ("ctrl+r", True),
    "refresh browser": ("ctrl+r", True),
    "next tab": ("ctrl+Page_Down", True),
    "previous tab": ("ctrl+Page_Up", True),
    "switch to next tab": ("ctrl+Page_Down", True),
    "switch to previous tab": ("ctrl+Page_Up", True),
}
REPEAT = re.compile(r"^(scroll (?:up|down)|page (?:up|down))\s+(?:(\d+)\s+times?|twice|three times)$", re.I)


@dataclass(frozen=True)
class NavigationStep:
    label: str
    key: str
    browser_only: bool


@dataclass(frozen=True)
class NavigationPlan:
    description: str
    steps: tuple[NavigationStep, ...]


def parse_navigation_request(raw):
    """Return None for unrelated chat, reject ambiguous/unsafe command plans."""
    if not isinstance(raw, str) or not raw.strip() or len(raw) > MAX_TEXT:
        return None
    phrase = WAKE.sub("", raw.strip(), count=1)
    phrase = re.sub(r"\s+", " ", phrase).strip(" .,!?").lower()
    if not phrase:
        return None
    parts = re.split(r"\s+(?:and\s+)?then\s+", phrase)
    if len(parts) > MAX_STEPS:
        return None
    steps = []
    for part in parts:
        match = REPEAT.fullmatch(part)
        if match:
            count = int(match.group(2)) if match.group(2) else (
                2 if part.endswith("twice") else 3)
            if count < 1 or count > MAX_STEPS:
                return None
            kind = match.group(1).lower()
            key, browser_only = CONTROLS[kind]
            steps.extend(NavigationStep(kind.title(), key, browser_only)
                         for _ in range(count))
            continue
        action = CONTROLS.get(part)
        if action is None:
            return None
        key, browser_only = action
        steps.append(NavigationStep(part.title(), key, browser_only))
    if not 1 <= len(steps) <= MAX_STEPS:
        return None
    return NavigationPlan(description=phrase[:MAX_TEXT], steps=tuple(steps))


class NavigationMission:
    """Non-persistent, stop-safe pending steps for one specifically bound window.

    The GUI owns authorization and must call complete only after an actual
    confined operator attempt; failure discards all remaining steps.
    """
    def __init__(self, *, clock=None):
        self.clock = clock or time.monotonic
        self.revision = 0
        self.stop()

    def stop(self):
        self.revision += 1
        self.plan = None
        self.window = None
        self.selected_app_id = None
        self.position = 0
        self.expires = 0.0

    def stage(self, plan, *, window, selected_app_id, browser=False,
              approved=False):
        if approved is not True:
            raise PermissionError("Authorize the selected window and task first")
        if (not isinstance(plan, NavigationPlan) or not plan.steps or
                len(plan.steps) > MAX_STEPS or not isinstance(window, str)
                or not re.fullmatch(r"0x[0-9a-fA-F]{1,16}", window)
                or not isinstance(selected_app_id, str) or
                not selected_app_id.endswith(".desktop")):
            raise ValueError("Invalid navigation task or selected window")
        if any(step.browser_only for step in plan.steps) and browser is not True:
            raise PermissionError("Browser navigation needs an approved browser app")
        self.stop()
        self.plan = plan
        self.window = window
        self.selected_app_id = selected_app_id
        self.position = 0
        self.expires = self.clock() + MAX_SECONDS
        return self.revision

    def next_step(self, *, granted=False, window=None, app_id=None,
                  browser=False, revision=None):
        if (granted is not True or self.plan is None or
                self.clock() >= self.expires or window != self.window or
                app_id != self.selected_app_id or
                (revision is not None and revision != self.revision)):
            self.stop()
            raise PermissionError("Navigation task expired, revoked, or changed window")
        if self.position >= len(self.plan.steps):
            self.stop()
            raise ValueError("No remaining navigation steps")
        step = self.plan.steps[self.position]
        if step.browser_only and browser is not True:
            self.stop()
            raise PermissionError("Selected browser is no longer approved")
        return step

    def complete(self, *, success=False, revision=None):
        if self.plan is None or revision != self.revision or success is not True:
            self.stop()
            return False
        self.position += 1
        if self.position >= len(self.plan.steps):
            self.stop()
            return False
        return True

    def progress(self):
        if self.plan is None or self.clock() >= self.expires:
            return "No pending desktop navigation mission."
        next_step = self.plan.steps[self.position]
        return (f"Step {self.position + 1} of {len(self.plan.steps)}: "
                f"{next_step.label}. Click Run next reviewed step. "
                "Every step needs an active grant and bound window.")
