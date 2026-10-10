"""Monotonic voice turn cancellation for Webbie.

A STOP spoken while the model is generating a reply invalidates the turn
so no late TTS can start talking again. Never grants microphone access.
"""
import threading


class VoiceTurnTracker:
    def __init__(self):
        self._lock = threading.RLock()
        self._generation = 0

    def start(self):
        with self._lock:
            return self._generation

    def interrupted(self):
        with self._lock:
            self._generation += 1
            return self._generation

    def current(self, generation):
        with self._lock:
            return generation == self._generation
