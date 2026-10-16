"""Bounded, dependency-free Standard MIDI File importer for Spider Auto Performer.

Supports SMF 0/1, running status, note-on/off, track labels, GM program,
percussion channel, velocities, tempo changes and initial meter. Never opens
ports or executes content. System-exclusive events are ignored, not executed.
"""
from __future__ import annotations

from collections import defaultdict, deque
from fractions import Fraction
from pathlib import Path
import struct

try:
    from .score_performer import MAX_BYTES, MAX_NOTES, MAX_PARTS, Note, Part, Performance
except ImportError:
    from score_performer import MAX_BYTES, MAX_NOTES, MAX_PARTS, Note, Part, Performance

MIDI_MAX_BYTES = 2_000_000
MIDI_MAX_EVENTS = 80_000
GM_GUITARS = range(24, 32)
GM_BASSES = range(32, 40)
GM_PIANOS = range(0, 8)

def _vlq(data, pos, end):
    value = 0
    for _ in range(4):
        if pos >= end:
            raise ValueError("Truncated MIDI variable-length number")
        byte = data[pos]
        pos += 1
        value = (value << 7) | (byte & 127)
        if not byte & 128:
            return value, pos
    raise ValueError("MIDI variable-length number exceeds four bytes")

def _track_events(data, start, end, track_id):
    pos = start
    absolute = 0
    previous_status = None
    count = 0
    name = None
    events = []
    while pos < end:
        delta, pos = _vlq(data, pos, end)
        absolute += delta
        count += 1
        if count > MIDI_MAX_EVENTS:
            raise ValueError("Too many events on one MIDI track")
        if pos >= end:
            raise ValueError("Truncated MIDI event")
        b = data[pos]
        if b >= 0x80:
            status = b
            pos += 1
            if 0x80 <= status < 0xF0:
                previous_status = status
            else:
                previous_status = None
        elif previous_status is not None:
            status = previous_status
        else:
            raise ValueError("MIDI running status without preceding message")
        if status == 0xFF:
            if pos >= end:
                raise ValueError("Truncated MIDI meta event")
            kind = data[pos]
            pos += 1
            length, pos = _vlq(data, pos, end)
            if pos + length > end:
                raise ValueError("Truncated MIDI meta payload")
            payload = data[pos:pos+length]
            pos += length
            if kind == 0x03:
                name = payload.decode("utf-8", "replace")[:80]
            elif kind in (0x51, 0x58):
                if (kind == 0x51 and length != 3 or
                        kind == 0x58 and length != 4):
                    raise ValueError("Malformed MIDI tempo/meter event")
                events.append((absolute, "tempo" if kind == 0x51 else "meter", payload, track_id))
            elif kind == 0x2F:
                break
        elif status in (0xF0, 0xF7):
            length, pos = _vlq(data, pos, end)
            if pos + length > end:
                raise ValueError("Truncated system-exclusive event")
            pos += length
        elif 0x80 <= status <= 0xEF:
            kind = status & 0xF0
            channel = status & 0x0F
            size = 1 if kind in (0xC0, 0xD0) else 2
            if pos+size > end:
                raise ValueError("Truncated MIDI channel message")
            payload = data[pos:pos+size]
            if any(byte >= 128 for byte in payload):
                raise ValueError("Malformed MIDI data byte")
            pos += size
            if kind in (0x80, 0x90, 0xC0, 0xB0):
                events.append((absolute, channel, kind, bytes(payload), track_id))
        else:
            raise ValueError("Unsupported MIDI system message")
    return name or f"Track {track_id+1}", absolute, events

