"""Safe notation-to-performance engine: MusicXML and guitar/bass ASCII tablature.

Each import becomes a timed, polyphonic MIDI performance with explicit tempo.
Never executes score contents or downloads samples. Supports common partwise
MusicXML notes/rests, chords, voices, ties, backup/forward and tempo directions.
Advanced repeats/ornaments/transpositions are intentionally rejected or noted.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
import re
import xml.etree.ElementTree as ET

MAX_SCORE_BYTES = 2_000_000
MAX_NOTES = 40_000
MAX_TICKS = 480 * 4 * 1000
PPQ = 480
PITCH_CLASSES = {"C":0,"D":2,"E":4,"F":5,"G":7,"A":9,"B":11}
GUITAR_TUNING = (64,59,55,50,45,40)  # top/high-e to low-E
BASS_TUNING = (43,38,33,28)  # G D A E

@dataclass(frozen=True)
class Note:
    start: int
    duration: int
    pitch: int
    velocity: int = 96
    track: int = 0

    def __post_init__(self):
        if (type(self.start) is not int or type(self.duration) is not int
                or self.start < 0 or self.duration < 1 or self.start+self.duration > MAX_TICKS
                or type(self.pitch) is not int or not 0 <= self.pitch <= 127
                or type(self.velocity) is not int or not 1 <= self.velocity <= 127
                or type(self.track) is not int or not 0 <= self.track <= 31):
            raise ValueError("Invalid score note or score exceeds maximum duration")

@dataclass
class Performance:
    title: str = "Spider Score"
    bpm: int = 120
    notes: list[Note] = field(default_factory=list)
    tracks: list[str] = field(default_factory=lambda: ["Instrument"])
    warnings: list[str] = field(default_factory=list)

    def validate(self):
        if type(self.bpm) is not int or not 30 <= self.bpm <= 300:
            raise ValueError("Performance BPM out of range")
        if not 1 <= len(self.tracks) <= 32 or len(self.notes) > MAX_NOTES:
            raise ValueError("Too many score tracks or notes")
        if any(note.track >= len(self.tracks) for note in self.notes):
            raise ValueError("Note references an unavailable track")
        return self

    @property
    def seconds(self):
        return max((n.start+n.duration for n in self.notes), default=0) / PPQ * 60 / self.bpm

def _local(tag):
    return tag.split("}", 1)[-1]

def _child(elem, name):
    return next((c for c in elem if _local(c.tag) == name), None)

def _children(elem, name):
    return [c for c in elem if _local(c.tag) == name]

def _text(elem, name, default=None):
    child = _child(elem, name)
    return child.text.strip() if child is not None and child.text else default

def _pitch(note):
    pitch = _child(note, "pitch")
    if pitch is None:
        return None
    step = _text(pitch, "step")
    if step not in PITCH_CLASSES:
        raise ValueError("Unsupported MusicXML pitch step")
    octave = int(_text(pitch, "octave"))
    alter = int(float(_text(pitch, "alter", "0")))
    midi = (octave + 1) * 12 + PITCH_CLASSES[step] + alter
    if not 0 <= midi <= 127:
        raise ValueError("Pitch outside MIDI range")
    return midi

def import_musicxml(source: str | bytes):
    raw = source.encode("utf-8") if isinstance(source, str) else source
    if not isinstance(raw, bytes) or len(raw) > MAX_SCORE_BYTES:
        raise ValueError("Score exceeds safe import limit")
    if re.search(rb"<!\s*(?:DOCTYPE|ENTITY)", raw, re.I):
        raise ValueError("External entities and document type declarations are not allowed")
    root = ET.fromstring(raw)
    if _local(root.tag) != "score-partwise":
        raise ValueError("Use MusicXML score-partwise documents")
    partlist = _child(root, "part-list")
    name_map = {}
    if partlist is not None:
        for part in _children(partlist, "score-part"):
            name_map[part.attrib.get("id", "")] = _text(part, "part-name", "Part")
    parts = _children(root, "part")
    if not parts or len(parts) > 32:
        raise ValueError("MusicXML requires 1 to 32 parts")
    perf = Performance(tracks=[])
    work = _child(root, "work")
    perf.title = _text(root, "movement-title", None) or (
        _text(work, "work-title", "Spider Score") if work is not None else "Spider Score")
    for track_index, part in enumerate(parts):
        perf.tracks.append(name_map.get(part.attrib.get("id", ""), f"Part {track_index+1}"))
        divisions = 1
        cursor = Fraction(0)
        prev_start = Fraction(0)
        ties = {}
        for measure in _children(part, "measure"):
            measure_start = cursor
            extent = cursor
            for element in measure:
                kind = _local(element.tag)
                if kind == "attributes":
                    div = _text(element, "divisions")
                    if div is not None:
                        divisions = int(div)
                        if not 1 <= divisions <= 100000:
                            raise ValueError("Invalid MusicXML divisions")
                elif kind == "direction":
                    sound = _child(element, "sound")
                    if sound is not None and "tempo" in sound.attrib and track_index == 0:
                        bpm = round(float(sound.attrib["tempo"]))
                        if not 30 <= bpm <= 300:
                            raise ValueError("Tempo out of range")
                        if cursor == 0:
                            perf.bpm = bpm
                        else:
                            perf.warnings.append("Mid-song tempo changes are not supported; first tempo retained")
                elif kind in ("backup", "forward"):
                    duration = int(_text(element, "duration", "0"))
                    movement = Fraction(duration * PPQ, divisions)
                    cursor += -movement if kind == "backup" else movement
                    if cursor < measure_start:
                        raise ValueError("Invalid MusicXML backup outside measure")
                    extent = max(extent, cursor)
                elif kind == "note":
                    duration = int(_text(element, "duration", "0"))
                    if duration < 0:
                        raise ValueError("Negative note duration")
                    ticks = Fraction(duration * PPQ, divisions)
                    chord = _child(element, "chord") is not None
                    start = prev_start if chord else cursor
                    pitch = None if _child(element, "rest") is not None else _pitch(element)
                    if not chord:
                        prev_start = start
                        cursor += ticks
                    extent = max(extent, start + ticks, cursor)
                    if pitch is not None and duration > 0:
                        starts = [t.attrib.get("type") for t in _children(element, "tie")]
                        key = (pitch, _text(element, "voice", "1"))
                        if "start" in starts and "stop" not in starts:
                            ties[key] = [start, ticks]
                            continue
                        if "stop" in starts and key in ties:
                            tie = ties.pop(key)
                            start, ticks = tie[0], tie[1] + ticks
                            if "start" in starts:
                                ties[key] = [start, ticks]
                                continue
                        onset, length = round(start), max(1, round(ticks))
                        perf.notes.append(Note(onset, length, pitch, track=track_index))
                        if len(perf.notes) > MAX_NOTES:
                            raise ValueError("Score exceeds note limit")
                elif kind == "barline":
                    if _child(element, "repeat") is not None:
                        perf.warnings.append("Written repeat markers not unfolded")
            cursor = max(cursor, extent)
        for (pitch, voice), (start, ticks) in ties.items():
            perf.notes.append(Note(round(start), max(1, round(ticks)), pitch, track=track_index))
            perf.warnings.append("An unterminated tie was closed at its last written note")
    perf.notes.sort(key=lambda n: (n.start, n.track, n.pitch))
    return perf.validate()

def import_ascii_tab(source: str, instrument="guitar", bpm=120, beat_columns=4):
    """Parse four/six equally aligned TAB strings, digits as fret positions.

    One text column equals one subdivided beat (default four columns per beat).
    Chords across strings play together; multi-digit fret tokens are accepted.
    Explicit barlines are ignored but preserve timing with all lines aligned.
    """
    if instrument not in ("guitar", "bass"):
        raise ValueError("TAB instrument must be guitar or bass")
    if type(bpm) is not int or not 30 <= bpm <= 300:
        raise ValueError("TAB tempo out of range")
    if type(beat_columns) is not int or not 1 <= beat_columns <= 16:
        raise ValueError("TAB subdivisions out of range")
    if not isinstance(source, str) or len(source) > 120000:
        raise ValueError("TAB text too large")
    tuning = GUITAR_TUNING if instrument == "guitar" else BASS_TUNING
    rows = []
    for line in source.splitlines():
        stripped = line.strip()
        if "|" not in stripped:
            continue
        before, body = stripped.split("|", 1)
        prefix = before.strip().lower()
        if prefix and not re.fullmatch(r"[a-g][#b]?\d?", prefix):
            continue
        rows.append(body.replace("|", ""))
    if len(rows) != len(tuning):
        raise ValueError(f"Expected exactly {len(tuning)} TAB string lines (high string first)")
    widths = [len(row) for row in rows]
    if len(set(widths)) != 1 or widths[0] > 10000:
        raise ValueError("TAB string positions must align and fit 10,000 columns")
    notes = []
    for string_index, row in enumerate(rows):
        for match in re.finditer(r"\d+", row):
            fret = int(match.group())
            if not 0 <= fret <= 24:
                raise ValueError("TAB frets must be 0 to 24")
            pitch = tuning[string_index] + fret
            start = round(match.start() * PPQ / beat_columns)
            duration = max(1, round(PPQ / beat_columns))
            notes.append(Note(start, duration, pitch))
            if len(notes) > MAX_NOTES:
                raise ValueError("TAB exceeds note limit")
    if not notes:
        raise ValueError("No playable fret notes found in TAB")
    return Performance(
        title="Spider " + instrument.title() + " TAB", bpm=bpm,
        notes=sorted(notes, key=lambda n: (n.start, n.pitch)),
        tracks=[instrument.title()],
        warnings=["Rhythm inferred from monospaced TAB columns; original rhythmic notation is not present"]
    ).validate()

def import_score_file(filename, instrument="guitar", bpm=120):
    path = Path(filename)
    if path.stat().st_size > MAX_SCORE_BYTES:
        raise ValueError("Score file too large")
    if path.suffix.lower() in (".musicxml", ".xml"):
        return import_musicxml(path.read_bytes())
    if path.suffix.lower() in (".tab", ".txt"):
        return import_ascii_tab(path.read_text("utf-8"), instrument, bpm)
    raise ValueError("Supported inputs: .musicxml, .xml, .tab, .txt")
