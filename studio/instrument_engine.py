"""Spider Studio instruments: offline WAV synthesis for drums, guitar, bass and keys.

Self-contained prototype instrument engine. Nothing is sent online, and audio
is not recorded or written until an explicit export. CPU bounded to <=12 s.
This does not replace a professional DAW or installed Ubuntu Studio tools.
"""
from __future__ import annotations

import io
import math
import random
import struct
import wave

RATE = 22050
STEPS = 16
NOTES = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5,
         "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
DRUMS = ("Kick", "Snare", "Closed hat", "Open hat")
INSTRUMENTS = ("Guitar", "Bass", "Keyboard")


def frequency(note, octave=3):
    if note not in NOTES or not 1 <= octave <= 7:
        raise ValueError("Unknown piano note or octave")
    midi = (octave + 1) * 12 + NOTES[note]
    return 440.0 * 2.0 ** ((midi - 69) / 12.0)


def _fade(i, length):
    return min(1.0, i / max(1, int(0.008 * RATE))) * max(
        0.0, min(1.0, (length - i) / max(1, int(0.03 * RATE))))


def _pluck(hz, seconds=1.35, damping=0.996, brightness=0.8, seed=21):
    if hz <= 20 or hz > 12000 or seconds <= 0 or seconds > 12:
        raise ValueError("Invalid plucked note")
    count = int(seconds * RATE)
    period = max(3, round(RATE / hz))
    rng = random.Random(seed + int(hz))
    ring = [rng.uniform(-brightness, brightness) for _ in range(period)]
    result = [0.0] * count
    for index in range(count):
        pos = index % period
        nxt = (pos + 1) % period
        current = ring[pos]
        ring[pos] = (ring[pos] + ring[nxt]) * 0.5 * damping
        result[index] = current * _fade(index, count)
    return result


def note_sound(instrument, note="C", octave=3, seconds=1.35):
    if instrument not in INSTRUMENTS:
        raise ValueError("Unknown instrument")
    if not 0.06 <= seconds <= 12:
        raise ValueError("Invalid note duration")
    hz = frequency(note, octave)
    count = int(seconds * RATE)
    if instrument == "Guitar":
        return _pluck(hz, seconds, 0.997, 0.76, seed=38)
    if instrument == "Bass":
        return _pluck(hz, seconds, 0.9987, 0.75, seed=82)
    # A harmonic keyboard voice with slight attack and soft release.
    return [
        (0.51 * math.sin(math.tau * hz * i / RATE)
         + 0.21 * math.sin(math.tau * hz * 2 * i / RATE)
         + 0.10 * math.sin(math.tau * hz * 3 * i / RATE))
        * math.exp(-0.75 * i / RATE) * _fade(i, count)
        for i in range(count)
    ]


def drum_sound(kind, seconds=0.42, seed=137):
    if kind not in DRUMS or not 0.08 <= seconds <= 1.0:
        raise ValueError("Unknown drum voice")
    count = int(RATE * seconds)
    rng = random.Random(seed + DRUMS.index(kind))
    signal = []
    phase = 0.0
    for i in range(count):
        t = i / RATE
        if kind == "Kick":
            hz = 55 + 115 * math.exp(-t * 30)
            phase += math.tau * hz / RATE
            level = 0.86 * math.sin(phase) * math.exp(-t * 14)
        elif kind == "Snare":
            level = ((0.26 * math.sin(math.tau * 185 * t)) +
                     0.63 * rng.uniform(-1, 1)) * math.exp(-t * 22)
        elif kind == "Closed hat":
            level = 0.48 * rng.uniform(-1, 1) * math.exp(-t * 70)
        else:
            level = 0.43 * rng.uniform(-1, 1) * math.exp(-t * 14)
        signal.append(level * _fade(i, count))
    return signal


def demo_pattern():
    return {
        "Kick": [i in (0, 4, 8, 12) for i in range(STEPS)],
        "Snare": [i in (4, 12) for i in range(STEPS)],
        "Closed hat": [i % 2 == 0 for i in range(STEPS)],
        "Open hat": [False] * STEPS,
    }


def _mix_into(mix, sound, start, gain=1.0):
    for offset, sample in enumerate(sound):
        position = start + offset
        if position >= len(mix):
            break
        mix[position] += sample * gain


def render_pattern(pattern, bpm=110, bars=1):
    if not isinstance(bpm, int) or not 45 <= bpm <= 220:
        raise ValueError("Tempo must be 45–220 BPM")
    if not isinstance(bars, int) or not 1 <= bars <= 4:
        raise ValueError("Choose one to four bars")
    if not isinstance(pattern, dict) or set(pattern) != set(DRUMS):
        raise ValueError("Pattern must define four drum voices")
    for name in DRUMS:
        if (not isinstance(pattern[name], (list, tuple)) or
                len(pattern[name]) != STEPS or
                any(not isinstance(entry, bool) for entry in pattern[name])):
            raise ValueError("Pattern contains malformed steps")
    beat = 60 / bpm
    per_step = beat / 4
    sample_count = int((bars * STEPS * per_step + 0.25) * RATE)
    if sample_count > RATE * 24:
        raise ValueError("Requested audio is too long")
    track = [0.0] * sample_count
    # Deterministically vary articulation. Never import MIDI or remote models.
    voices = {name: drum_sound(name) for name in DRUMS}
    for bar in range(bars):
        for step in range(STEPS):
            for name in DRUMS:
                if pattern[name][step]:
                    start = int((bar * STEPS + step) * per_step * RATE)
                    velocity = 0.68 if name in ("Kick", "Snare") else 0.39
                    _mix_into(track, voices[name], start, velocity)
    return track


def _pcm_wav(samples):
    if len(samples) > RATE * 25:
        raise ValueError("Audio limit exceeded")
    peak = max((abs(sample) for sample in samples), default=0.0)
    gain = min(1.0, 0.95 / peak) if peak else 1.0
    data = b"".join(struct.pack("<h", int(max(-1.0, min(1.0, item * gain))
                                          * 32767)) for item in samples)
    with io.BytesIO() as output:
        with wave.open(output, "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(RATE)
            stream.writeframes(data)
        return output.getvalue()


def export_wav(instrument="Keyboard", note="C", octave=3, pattern=None,
               bpm=110, bars=1):
    """Return a standalone, valid WAV; caller alone chooses destination."""
    if instrument == "Drums":
        samples = render_pattern(pattern if pattern is not None else demo_pattern(),
                                 bpm, bars)
    else:
        samples = note_sound(instrument, note, octave)
    return _pcm_wav(samples)