def import_midi(source):
    """Import MIDI bytes as validated named parts with a preserved tempo map."""
    if not isinstance(source, bytes) or not 14 <= len(source) <= MIDI_MAX_BYTES:
        raise ValueError("MIDI input must be a file up to 2 MB")
    if source[:4] != b"MThd":
        raise ValueError("Not a standard MIDI file")
    header_size = struct.unpack_from(">I", source, 4)[0]
    if header_size < 6 or 8 + header_size > len(source):
        raise ValueError("Malformed MIDI header")
    format_no, count, division = struct.unpack_from(">HHH", source, 8)
    if format_no not in (0, 1) or not 1 <= count <= 32:
        raise ValueError("Only standard MIDI type 0/1 with at most 32 tracks is supported")
    if division & 0x8000 or division == 0:
        raise ValueError("SMPTE timing is not supported; use PPQ-based MIDI")
    pos = 8 + header_size
    tracks = []
    all_events = []
    end_tick = 0
    for index in range(count):
        if pos+8 > len(source) or source[pos:pos+4] != b"MTrk":
            raise ValueError("Missing MIDI track chunk")
        length = struct.unpack_from(">I", source, pos+4)[0]
        start = pos + 8
        end = start + length
        if end > len(source):
            raise ValueError("Truncated MIDI track chunk")
        name, duration, events = _track_events(source, start, end, index)
        tracks.append(name)
        end_tick = max(end_tick, duration)
        all_events.extend(events)
        if len(all_events) > MIDI_MAX_EVENTS:
            raise ValueError("MIDI file exceeds the safe event limit")
        pos = end
    if pos != len(source):
        raise ValueError("MIDI file contains unexpected trailing data")
    tempo_events = sorted((event[0], (event[2][0]<<16 | event[2][1]<<8 | event[2][2]))
                          for event in all_events if len(event) == 4 and event[1] == "tempo")
    tempo = 120
    tempo_changes = []
    for tick, micros in tempo_events:
        if micros <= 0:
            raise ValueError("Invalid MIDI tempo")
        bpm = round(60_000_000 / micros)
        if not 30 <= bpm <= 280:
            raise ValueError("Imported tempo outside 30–280 BPM")
        if tick == 0:
            tempo = bpm
        elif tick < end_tick:
            beat = Fraction(tick, division)
            if tempo_changes and tempo_changes[-1][0] == beat:
                tempo_changes[-1] = (beat, bpm)
            elif not tempo_changes or tempo_changes[-1][1] != bpm:
                tempo_changes.append((beat, bpm))
    meter = (4,4)
    warnings = []
    for tick, kind, payload, _ in (event for event in all_events if len(event) == 4):
        if kind == "meter":
            candidate = (payload[0], 2**payload[1])
            if not 1 <= candidate[0] <= 16 or candidate[1] not in (1,2,4,8,16):
                warnings.append("Unsupported MIDI time signature retained as 4/4")
            elif tick == 0:
                meter = candidate
            elif candidate != meter:
                warnings.append("Time signature changes are not represented by this score editor")
    # Sort real channel messages by tick; at equal tick the input track order
    # is stable. Note off is processed before new note on for the same pitch.
    channel_events = sorted(
        (tick, 0 if kind == 0x80 or kind == 0x90 and payload[1] == 0 else 1,
         tid, channel, kind, payload)
        for tick, channel, kind, payload, tid in (event for event in all_events if len(event) == 5))
    programs = {}
    track_notes = []
    active = defaultdict(deque)
    for tick, _, tid, channel, kind, payload in channel_events:
        key = (tid,channel)
        if kind == 0xC0:
            if key in programs and programs[key] != payload[0]:
                warnings.append("Mid-song MIDI program changes use the first instrument sound")
            programs.setdefault(key, payload[0])
        elif kind in (0x80,0x90):
            pitch = payload[0]
            on = kind == 0x90 and payload[1] > 0
            note_key = (tid,channel,pitch)
            if on:
                active[note_key].append((tick,payload[1]))
            elif active[note_key]:
                start, velocity = active[note_key].popleft()
                track_notes.append((key, pitch, start, max(start+1,tick), velocity))
                if len(track_notes) > MAX_NOTES:
                    raise ValueError("MIDI exceeds the note limit")
            else:
                warnings.append("Orphan MIDI note-off was ignored")
        elif kind == 0xB0 and payload[0] == 64:
            warnings.append("MIDI sustain-pedal events are not yet reproduced")
    if any(active.values()):
        warnings.append("Unclosed MIDI notes were sustained to the end of their track")
        for (tid, channel, pitch), pending in active.items():
            for start, velocity in pending:
                track_notes.append(((tid,channel), pitch, start, max(start+1,end_tick), velocity))
    if not track_notes or len(track_notes) > MAX_NOTES:
        raise ValueError("MIDI contains no supported notes or exceeds safe limits")
    used_keys = sorted({key for key, *_ in track_notes})
    if len(used_keys) > MAX_PARTS:
        raise ValueError("MIDI contains more than 15 simultaneously addressable instruments")
    key_to_part = {key: i for i,key in enumerate(used_keys)}
    parts = []
    for tid, channel in used_keys:
        program = programs.get((tid,channel),0)
        label = tracks[tid]
        if label.startswith("Track ") or label.casefold().startswith("spider auto performer"):
            if channel == 9:
                label = "Drum Set"
            elif program in GM_GUITARS:
                label = "Guitar"
            elif program in GM_BASSES:
                label = "Bass"
            elif program in GM_PIANOS:
                label = "Piano"
        parts.append(Part(label, program, channel if channel == 9 else
                          next((x for x in range(16) if x != 9 and x not in
                                [p.channel for p in parts]), 0)))
    notes = [Note(key_to_part[key], pitch, Fraction(start,division),
                  Fraction(end-start,division),velocity)
             for key,pitch,start,end,velocity in track_notes]
    beat_end = max([Fraction(end_tick,division),
                    *(note.start+note.duration for note in notes)])
    if beat_end > 2048:
        raise ValueError("Imported MIDI is too long")
    return Performance(
        "Imported MIDI Performance", tempo, parts,
        sorted(notes,key=lambda n:(n.start,n.part,n.pitch)),
        beat_end, list(dict.fromkeys(warnings)), meter,
        tempo_changes=tempo_changes).validated()

def import_midi_file(filename):
    target = Path(filename)
    if target.stat().st_size > MIDI_MAX_BYTES:
        raise ValueError("MIDI file exceeds 2 MB")
    performance = import_midi(target.read_bytes())
    performance.origin = target.resolve()
    performance.title = target.stem[:150] or "Imported MIDI Performance"
    return performance
