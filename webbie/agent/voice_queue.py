"""Bounded, cancellable voice-turn queue for the resident Webbie source agent.

The local microphone loop owns this coordinator. It is not an identity verifier,
permission grant, desktop controller, microphone reader, or new TTS process.
Only the most recent correction is retained while a slow model turn finishes.
"""
from __future__ import annotations

import threading
import time


class VoiceTurnCoordinator:
    """Run one voice worker at a time without silently dropping corrections.

    STOP invalidates the active generation and clears any pending command.
    A later corrected command gets a fresh generation and one expiring queue
    slot. Pending turns are rechecked against sleep and cancellation before
    they run. We never spin up concurrent model workers to beat a slow reply.
    """

    def __init__(self, run_command, tracker, *, can_run=None, on_error=None,
                 clock=None, queue_ttl=45, thread_factory=None,
                 on_supersede=None):
        if not callable(run_command):
            raise TypeError("run_command must be callable")
        if not 1 <= queue_ttl <= 45:
            raise ValueError("Queued voice turns must expire within 45 seconds")
        self.run_command = run_command
        self.tracker = tracker
        self.can_run = can_run or (lambda: True)
        self.on_error = on_error
        self.on_supersede = on_supersede
        self.clock = clock or time.monotonic
        self.queue_ttl = queue_ttl
        self.thread_factory = thread_factory or threading.Thread
        self._lock = threading.RLock()
        self._busy = False
        self._pending = None

    def submit(self, command, *, speaker_verified=False):
        """Return 'started', 'queued', or 'ignored'; never grant voice identity."""
        command = str(command or "").strip()
        if not command or not self.can_run():
            return "ignored"
        # Only a separate trusted local verification adapter can set True.
        with self._lock:
            if self._busy:
                # A new command is a correction: invalidate the slow prior
                # answer immediately so it cannot speak after the correction.
                generation = self.tracker.interrupted()
                self._pending = (
                    (command, generation, speaker_verified is True),
                    self.clock() + self.queue_ttl)
                if self.on_supersede is not None:
                    try:
                        self.on_supersede()
                    except Exception:
                        pass
                return "queued"
            item = (command, self.tracker.start(), speaker_verified is True)
            self._busy = True
        self._start_worker(item)
        return "started"

    def cancel(self):
        """Invalidate running/queued voice turns; never authorize a new action."""
        self.tracker.interrupted()
        with self._lock:
            self._pending = None

    def snapshot(self):
        with self._lock:
            return {"busy": self._busy, "queued": self._pending is not None}

    def _start_worker(self, item):
        try:
            worker = self.thread_factory(
                target=self._run_one, args=(item,),
                name="webbie-voice-turn", daemon=True,
            )
            worker.start()
        except Exception:
            with self._lock:
                self._busy = False
                self._pending = None
            raise

    def _run_one(self, item):
        try:
            command, generation, speaker_verified = item
            if self.tracker.current(generation) and self.can_run():
                self.run_command(command, generation, speaker_verified)
        except Exception as error:
            if self.on_error is not None:
                try:
                    self.on_error(error)
                except Exception:
                    pass
        finally:
            next_item = None
            with self._lock:
                queued = self._pending
                self._pending = None
                if queued is not None:
                    candidate, expires_at = queued
                    if (self.clock() < expires_at
                            and self.tracker.current(candidate[1])
                            and self.can_run()):
                        next_item = candidate
                if next_item is None:
                    self._busy = False
            if next_item is not None:
                self._start_worker(next_item)
