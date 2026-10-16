"""Deterministic expressive timing/dynamics for Spider's autonomous musicians.

The score remains immutable to callers. Transformations are bounded, reversible
by re-running the original, and never invent or delete a written pitch. This
changes how a note is performed, NOT the musical composition.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction
import hashlib

try:
    from .score_performer import Note, Performance
except ImportError:
    from score_performer import Note, Performance

GROOVES = ("As written", "Natural player", "Behind the beat", "Swing 60%", "Driving rock")
MAX_STRUM_MS = 45

@dataclass(frozen=True)
class Expression:
    groove: str = "Natural player"
    energy: int = 72
    strum_ms: int = 9
    seed: int = 313

    def validate(self):
        if self.groove not in GROOVES:
            raise ValueError("Unknown musical performance groove")
        if type(self.energy) is not int or not 0 <= self.energy <= 100:
            raise ValueError("Performance energy must be 0 to 100")
        if type(self.strum_ms) is not int or not 0 <= self.strum_ms <= MAX_STRUM_MS:
            raise ValueError("Guitar strum spread must be 0 to 45 milliseconds")
        if type(self.seed) is not int or not 0 <= self.seed <= 2**32 - 1:
            raise ValueError("Invalid reproducible performance seed")
        return self

def _rand(seed, *parts):
    """Stable signed variation; no global random state or runtime hash salt."""
    key = ("|".join(str(p) for p in (seed, *parts))).encode("utf-8")
    n = int.from_bytes(hashlib.blake2s(key, digest_size=4).digest(), "little")
    return (n % 2001 - 1000) / 1000

def _kind(name):
    name = name.casefold()
    if "drum" in name or "percussion" in name:
        return "drums"
    if "guitar" in name:
        return "guitar"
    if "bass" in name:
        return "bass"
    return "other"

def _tempo_at(score, beat):
    tempo = score.bpm
    for start, value in score.tempo_changes:
        if start > beat:
            break
        tempo = value
    return tempo

def express(performance: Performance, expression: Expression = Expression()):
    """Return the same written pitches with expressive timing and velocity.

    A controlled, repeatable process: swing delays eighth offbeats, guitar
    chords are rolled on selected instruments, and music breathes through
    modest performance-level offsets. "As written" at energy=75/strum=0 is
    bit-identical to source notes.
    """
    score = performance.validated()
    config = expression.validate()
    # 75 is the neutral energy; values above/below scale source velocities.
    energy_gain = 0.55 + (config.energy / 75) * 0.45
    offsets = {}
    if config.strum_ms:
        # Roll simultaneous guitar chord tones, not every melody note.
        grouped = {}
        for i, n in enumerate(score.notes):
            if _kind(score.parts[n.part].name) == "guitar":
                grouped.setdefault((n.part, n.start), []).append(i)
        for (_, onset), indices in grouped.items():
            if len(indices) < 2:
                continue
            sorted_notes = sorted(indices, key=lambda i: score.notes[i].pitch)
            # Odd groupings strum upward to avoid robotic repetition.
            if (onset.numerator // max(1, onset.denominator)) % 2:
                sorted_notes.reverse()
            for rank, i in enumerate(sorted_notes):
                offsets[i] = (Fraction(config.strum_ms * rank, 1000) *
                              _tempo_at(score, onset) / 60)
    out = []
    for index, note in enumerate(score.notes):
        instrument = _kind(score.parts[note.part].name)
        start = note.start
        duration = note.duration
        current_tempo = _tempo_at(score, start)
        delta = offsets.get(index, Fraction(0))
        variability = _rand(config.seed, note.part, note.start, note.pitch, index)
        if config.groove == "Natural player":
            delta += Fraction(round(variability * 12), 1000) * current_tempo / 60
        elif config.groove == "Behind the beat":
            delta += Fraction(24 + round(variability * 7), 1000) * current_tempo / 60
        elif config.groove == "Swing 60%":
            # Eighth-note offbeat moves from beat fraction .5 to .6.
            if (start % 1) == Fraction(1, 2):
                delta += Fraction(1, 10)
            delta += Fraction(round(variability * 4), 1000) * current_tempo / 60
        elif config.groove == "Driving rock":
            if instrument in ("drums", "bass"):
                delta -= Fraction(5, 1000) * current_tempo / 60
            delta += Fraction(round(variability * 5), 1000) * current_tempo / 60
        start = max(Fraction(0), min(score.beats - Fraction(1, 480), start + delta))
        duration = min(duration, score.beats - start)
        if duration <= 0:
            raise ValueError("Expression settings produced an invalid note length")
        variation = 0 if config.groove == "As written" else round(variability * 7)
        velocity = round(note.velocity * energy_gain + variation)
        if config.groove == "Driving rock" and instrument in ("drums", "guitar"):
            velocity += 6
        velocity = max(1, min(127, velocity))
        out.append(Note(note.part, note.pitch, start, duration, velocity))
    return replace(
        score,
        notes=sorted(out, key=lambda n: (n.start, n.part, n.pitch)),
        warnings=list(score.warnings),
        parts=list(score.parts),
    ).validated()
