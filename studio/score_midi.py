"""Standard MIDI output for polyphonic Spider MusicXML / TAB performances."""
from __future__ import annotations

import os
from pathlib import Path
import struct
import tempfile

try:
    from .midi_song_export import track_bytes, chunk
    from .score_performer import Performance
except ImportError:
    from midi_song_export import track_bytes, chunk
    from score_performer import Performance

PPQ = 480

def _tick(beat):
    return round(beat * PPQ)

def encode_performance_midi(performance):
    p = performance.validated()
    tempo = round(60_000_000 / p.bpm)
    if not 1 <= tempo < 2**24:
        raise ValueError("Unsupported tempo")
    end_tick = _tick(p.beats)
    # MIDI time signature denominator is expressed as log2.
    denominator_exponent = p.meter[1].bit_length() - 1
    tempo_events = [
        (0, 0, bytes((0xFF, 0x58, 4, p.meter[0], denominator_exponent, 24, 8))),
        (0, 1, b"\xff\x51\x03" + tempo.to_bytes(3, "big")),
    ]
    output = [chunk(b"MThd", struct.pack(">HHH", 1, len(p.parts) + 1, PPQ)),
              track_bytes(tempo_events, "Spider Auto Performer Tempo", end_tick)]
    for index, part in enumerate(p.parts):
        if not 0 <= part.program <= 127 or not 0 <= part.channel <= 15:
            raise ValueError("Invalid MIDI part")
        events = []
        if part.channel != 9:
            events.append((0, 0, bytes((0xC0 | part.channel, part.program))))
        for note in p.notes:
            if note.part != index:
                continue
            start = _tick(note.start)
            end = max(start + 1, _tick(note.start + note.duration))
            events.append((start, 2, bytes((0x90 | part.channel, note.pitch, note.velocity))))
            events.append((end, 1, bytes((0x80 | part.channel, note.pitch, 0))))
        output.append(track_bytes(events, part.name, end_tick))
    return b"".join(output)

def export_performance_midi(p, destination):
    target = Path(destination)
    if not target.parent.is_dir():
        raise FileNotFoundError("Destination directory missing")
    data = encode_performance_midi(p)
    temporary = None
    try:
        fd, temporary = tempfile.mkstemp(prefix=".spider-score-", suffix=".mid.tmp",
                                         dir=str(target.parent))
        with os.fdopen(fd, "wb") as file:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)
