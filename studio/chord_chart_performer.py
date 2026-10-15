"""Generate a playable rhythm-section arrangement from a chord-only chart.

This deliberately creates a *new generic backing performance*, not a claim to
transcribe the original song, performance or copyrighted recording.
"""
from __future__ import annotations

from fractions import Fraction
import re
try:
    from .score_performer import MAX_NOTES, Note, Part, Performance
except ImportError:
    from score_performer import MAX_NOTES, Note, Part, Performance

PITCH = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
CHORD = re.compile(r"^([A-G])([#b]?)(maj7|m7|dim|aug|sus4|sus2|add9|m|7)?(?:/([A-G])([#b]?))?$")
QUALITY = {
    "": (0, 4, 7), "m": (0, 3, 7),
    "7": (0, 4, 7, 10), "maj7": (0, 4, 7, 11),
    "m7": (0, 3, 7, 10), "dim": (0, 3, 6),
    "aug": (0, 4, 8), "sus4": (0, 5, 7),
    "sus2": (0, 2, 7), "add9": (0, 4, 7, 14),
}

def _pitch(key, accidental):
    return (PITCH[key] + (1 if accidental == "#" else -1 if accidental == "b" else 0)) % 12

def _fit(midi, low, high):
    while midi < low:
        midi += 12
    while midi > high:
        midi -= 12
    return midi

def parse_chord_chart(text, bpm=110):
    """One chord symbol represents one 4-beat bar; '|' and lines are separators.

    Section labels in [brackets] are permitted, but lyrics are not silently
    discarded. A slash chord uses its specified bass note for the low root.
    """
    if not isinstance(text, str) or not 1 <= len(text.encode("utf-8")) <= 20000:
        raise ValueError("Chord chart must be plain text under 20 KB")
    if type(bpm) is not int or not 30 <= bpm <= 280:
        raise ValueError("Chord tempo must be 30–280 BPM")
    cleaned = []
    for line in text.splitlines():
        if line.strip().startswith("[") and line.strip().endswith("]"):
            continue
        cleaned.extend(line.replace("|", " ").split())
    if not 1 <= len(cleaned) <= 128:
        raise ValueError("Provide 1 to 128 chord symbols")
    parsed = []
    for token in cleaned:
        match = CHORD.fullmatch(token)
        if not match:
            raise ValueError(
                f"Unrecognized chord {token!r}; enter chord symbols only, such as Am F C G or G7 Bbmaj7")
        key, accidental, kind, basskey, bassacc = match.groups()
        root = _pitch(key, accidental)
        bass = root if basskey is None else _pitch(basskey, bassacc)
        parsed.append((root, bass, QUALITY[kind or ""]))
    parts = [Part("Rhythm Guitar", 25, 0), Part("Bass", 33, 1),
             Part("Keys", 0, 2), Part("Drum Machine", 0, 9)]
    notes = []
    def add(part, pitch, start, duration, velocity):
        notes.append(Note(part, pitch, Fraction(start), Fraction(duration), velocity))
    for bar, (root, bass, intervals) in enumerate(parsed):
        start = Fraction(bar * 4)
        # Spread voices without voice-leading jumps; the SoundFont supplies
        # instrument identity, and these patterns are entirely new material.
        chord = sorted({_fit(60 + root + interval, 56, 83) for interval in intervals})
        for pulse, velocity in [(0, 80), (Fraction(3, 2), 62), (2, 85), (3, 70)]:
            for index, midi in enumerate(chord):
                add(0, midi, start + pulse + Fraction(index, 64),
                    Fraction(7, 16), max(1, velocity - index * 3))
        bass_note = _fit(36 + bass, 28, 47)
        add(1, bass_note, start, Fraction(3, 2), 96)
        add(1, bass_note, start + 2, Fraction(3, 2), 89)
        for midi in chord:
            add(2, midi, start, Fraction(15, 8), 54)
            add(2, midi, start + 2, Fraction(15, 8), 50)
        for hit in range(8):
            add(3, 42, start + Fraction(hit, 2), Fraction(1, 8), 64 if hit % 2 else 79)
        for beat in (0, 2):
            add(3, 36, start + beat, Fraction(1, 8), 104)
        for beat in (1, 3):
            add(3, 38, start + beat, Fraction(1, 8), 97)
        if len(notes) > MAX_NOTES:
            raise ValueError("Chord chart exceeds note allocation")
    beats = Fraction(4 * len(parsed))
    return Performance("Spider Chord-Chart Arrangement", bpm, parts, notes,
                       beats, [
                           "Generated new generic accompaniment from chord symbols; not a transcription of an original recording.",
                           "One chord is treated as one 4/4 bar; no exact strumming or song-specific rhythm was supplied."
                       ]).validated()
