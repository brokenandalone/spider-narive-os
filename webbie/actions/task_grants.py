"""Short-lived, explicit GUI authorization for a single Spider OS desktop task.

A language model cannot create a grant, change the selected application,
approve a risk, or disable the stop flag. The GUI owns this object and calls
activate ONLY from its own user-click handler after a visible consent dialog.
This is a process-local permission cache, not an authentication service.
"""
from __future__ import annotations
import threading
import time

ROUTINE = frozenset({
    'observe.apps', 'observe.windows', 'app.open', 'window.focus',
    'pointer.click', 'keyboard.key', 'keyboard.type', 'task.begin', 'window.target',
})
SENSITIVE = frozenset({'window.close.confirm', 'keyboard.change.confirm'})
MAX_SECONDS = 600
MAX_ACTIONS = 75


class TaskGrant:
    def __init__(self, *, clock=None, approve_sensitive=None):
        self.clock = clock or time.monotonic
        self.approve_sensitive = approve_sensitive
        self._lock = threading.RLock()
        self._active = False
        self._expires = 0.0
        self._remaining = 0
        self._task = ''
        self._app_id = ''
        self._stopped = False

    def activate(self, task, app_id, *, seconds=300):
        """ONLY a trusted UI should call this after the user clicks Allow."""
        if (not isinstance(task, str) or not task.strip()
                or len(task) > 300 or not isinstance(app_id, str)
                or not app_id or len(app_id) > 200 or
                type(seconds) is not int or not 1 <= seconds <= MAX_SECONDS):
            raise ValueError('Choose an app, task and short approval duration')
        with self._lock:
            self._active = True
            self._expires = self.clock() + seconds
            self._remaining = MAX_ACTIONS
            self._task = task.strip()
            self._app_id = app_id
            self._stopped = False

    def stop(self):
        with self._lock:
            self._active = False
            self._stopped = True
            self._remaining = 0

    def status(self):
        with self._lock:
            valid = self._active and not self._stopped and self.clock() < self._expires
            return {
                'active': valid,
                'stopped': self._stopped,
                'remaining_seconds': max(0, int(self._expires - self.clock())) if valid else 0,
                'remaining_actions': self._remaining if valid else 0,
                'selected_app_id': self._app_id if valid else '',
                'task': self._task if valid else '',
            }

    def authorize(self, action, preview):
        with self._lock:
            if (not self._active or self._stopped or
                    self.clock() >= self._expires or self._remaining <= 0 or
                    action not in ROUTINE | SENSITIVE):
                return False
            if action == 'app.open' and preview != 'app_id=' + self._app_id:
                return False
            if action in SENSITIVE:
                # This invokes a trusted local on-screen dialog. Callbacks
                # based solely on LLM/speech text must NOT be used here.
                if self.approve_sensitive is None:
                    return False
                if self.approve_sensitive(action, preview) is not True:
                    return False
                if not self._active or self._stopped or self.clock() >= self._expires:
                    return False
            self._remaining -= 1
            return True
