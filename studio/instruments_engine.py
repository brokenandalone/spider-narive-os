"""Independent, offline synthesis and song-pattern model for Spider Audio Studio.

Prototype audio renderer. PCM exports contain original synthesized sounds, not
third-party samples or cloned commercial instruments. No audio device is touched.
"""
from __future__ import annotations

from array import array
from dataclasses import dataclass, field
import json
import math
import random
import sys
import wave

RATE = 44100
STEPS = 16
TRACKS = ("kick", "snare", "hat", "clap", "guitar", "bass", "keys")
DRUMS = frozenset(TRACKS[:4])
DEFAULT_MIDI = {"guitar": 52, "bass": 40, "keys": 60}
PRESETS = {
    "Rock": {"kick": (0, 8), "snare": (4, 12), "hat": (0, 2, 4, 6, 8, 10, 12, 14)},
    "Four on the floor": {"kick": (0, 4, 8, 12), "clap": (4, 12), "hat": (2, 6, 10, 14)},
    "Half time": {"kick": (0, 3, 10), "snare": (8,), "hat": (0, 2, 4, 6, 8, 10, 12, 14)},
}

def frequency(midi):
    if not isinstance(midi, int) or not 24 <= midi <= 96:
        raise ValueError("MIDI note must be between 24 and 96")
    return 440.0 * 2 ** ((midi - 69) / 12)

def note_name(midi):
    return ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")[midi % 12] + str(midi // 12 - 1)

@dataclass
class Pattern:
    bpm: int = 110
    events: dict = field(default_factory=lambda: {k: [None] * STEPS for k in TRACKS})

    def set(self, track, step, pitch=None):
        if track not in TRACKS or not isinstance(step, int) or not 0 <= step < STEPS:
            raise ValueError("Unknown track or sequencer step")
        if track in DRUMS:
            if pitch is not None and pitch is not True:
                raise ValueError("Drum steps have no pitch")
            self.events[track][step] = True
        else:
            if not isinstance(pitch, int):
                raise ValueError("An instrument step needs a MIDI pitch")
            frequency(pitch)
            self.events[track][step] = pitch

    def clear(self, track, step):
        if track not in TRACKS or not isinstance(step, int) or not 0 <= step < STEPS:
            raise ValueError("Unknown track or sequencer step")
        self.events[track][step] = None

    def as_dict(self):
        return {"format": "spider-pattern-1", "bpm": self.bpm,
                "events": {k: list(self.events[k]) for k in TRACKS}}

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or data.get("format") != "spider-pattern-1":
            raise ValueError("Not a Spider Audio Studio pattern")
        bpm = data.get("bpm")
        if type(bpm) is not int or not 40 <= bpm <= 240:
            raise ValueError("Tempo must be between 40 and 240 BPM")
        source = data.get("events")
        if not isinstance(source, dict) or set(source) != set(TRACKS):
            raise ValueError("Pattern track list is invalid")
        result = cls(bpm=bpm)
        for track in TRACKS:
            row = source[track]
            if not isinstance(row, list) or len(row) != STEPS:
                raise ValueError("Pattern must have exactly 16 steps per track")
            for step, value in enumerate(row):
                if value is None:
                    continue
                if track in DRUMS and value is True:
                    result.set(track, step)
                elif track not in DRUMS and type(value) is int:
                    result.set(track, step, value)
                else:
                    raise ValueError("Invalid event data")
        return result

    @classmethod
    def preset(cls, name):
        if name not in PRESETS:
            raise ValueError("Unknown preset")
        result = cls()
        for track, steps in PRESETS[name].items():
            for step in steps:
                result.set(track, step)
        return result

