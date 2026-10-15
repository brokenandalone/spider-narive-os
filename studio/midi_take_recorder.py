"""Owner-controlled, in-memory live MIDI take capture for Spider Audio Studio.

A take starts only on an explicit UI action. Record note-on/off timestamp
and velocity, safely terminate sustained notes, and produce the exact same
symbolic Performance model used by the autonomous score player.
No MIDI hardware, microphone, filesystem or sound server access is required.
"""
from __future__ import annotations

from collections import defaultdict, deque
from fractions import Fraction

try:
    from .score_performer import MAX_NOTES, MAX_BEATS, Note, Part, Performance
except ImportError:
    from score_performer import MAX_NOTES, MAX_BEATS, Note, Part, Performance

MAX_RECORD_SECONDS = 180.0
TICKS = 480
INSTRUMENTS = {
    "keys": ("Keyboard", 0),
    "guitar": ("Guitar", 24),
    "bass": ("Bass", 33),
}

class MIDITake:
    def __init__(self, bpm=120):
        if type(bpm) is not int or not 30 <= bpm <= 280:
            raise ValueError("MIDI take tempo must be 30–280 BPM")
        self.bpm = bpm
        self.started = None
        self.stopped = False
        self.active = defaultdict(deque)
        self.notes = []
        self.last_time = None

    def start(self, timestamp):
        if self.started is not None or type(timestamp) not in (float, int):
            raise ValueError("Invalid or repeated MIDI record start")
        self.started = float(timestamp)
        self.last_time = self.started

    def _check_time(self, timestamp):
        if self.started is None or self.stopped:
            raise ValueError("No active MIDI recording")
        if type(timestamp) not in (float, int) or not self.started <= timestamp:
            raise ValueError("MIDI event arrived before the recording began")
        if timestamp - self.started > MAX_RECORD_SECONDS:
            raise ValueError("MIDI recording exceeds 3 minutes")
        if timestamp < self.last_time:
            raise ValueError("MIDI events must be in timestamp order")
        self.last_time = float(timestamp)

    def _beat(self, seconds):
        return Fraction(round(seconds * self.bpm / 60 * TICKS), TICKS)

    def event(self, kind, pitch, velocity, timestamp, instrument="keys"):
        self._check_time(timestamp)
        if instrument not in INSTRUMENTS or kind not in ("note_on", "note_off"):
            raise ValueError("Unrecognized MIDI note or virtual instrument")
        if type(pitch) is not int or not 0 <= pitch <= 127:
            raise ValueError("MIDI note pitch must be 0–127")
        if type(velocity) is not int or not 0 <= velocity <= 127:
            raise ValueError("MIDI velocity must be 0–127")
        key = (instrument, pitch)
        if kind == "note_on" and velocity:
            if len(self.notes) + sum(map(len, self.active.values())) >= MAX_NOTES:
                raise ValueError("MIDI recording exceeds note limit")
            self.active[key].append((float(timestamp), velocity))
        elif self.active[key]:
            note_start, recorded_velocity = self.active[key].popleft()
            self._append_note(instrument, pitch, recorded_velocity, note_start, float(timestamp))

    def _append_note(self, instrument, pitch, velocity, start, end):
        begin = self._beat(start - self.started)
        finish = self._beat(end - self.started)
        if finish <= begin:
            finish = begin + Fraction(1, TICKS)
        self.notes.append((instrument, pitch, begin, finish - begin, velocity))

    def stop(self, timestamp):
        self._check_time(timestamp)
        for (instrument, pitch), notes in list(self.active.items()):
            while notes:
                start, velocity = notes.popleft()
                self._append_note(instrument, pitch, velocity, start, float(timestamp))
        self.active.clear()
        self.stopped = True
        if not self.notes:
            raise ValueError("No MIDI notes were recorded")

    def as_performance(self):
        if not self.stopped or not self.notes:
            raise ValueError("Finish recording at least one note before exporting")
        instruments = [name for name in INSTRUMENTS if any(n[0] == name for n in self.notes)]
        parts = [Part(INSTRUMENTS[kind][0], INSTRUMENTS[kind][1], i)
                 for i, kind in enumerate(instruments)]
        mapping = {name: i for i, name in enumerate(instruments)}
        notes = [
            Note(mapping[kind], pitch, start, duration, velocity)
            for kind, pitch, start, duration, velocity in self.notes
        ]
        end = max(n.start + n.duration for n in notes)
        if end > MAX_BEATS:
            raise ValueError("Recorded take exceeds supported score duration")
        return Performance(
            "Spider Live MIDI Take", self.bpm, parts,
            sorted(notes, key=lambda n: (n.start, n.part, n.pitch)),
            end, ["Timing reflects captured controller events; no quantization applied."],
        ).validated()
