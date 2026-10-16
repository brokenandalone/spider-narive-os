"""Export Spider song patterns as standard MIDI files (SMF format 1).

Pure-Python implementation with no external MIDI dependency. This is file
export for interoperability, NOT live MIDI input or audio recording.
"""
from __future__ import annotations

import os
from pathlib import Path
import struct
import tempfile
try:
    from .instruments_engine import DRUMS, TRACKS
    from .song_arranger_engine import Song
except ImportError:
    from instruments_engine import DRUMS, TRACKS
    from song_arranger_engine import Song

PPQ = 480
TICKS_STEP = PPQ // 4
TICKS_BAR = PPQ * 4
DRUM_NOTES = {"kick": 36, "snare": 38, "hat": 42, "clap": 39}
MELODIC = {"guitar": (0, 24), "bass": (1, 33), "keys": (2, 0)}

def vlq(value):
    if type(value) is not int or not 0 <= value <= 0x0FFFFFFF:
        raise ValueError("MIDI delta out of range")
    parts = [value & 0x7f]
    value >>= 7
    while value:
        parts.insert(0, (value & 0x7f) | 0x80)
        value >>= 7
    return bytes(parts)

def chunk(kind, payload):
    return kind + struct.pack(">I", len(payload)) + payload

def track_bytes(events, track_name, end_tick):
    encoded = bytearray()
    name = track_name.encode("utf-8")[:127]
    events = [(0, 0, b"\xff\x03" + bytes([len(name)]) + name), *events,
              (end_tick, 9, b"\xff\x2f\x00")]
    events.sort(key=lambda item: (item[0], item[1]))
    prev = 0
    for tick, priority, payload in events:
        if tick < prev:
            raise ValueError("MIDI event order invalid")
        encoded.extend(vlq(tick - prev))
        encoded.extend(payload)
        prev = tick
    return chunk(b"MTrk", encoded)

def encode_song_midi(song):
    """Return standards-compliant format-1 MIDI with separate drum/tonal tracks."""
    validated = Song.from_dict(song.as_dict())
    if not validated.bars:
        raise ValueError("Song needs at least one bar for MIDI export")
    tempo = round(60_000_000 / validated.bpm)
    tempo_meta = b"\xff\x51\x03" + tempo.to_bytes(3, "big")
    time_signature = b"\xff\x58\x04\x04\x02\x18\x08"
    end_tick = len(validated.bars) * TICKS_BAR
    tempo_track = track_bytes([(0, 1, time_signature), (0, 2, tempo_meta)],
                              "Spider Tempo", end_tick)
    parts = [chunk(b"MThd", struct.pack(">HHH", 1, len(TRACKS) + 1, PPQ)),
             tempo_track]
    for track in TRACKS:
        channel, program = (9, None) if track in DRUMS else MELODIC[track]
        notes = []
        if program is not None:
            notes.append((0, 0, bytes([0xC0 | channel, program])))
        for barno, bar in enumerate(validated.bars):
            for step, value in enumerate(bar.pattern.events[track]):
                if value is None:
                    continue
                midi = DRUM_NOTES[track] if track in DRUMS else value
                tick = barno * TICKS_BAR + step * TICKS_STEP
                length = 65 if track in DRUMS else 180
                velocity = 108 if track in DRUMS else 96
                notes.extend([
                    (tick, 2, bytes([0x90 | channel, midi, velocity])),
                    (min(tick + length, end_tick), 1, bytes([0x80 | channel, midi, 0]))
                ])
        parts.append(track_bytes(notes, "Spider " + track.title(), end_tick))
    return b"".join(parts)

def write_song_midi(song, destination):
    target = Path(destination)
    if not target.parent.is_dir():
        raise FileNotFoundError("MIDI output directory does not exist")
    data = encode_song_midi(song)
    temporary = None
    try:
        descriptor, temporary = tempfile.mkstemp(
            prefix=".spider-midi-", suffix=".mid.tmp", dir=str(target.parent))
        with os.fdopen(descriptor, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)