def synthesize(instrument, midi=None, seconds=0.36, rate=RATE):
    """Return signed 16-bit mono PCM, with deterministic procedural timbres."""
    if instrument not in TRACKS:
        raise ValueError("Unknown instrument")
    if not 8000 <= rate <= 96000 or not 0.03 <= seconds <= 3.0:
        raise ValueError("Unsupported sample rate or duration")
    if instrument not in DRUMS:
        f = frequency(midi)
    else:
        f = 0.0
    count = int(seconds * rate)
    samples = array("h")
    rng = random.Random(0x51D3 + (midi or 0) + sum(ord(c) for c in instrument))
    delay = []
    if instrument == "guitar":
        # A small plucked-string delay line: a Karplus-Strong starting point.
        length = max(2, round(rate / f))
        delay = [rng.uniform(-0.75, 0.75) for _ in range(length)]
    last = 0.0
    for n in range(count):
        t = n / rate
        if instrument == "kick":
            phase = 2 * math.pi * (56 * t + 58 * (1 - math.exp(-t * 24)) / 24)
            amp = math.exp(-t * 17) * math.sin(phase)
        elif instrument == "snare":
            noise = rng.uniform(-1, 1)
            last = 0.65 * last + 0.35 * noise
            amp = math.exp(-t * 19) * (0.7 * (noise - last) + 0.3 * math.sin(2 * math.pi * 180 * t))
        elif instrument == "hat":
            noise = rng.uniform(-1, 1)
            last = 0.89 * last + 0.11 * noise
            amp = 1.6 * math.exp(-t * 43) * (noise - last)
        elif instrument == "clap":
            noise = rng.uniform(-1, 1)
            burst = sum(math.exp(-abs(t - center) * 160) for center in (0, .018, .036))
            amp = (burst + math.exp(-t * 26) * .4) * noise * .4
        elif instrument == "guitar":
            i = n % len(delay)
            amp = delay[i] * math.exp(-t * 1.5)
            delay[i] = 0.498 * (delay[i] + delay[(i + 1) % len(delay)])
        elif instrument == "bass":
            attack = min(1.0, t * 125)
            amp = attack * math.exp(-t * 2.8) * (
                .82 * math.sin(2 * math.pi * f * t) +
                .18 * math.sin(2 * math.pi * f * 2 * t))
        else:
            attack = min(1.0, t * 85)
            amp = attack * math.exp(-t * 2.2) * (
                .65 * math.sin(2 * math.pi * f * t) +
                .23 * math.sin(2 * math.pi * f * 2 * t) +
                .12 * math.sin(2 * math.pi * f * 3 * t))
        tail = min(1.0, max(0.0, (seconds - t) * 90))
        samples.append(int(max(-1.0, min(1.0, amp * tail * .8)) * 32767))
    if sys.byteorder != "little":
        samples.byteswap()
    return samples.tobytes()

def render_loop(pattern, rate=RATE, repeats=1):
    """Mix an arrangement to a bounded PCM buffer; 16 steps make one 4/4 bar."""
    if not isinstance(pattern, Pattern):
        raise TypeError("Expected Pattern")
    if not 8000 <= rate <= 96000 or type(repeats) is not int or not 1 <= repeats <= 16:
        raise ValueError("Unsupported export settings")
    validated = Pattern.from_dict(pattern.as_dict())
    step_frames = 60 * rate / (validated.bpm * 4)
    bar_frames = round(step_frames * STEPS)
    mix = [0.0] * (bar_frames * repeats)
    for rep in range(repeats):
        for track in TRACKS:
            for step, value in enumerate(validated.events[track]):
                if value is None:
                    continue
                start = rep * bar_frames + round(step * step_frames)
                seconds = .23 if track in DRUMS else min(1.1, step_frames / rate * 2.8)
                audio = synthesize(track, value if track not in DRUMS else None, seconds, rate)
                vals = array("h")
                vals.frombytes(audio)
                if sys.byteorder != "little":
                    vals.byteswap()
                for i, val in enumerate(vals):
                    if start + i >= len(mix):
                        break
                    mix[start + i] += val / 32768.0
    output = array("h", (int(32767 * math.tanh(x * .7)) for x in mix))
    if sys.byteorder != "little":
        output.byteswap()
    return output.tobytes()

def write_wav(path, pcm, rate=RATE):
    with wave.open(str(path), "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(rate)
        writer.writeframes(pcm)
