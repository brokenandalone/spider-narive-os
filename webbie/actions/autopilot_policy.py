"""Bounded, user-consented Webbie navigation autopilot policy.

Policy never controls an OS, captures a screen, or grants permissions.
The trusted GUI owns approval and the DesktopOperator enforces its own
selected-window restrictions. Navigation-only keys can continue automatically.
Clicks ALWAYS require a visible owner confirmation, even within a task.
Stop, expiry, window loss, uncertainty, repetition and risk all fail closed.
"""
from __future__ import annotations
import re
import time

MAX_STEPS = 6
MAX_SECONDS = 120
AUTO_KEYS = frozenset({
    'Tab', 'Escape', 'Up', 'Down', 'Left', 'Right',
    'Home', 'End', 'Page_Up', 'Page_Down',
})
DANGEROUS_WORDS = re.compile(
    r'\b(?:delete|erase|wipe|remove|destroy|format|overwrite|publish|post|'
    r'send|submit|transfer|pay|purchase|checkout|buy|subscribe|install|'
    r'uninstall|upgrade|sudo|admin|password|credential|secret|sign[ -]?in|'
    r'security|firewall|root|terminal|shell|command|execute|'
    r'download|upload|bank|payment|wire|commit|push|deploy)\b', re.I)


def risky_content(text):
    return bool(DANGEROUS_WORDS.search(str(text or '')))


class AutopilotPolicy:
    """A state machine controlled only by visible GUI consent and stop controls."""

    def __init__(self, *, clock=None, max_steps=MAX_STEPS):
        if type(max_steps) is not int or not 1 <= max_steps <= MAX_STEPS:
            raise ValueError('Autopilot must have a small fixed action budget')
        self.clock = clock or time.monotonic
        self.limit = max_steps
        self.active = False
        self.target = None
        self.task = ''
        self.ends_at = 0.0
        self.count = 0
        self.last = None
        self.repeats = 0
        self.revision = 0

    def begin(self, task, selected_window, *, approved=False):
        if approved is not True:
            raise PermissionError('Only the on-screen user can start autopilot')
        if (not isinstance(task, str) or not task.strip() or
                len(task) > 300 or not isinstance(selected_window, str) or
                not re.fullmatch(r'0x[0-9a-fA-F]{1,16}', selected_window)):
            raise ValueError('A bounded task and authorized window are required')
        if risky_content(task):
            raise PermissionError('High-impact tasks require manual controls, not autopilot')
        self.revision += 1
        self.active = True
        self.task = task.strip()
        self.target = selected_window.lower()
        self.ends_at = self.clock() + MAX_SECONDS
        self.count = 0
        self.last = None
        self.repeats = 0
        return self.revision

    def stop(self):
        self.active = False
        self.revision += 1

    def ready(self, *, window, granted, revision):
        return (self.active and granted is True and
                window is not None and window.lower() == self.target and
                revision == self.revision and
                self.clock() < self.ends_at and self.count < self.limit)

    def decide(self, proposal, *, window, granted, revision):
        """Returns 'auto', 'review', 'done', or 'pause'; never executes a step."""
        if not self.ready(window=window, granted=granted, revision=revision):
            self.stop()
            return 'pause'
        if not isinstance(proposal, dict):
            self.stop()
            return 'pause'
        action = proposal.get('action')
        if action == 'done':
            self.stop()
            return 'done'
        if action not in {'click', 'press'} or risky_content(proposal.get('reason')):
            self.stop()
            return 'pause'
        confidence = proposal.get('confidence', 0)
        if (isinstance(confidence, bool) or
                not isinstance(confidence, (int, float)) or confidence < .90):
            self.stop()
            return 'pause'
        fingerprint = (action, proposal.get('key') if action == 'press'
                       else (proposal.get('x'), proposal.get('y')))
        self.repeats = self.repeats + 1 if fingerprint == self.last else 0
        self.last = fingerprint
        if self.repeats >= 2:
            self.stop()
            return 'pause'
        if action == 'press' and proposal.get('key') in AUTO_KEYS:
            return 'auto'
        if action == 'click':
            return 'review'
        self.stop()
        return 'pause'

    def record_step(self, *, window, granted, revision):
        if not self.ready(window=window, granted=granted, revision=revision):
            self.stop()
            return False
        self.count += 1
        if self.count >= self.limit:
            self.stop()
            return False
        return True
