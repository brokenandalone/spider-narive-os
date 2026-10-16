"""Non-destructive, offline PCM WAV clip edits for Spider Audio Studio.

Every operation reads an immutable imported source buffer; trim, fades,
gain and reverse are merely editor settings until exported to a NEW file.
No resampling, compressed format decoding or direct device recording yet.
"""
from __future__ import annotations

from array import array
from dataclasses import dataclass, replace
import math
import os
from pathlib import Path
import sys
import tempfile
import wave

MAX_IMPORT_BYTES = 48_000_000
MAX_DURATION = 180.0

@dataclass(frozen=True)
class AudioClip:
    original: Path
    rate: int
    channels: int
    source: bytes
    start: int = 0
    end: int = 0
    gain_db: int = 0
    fade_in_ms: int = 0
    fade_out_ms: int = 0
    reverse: bool = False

    @property
    def total_frames(self):
        return len(self.source) // (self.channels * 2)

    @property
    def duration(self):
        return (self.end - self.start) / self.rate

    def validate(self):
        if not isinstance(self.original, Path):
            raise ValueError("Clip source must be a file path")
        if type(self.rate) is not int or not 8000 <= self.rate <= 96000:
            raise ValueError("Unsupported sample rate")
        if type(self.channels) is not int or self.channels not in (1, 2):
            raise ValueError("Only mono or stereo PCM audio is supported")
        if len(self.source) % (self.channels * 2):
            raise ValueError("Malformed PCM frame buffer")
        if len(self.source) > MAX_IMPORT_BYTES or self.total_frames > self.rate * MAX_DURATION:
            raise ValueError("Clip exceeds the safe editor size")
        if type(self.start) is not int or type(self.end) is not int or not 0 <= self.start < self.end <= self.total_frames:
            raise ValueError("Trim range must be inside the source")
        if type(self.gain_db) is not int or not -36 <= self.gain_db <= 12:
            raise ValueError("Gain must be between -36 and +12 dB")
        if (type(self.fade_in_ms) is not int or type(self.fade_out_ms) is not int
            or not 0 <= self.fade_in_ms <= 10000 or not 0 <= self.fade_out_ms <= 10000):
            raise ValueError("Fade length must be between 0 and 10 seconds")
        if type(self.reverse) is not bool:
            raise ValueError("Reverse must be a switch")
        return self

    def edited(self, **changes):
        return replace(self, **changes).validate()

def import_wav(filename):
    target = Path(filename)
    if target.stat().st_size > MAX_IMPORT_BYTES + 1024 * 1024:
        raise ValueError("File exceeds 48 MB prototype editor limit")
    with wave.open(str(target), "rb") as reader:
        if reader.getcomptype() != "NONE" or reader.getsampwidth() != 2:
            raise ValueError("Only uncompressed 16-bit PCM WAV is supported")
        channels = reader.getnchannels()
        rate = reader.getframerate()
        frames = reader.getnframes()
        if channels not in (1, 2) or not 8000 <= rate <= 96000 or frames > rate * MAX_DURATION:
            raise ValueError("Unsupported channel count, sample rate or duration")
        source = reader.readframes(frames)
    return AudioClip(target, rate, channels, source, end=frames).validate()

def render_clip(clip):
    """Render edited 16-bit PCM bytes, preserving source channels and rate."""
    clip.validate()
    samples = array("h")
    samples.frombytes(clip.source)
    if sys.byteorder != "little":
        samples.byteswap()
    count = clip.end - clip.start
    gain = 10.0 ** (clip.gain_db / 20.0)
    fade_in = min(count, round(clip.fade_in_ms * clip.rate / 1000))
    fade_out = min(count, round(clip.fade_out_ms * clip.rate / 1000))
    edited = array("h")
    for index in range(count):
        frame = clip.end - 1 - index if clip.reverse else clip.start + index
        envelope = gain
        if fade_in:
            envelope *= min(1.0, index / fade_in)
        if fade_out:
            envelope *= min(1.0, (count - 1 - index) / fade_out)
        for channel in range(clip.channels):
            value = samples[frame * clip.channels + channel]
            edited.append(max(-32768, min(32767, round(value * envelope))))
    if sys.byteorder != "little":
        edited.byteswap()
    return edited.tobytes()

def outline(clip, points=200):
    """Return peak ranges for a source clip, bounded regardless of file length."""
    clip.validate()
    if type(points) is not int or not 8 <= points <= 1200:
        raise ValueError("Waveform resolution out of range")
    data = array("h")
    data.frombytes(clip.source)
    if sys.byteorder != "little":
        data.byteswap()
    frames = clip.end - clip.start
    results = []
    for bin_index in range(points):
        a = clip.start + bin_index * frames // points
        b = clip.start + (bin_index + 1) * frames // points
        if b <= a:
            results.append((0.0, 0.0))
            continue
        minimum, maximum = 32767, -32768
        # Sample up to 512 frames per bin, for very long tracks.
        stride = max(1, (b - a) // 512)
        for frame in range(a, b, stride):
            for channel in range(clip.channels):
                v = data[frame * clip.channels + channel]
                minimum = min(minimum, v)
                maximum = max(maximum, v)
        results.append((minimum / 32768, maximum / 32768))
    return results[::-1] if clip.reverse else results

def export_clip(clip, destination):
    clip.validate()
    target = Path(destination)
    if target.resolve() == clip.original.resolve():
        raise ValueError("Refusing to overwrite the imported original audio")
    if not target.parent.is_dir():
        raise FileNotFoundError("Output directory does not exist")
    pcm = render_clip(clip)
    temp = None
    try:
        descriptor, temp = tempfile.mkstemp(
            prefix=".spider-clip-", suffix=".wav.tmp", dir=str(target.parent))
        with os.fdopen(descriptor, "wb") as output_file:
            with wave.open(output_file, "wb") as writer:
                writer.setnchannels(clip.channels)
                writer.setsampwidth(2)
                writer.setframerate(clip.rate)
                writer.writeframes(pcm)
            output_file.flush()
            os.fsync(output_file.fileno())
        os.replace(temp, target)
    finally:
        if temp is not None:
            Path(temp).unlink(missing_ok=True)
