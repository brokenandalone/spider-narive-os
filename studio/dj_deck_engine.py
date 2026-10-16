"""Two-deck DJ mix/bounce engine, independent of Nova or Mixxx.

Crossfades uncompressed source WAVs at their native sample rate. Streaming
conversion limits working memory. Tempo analysis, beatmatching, cue pads and
external controllers are NOT part of this prototype.
"""
from __future__ import annotations

from array import array
import math
import os
from pathlib import Path
import struct
import sys
import tempfile
import wave

try:
    from .waveform_edit_engine import AudioClip
except ImportError:
    from waveform_edit_engine import AudioClip

BLOCK_FRAMES = 4096

def _validate(a, b, cross, gain_a, gain_b):
    if a is None and b is None:
        raise ValueError("Load at least one WAV deck")
    for clip in (a, b):
        if clip is not None:
            if not isinstance(clip, AudioClip):
                raise TypeError("Deck audio must be an imported PCM clip")
            clip.validate()
    if a is not None and b is not None and a.rate != b.rate:
        raise ValueError("Decks must have matching sample rates (resampling is not built yet)")
    if type(cross) is not int or not -100 <= cross <= 100:
        raise ValueError("Crossfader must be between -100 and 100")
    if any(type(value) is not int or not 0 <= value <= 100 for value in (gain_a, gain_b)):
        raise ValueError("Deck gains must be 0 to 100")
    return (a or b).rate

def _read(clip, index, channel):
    if clip is None or index >= clip.end - clip.start:
        return 0.0
    frame = clip.end - 1 - index if clip.reverse else clip.start + index
    chan = min(channel, clip.channels - 1)
    return struct.unpack_from("<h", clip.source, (frame * clip.channels + chan) * 2)[0] / 32768

def render_deck_chunks(a, b, cross=0, gain_a=100, gain_b=100,
                       limit_frames=None):
    """Yield 2-channel signed 16-bit PCM blocks for a static crossfader setting."""
    rate = _validate(a, b, cross, gain_a, gain_b)
    total = max((clip.end - clip.start) if clip else 0 for clip in (a, b))
    if limit_frames is not None:
        if type(limit_frames) is not int or not 1 <= limit_frames <= rate * 180:
            raise ValueError("Invalid preview frame limit")
        total = min(total, limit_frames)
    angle = math.pi * (cross + 100) / 400
    coeff_a = gain_a / 100 * math.cos(angle)
    coeff_b = gain_b / 100 * math.sin(angle)
    for start in range(0, total, BLOCK_FRAMES):
        block = array("h")
        for i in range(start, min(start + BLOCK_FRAMES, total)):
            for channel in (0, 1):
                sample = _read(a, i, channel) * coeff_a + _read(b, i, channel) * coeff_b
                block.append(round(math.tanh(sample * .82) * 32767))
        if sys.byteorder != "little":
            block.byteswap()
        yield block.tobytes()

def write_deck_wav(a, b, destination, cross=0, gain_a=100, gain_b=100):
    rate = _validate(a, b, cross, gain_a, gain_b)
    target = Path(destination)
    protected = {clip.original.resolve() for clip in (a, b) if clip is not None}
    if target.resolve() in protected:
        raise ValueError("Refusing to overwrite an imported DJ deck original")
    if not target.parent.is_dir():
        raise FileNotFoundError("Export directory missing")
    temp = None
    try:
        fd, temp = tempfile.mkstemp(prefix=".spider-dj-", suffix=".tmp", dir=str(target.parent))
        with os.fdopen(fd, "wb") as stream:
            with wave.open(stream, "wb") as out:
                out.setnchannels(2)
                out.setsampwidth(2)
                out.setframerate(rate)
                for block in render_deck_chunks(a, b, cross, gain_a, gain_b):
                    out.writeframesraw(block)
                out.writeframes(b"")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, target)
    finally:
        if temp:
            Path(temp).unlink(missing_ok=True)
