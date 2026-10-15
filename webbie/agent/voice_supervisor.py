"""Bounded retry supervisor for Webbie's existing voice listener.

Never records audio, changes device settings, restarts the service, or authorizes
a speaker. Merely retries the installed listener if it exits unexpectedly.
"""
from __future__ import annotations
import time


class VoiceSupervisor:
    def __init__(self, listener, should_continue, *, notify=None,
                 clock=None, sleeper=None, min_delay=3, max_delay=60):
        if not callable(listener) or not callable(should_continue):
            raise TypeError("VoiceSupervisor needs listener and lifecycle callbacks")
        if not (1 <= min_delay <= max_delay <= 120):
            raise ValueError("Unsafe voice retry interval")
        self.listener = listener
        self.should_continue = should_continue
        self.notify = notify
        self.clock = clock or time.monotonic
        self.sleeper = sleeper or time.sleep
        self.min_delay = min_delay
        self.max_delay = max_delay

    def serve(self):
        delay = self.min_delay
        while self.should_continue():
            started = self.clock()
            try:
                self.listener()
                failure = "listener_exited"
            except Exception:
                # Do not include exception text: installed paths, transcripts
                # and user information may occur in error messages.
                failure = "listener_error"
            if not self.should_continue():
                return
            duration = max(0, self.clock() - started)
            delay = self.min_delay if duration >= 120 else delay
            if self.notify is not None:
                try:
                    self.notify(failure, delay)
                except Exception:
                    pass
            # Sleep in small pieces so shutdown remains responsive.
            remaining = delay
            while self.should_continue() and remaining > 0:
                step = min(1, remaining)
                self.sleeper(step)
                remaining -= step
            delay = min(self.max_delay, delay * 2)
