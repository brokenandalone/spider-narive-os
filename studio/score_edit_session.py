"""Non-destructive Spider Score Editor: note events, undo/redo, and local projects.

Exactly rational quarter-note positions are preserved, including imported
tempo maps. Every edit is validated before history changes; a bad operation
cannot partially modify the composition. Saving never writes the source file.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
import json
import os
from pathlib import Path
import tempfile

try:
    from .score_performer import MAX_BEATS, MAX_NOTES, Note, Part, Performance
except ImportError:
    from score_performer import MAX_BEATS, MAX_NOTES, Note, Part, Performance

MAX_PROJECT = 4_000_000
HISTORY = 24
VERSION = 1

def _frac(v):
    if (not isinstance(v, (list, tuple)) or len(v) != 2
            or any(type(x) is not int for x in v)
            or v[1] <= 0 or abs(v[0]) > MAX_BEATS * v[1] * 2):
        raise ValueError("Invalid rational musical time")
    return Fraction(*v)

def _pair(frac):
    return [frac.numerator, frac.denominator]

def _validated_copy(score):
    return deepcopy(score.validated())

def quantized_position(start, subdivision):
    step = Fraction(1, subdivision)
    # Round halves forward instead of Python's surprising bankers rounding.
    count = (start / step) + Fraction(1, 2)
    return int(count // 1) * step

class ScoreEditor:
    def __init__(self, performance):
        self.score = _validated_copy(performance)
        self._undo = []
        self._redo = []

    @property
    def can_undo(self):
        return bool(self._undo)

    @property
    def can_redo(self):
        return bool(self._redo)

    def _commit(self, candidate):
        candidate.validated()
        if candidate == self.score:
            return False
        self._undo.append(_validated_copy(self.score))
        self._undo = self._undo[-HISTORY:]
        self._redo.clear()
        self.score = _validated_copy(candidate)
        return True

    def undo(self):
        if not self._undo:
            return False
        previous = self._undo.pop()
        self._redo.append(_validated_copy(self.score))
        self.score = previous
        return True

    def redo(self):
        if not self._redo:
            return False
        future = self._redo.pop()
        self._undo.append(_validated_copy(self.score))
        self.score = future
        return True

    def edit_note(self, index, *, pitch=None, start=None, duration=None, velocity=None):
        if type(index) is not int or not 0 <= index < len(self.score.notes):
            raise ValueError("Select an existing score note")
        old = self.score.notes[index]
        for v in (start, duration):
            if v is not None and not isinstance(v, Fraction):
                raise ValueError("Note time values must be rational quarter-note beats")
        new = replace(old,
                      pitch=old.pitch if pitch is None else pitch,
                      start=old.start if start is None else start,
                      duration=old.duration if duration is None else duration,
                      velocity=old.velocity if velocity is None else velocity)
        draft = _validated_copy(self.score)
        draft.notes[index] = new
        draft.notes.sort(key=lambda n:(n.start,n.part,n.pitch))
        return self._commit(draft)

    def set_program(self, part_index, program):
        if type(part_index) is not int or not 0 <= part_index < len(self.score.parts):
            raise ValueError("Invalid score part")
        if type(program) is not int or not 0 <= program <= 127:
            raise ValueError("GM instrument program must be 0–127")
        draft = _validated_copy(self.score)
        draft.parts[part_index] = replace(draft.parts[part_index], program=program)
        return self._commit(draft)

    def transpose(self, part_index, semitones):
        if type(part_index) is not int or not 0 <= part_index < len(self.score.parts):
            raise ValueError("Select an existing score part")
        if type(semitones) is not int or not -24 <= semitones <= 24:
            raise ValueError("Transpose by no more than two octaves")
        if self.score.parts[part_index].channel == 9:
            raise ValueError("Drum notes use kit mappings and cannot be transposed")
        draft = _validated_copy(self.score)
        draft.notes = [
            replace(n, pitch=n.pitch+semitones) if n.part == part_index else n
            for n in draft.notes]
        return self._commit(draft)

    def quantize(self, subdivision=4, strength=100, part_index=None):
        """Move onsets toward a rhythmic grid; keep each written note length."""
        if type(subdivision) is not int or subdivision not in (1,2,3,4,6,8,12,16):
            raise ValueError("Supported grids are quarter to 64th/triplets")
        if type(strength) is not int or not 0 <= strength <= 100:
            raise ValueError("Quantize strength must be 0–100")
        if part_index is not None and (type(part_index) is not int or
                                       not 0 <= part_index < len(self.score.parts)):
            raise ValueError("Invalid part selection")
        draft = _validated_copy(self.score)
        adjusted = []
        for note in draft.notes:
            if part_index is not None and note.part != part_index:
                adjusted.append(note)
                continue
            target = quantized_position(note.start, subdivision)
            new_start = note.start + (target-note.start) * Fraction(strength, 100)
            new_start = min(new_start, draft.beats - Fraction(1,480))
            # Preserve written length unless a move would cross the score end.
            duration = min(note.duration, draft.beats - new_start)
            adjusted.append(replace(note, start=new_start, duration=duration))
        draft.notes = sorted(adjusted, key=lambda n:(n.start,n.part,n.pitch))
        return self._commit(draft)

    def set_tempo(self, bpm):
        if type(bpm) is not int or not 30 <= bpm <= 280:
            raise ValueError("Tempo outside 30–280 BPM")
        return self._commit(replace(self.score, bpm=bpm))

    def delete_note(self, index):
        if len(self.score.notes) == 1:
            raise ValueError("Cannot delete the final note of a score")
        if type(index) is not int or not 0 <= index < len(self.score.notes):
            raise ValueError("No selected note")
        draft = _validated_copy(self.score)
        draft.notes.pop(index)
        return self._commit(draft)

def encode_project(performance, mix=None):
    """JSON-only score and mix settings, no samples or system instructions."""
    p = performance.validated()
    data = {
        "format":"spider-audio-score-session", "version":VERSION,
        "title":p.title, "bpm":p.bpm,
        "meter":list(p.meter),
        "parts":[{"name":part.name,"program":part.program,"channel":part.channel}
                 for part in p.parts],
        "notes":[[n.part,n.pitch,*_pair(n.start),*_pair(n.duration),n.velocity]
                 for n in p.notes],
        "beats":_pair(p.beats),
        "tempo_changes":[[_pair(beat),bpm] for beat,bpm in p.tempo_changes],
        "mix":mix or {},
        # Do not persist origin/source paths or account-specific file locations.
    }
    blob = json.dumps(data,ensure_ascii=False,separators=(",",":"))
    if len(blob.encode("utf-8")) > MAX_PROJECT:
        raise ValueError("Score session exceeds size limit")
    return blob

def decode_project(source):
    if isinstance(source, bytes):
        if len(source) > MAX_PROJECT:
            raise ValueError("Score session exceeds size limit")
        source = source.decode("utf-8")
    if not isinstance(source,str) or len(source.encode("utf-8")) > MAX_PROJECT:
        raise ValueError("Invalid score session size")
    data = json.loads(source)
    if not isinstance(data,dict) or data.get("format") != "spider-audio-score-session" or data.get("version") != VERSION:
        raise ValueError("Not a supported Spider Score Session")
    if not isinstance(data.get("parts"),list) or not 1 <= len(data["parts"]) <= 15:
        raise ValueError("Invalid session parts")
    if not isinstance(data.get("notes"),list) or not 1 <= len(data["notes"]) <= MAX_NOTES:
        raise ValueError("Invalid session note count")
    parts = [Part(str(p["name"]),p["program"],p["channel"]) for p in data["parts"]]
    notes=[]
    for n in data["notes"]:
        if not isinstance(n,list) or len(n) != 7:
            raise ValueError("Malformed saved note")
        notes.append(Note(n[0],n[1],_frac(n[2:4]),_frac(n[4:6]),n[6]))
    changes = [(_frac(x[0]),x[1]) for x in data.get("tempo_changes",[])]
    score = Performance(data["title"],data["bpm"],parts,notes,
                        _frac(data["beats"]),meter=tuple(data["meter"]),
                        tempo_changes=changes).validated()
    if (any(type(p.program) is not int or not 0 <= p.program <= 127 or
            type(p.channel) is not int or not 0 <= p.channel <= 15 or
            not isinstance(p.name,str) or not 1 <= len(p.name) <= 80
            for p in score.parts)):
        raise ValueError("Invalid saved instrument definition")
    mixer = data.get("mix",{})
    if not isinstance(mixer,dict) or len(mixer)>24:
        raise ValueError("Invalid score mixer settings")
    return score,mixer

def save_project(path, performance, mix=None):
    target=Path(path)
    if not target.parent.is_dir():
        raise FileNotFoundError("Score session folder does not exist")
    if performance.origin is not None and target.resolve()==performance.origin.resolve():
        raise ValueError("Refusing to overwrite original imported score")
    raw=encode_project(performance,mix).encode("utf-8")
    tmp=None
    try:
        fd,tmp=tempfile.mkstemp(prefix=".spider-session-",suffix=".tmp",dir=str(target.parent))
        with os.fdopen(fd,"wb") as out:
            out.write(raw)
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp,target)
    finally:
        if tmp is not None:
            Path(tmp).unlink(missing_ok=True)

def load_project(path):
    target=Path(path)
    if target.stat().st_size>MAX_PROJECT:
        raise ValueError("Score session file is too large")
    return decode_project(target.read_bytes())
