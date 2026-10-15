"""Bar-based song arrangement and channel mixer for Spider Audio Studio.

Independent offline/streaming 16-bit stereo renderer. No sound device, project
folder, service or existing installation is modified by imports or rendering.
This is a production *prototype*: effects/MIDI and live recording remain future.
"""
from __future__ import annotations

from array import array
from dataclasses import dataclass, field
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import wave

try:
    from .instruments_engine import RATE, DRUMS, TRACKS, Pattern, STEPS, synthesize
except ImportError:
    from instruments_engine import RATE, DRUMS, TRACKS, Pattern, STEPS, synthesize

MAX_BARS = 32
DEFAULT_NAME = "Untitled Spider Song"

@dataclass
class Channel:
    gain: int = 80
    pan: int = 0
    mute: bool = False
    solo: bool = False

    @classmethod
    def from_dict(cls, value):
        if not isinstance(value, dict) or set(value) != {"gain", "pan", "mute", "solo"}:
            raise ValueError("Invalid mixer channel")
        gain, pan, mute, solo = (value[key] for key in ("gain", "pan", "mute", "solo"))
        if type(gain) is not int or not 0 <= gain <= 100:
            raise ValueError("Channel gain must be between 0 and 100")
        if type(pan) is not int or not -100 <= pan <= 100:
            raise ValueError("Channel pan must be between -100 and 100")
        if type(mute) is not bool or type(solo) is not bool:
            raise ValueError("Mute and solo must be switches")
        return cls(gain, pan, mute, solo)

    def as_dict(self):
        return {"gain": self.gain, "pan": self.pan, "mute": self.mute, "solo": self.solo}


@dataclass
class Bar:
    name: str
    pattern: Pattern

    def as_dict(self):
        return {"name": self.name, "pattern": self.pattern.as_dict()}

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or set(data) != {"name", "pattern"}:
            raise ValueError("Invalid song section")
        name = data["name"]
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 60:
            raise ValueError("Song section names must be 1 to 60 characters")
        if any(ord(c) < 32 for c in name):
            raise ValueError("Section name contains control characters")
        return cls(name.strip(), Pattern.from_dict(data["pattern"]))


@dataclass
class Song:
    title: str = DEFAULT_NAME
    bpm: int = 110
    bars: list[Bar] = field(default_factory=list)
    mixer: dict[str, Channel] = field(
        default_factory=lambda: {track: Channel() for track in TRACKS}
    )

    def capture(self, name: str, pattern: Pattern):
        if len(self.bars) >= MAX_BARS:
            raise ValueError("This prototype supports up to 32 bars")
        data = {"name": name, "pattern": pattern.as_dict()}
        bar = Bar.from_dict(data)
        # Deep copy, so changing the instrument workbench doesn't alter the song.
        bar.pattern.bpm = self.bpm
        self.bars.append(bar)

    def as_dict(self):
        return {"format": "spider-song-1", "title": self.title, "bpm": self.bpm,
                "bars": [bar.as_dict() for bar in self.bars],
                "mixer": {track: self.mixer[track].as_dict() for track in TRACKS}}

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or set(data) != {"format", "title", "bpm", "bars", "mixer"}:
            raise ValueError("Not a Spider Audio Studio song")
        if data["format"] != "spider-song-1":
            raise ValueError("Unrecognized song file version")
        title, bpm = data["title"], data["bpm"]
        if not isinstance(title, str) or not 1 <= len(title.strip()) <= 100:
            raise ValueError("Song title must be 1 to 100 characters")
        if any(ord(c) < 32 for c in title):
            raise ValueError("Invalid song title")
        if type(bpm) is not int or not 40 <= bpm <= 240:
            raise ValueError("Tempo must be between 40 and 240 BPM")
        if not isinstance(data["bars"], list) or len(data["bars"]) > MAX_BARS:
            raise ValueError("Song exceeds 32 bars")
        mixer = data["mixer"]
        if not isinstance(mixer, dict) or set(mixer) != set(TRACKS):
            raise ValueError("Song mixer channels missing or unknown")
        result = cls(title=title.strip(), bpm=bpm)
        result.bars = [Bar.from_dict(item) for item in data["bars"]]
        result.mixer = {track: Channel.from_dict(mixer[track]) for track in TRACKS}
        for bar in result.bars:
            bar.pattern.bpm = bpm
        return result

def _valid_song(song):
    if not isinstance(song, Song):
        raise TypeError("Expected a Spider Audio Studio Song")
    return Song.from_dict(song.as_dict())

def _channel_enabled(track, mixer, stem):
    if stem is not None and track != stem:
        return False
    channel = mixer[track]
    if channel.mute or channel.gain == 0:
        return False
    soloed = any(v.solo and not v.mute for v in mixer.values())
    return not soloed or channel.solo

def _render_bar(bar, bpm, mixer, rate, stem=None):
    frames = round(rate * 240 / bpm)
    left = array("f", [0.0]) * frames
    right = array("f", [0.0]) * frames
    cache = {}
    for track in TRACKS:
        if not _channel_enabled(track, mixer, stem):
            continue
        channel = mixer[track]
        # Equal-power constant panning. Gain maps 0-100 linearly.
        angle = math.pi * (channel.pan + 100) / 400
        lgain = math.cos(angle) * channel.gain / 100
        rgain = math.sin(angle) * channel.gain / 100
        if lgain == 0 and rgain == 0:
            continue
        for step, value in enumerate(bar.pattern.events[track]):
            if value is None:
                continue
            start = round(frames * step / STEPS)
            duration = 0.23 if track in DRUMS else min(1.1, 240 / bpm / 16 * 2.8)
            key = (track, value, duration)
            if key not in cache:
                raw = synthesize(track, value if track not in DRUMS else None,
                                 seconds=duration, rate=rate)
                samples = array("h")
                samples.frombytes(raw)
                if sys.byteorder != "little":
                    samples.byteswap()
                cache[key] = samples
            sound = cache[key]
            for pos in range(min(len(sound), frames - start)):
                amp = sound[pos] / 32768
                left[start + pos] += amp * lgain
                right[start + pos] += amp * rgain
    output = array("h")
    for l, r in zip(left, right):
        # Gentle bounded saturator prevents hard digital clipping.
        output.append(round(32767 * math.tanh(.74 * l)))
        output.append(round(32767 * math.tanh(.74 * r)))
    if sys.byteorder != "little":
        output.byteswap()
    return output.tobytes()

def render_song_chunks(song: Song, rate=RATE, stem=None):
    """Generate one stereo PCM bar at a time to keep memory bounded."""
    validated = _valid_song(song)
    if not 8000 <= rate <= 96000:
        raise ValueError("Sample rate must be 8,000 to 96,000 Hz")
    if stem is not None and stem not in TRACKS:
        raise ValueError("Unknown stem channel")
    for bar in validated.bars:
        yield _render_bar(bar, validated.bpm, validated.mixer, rate, stem=stem)

def song_duration(song: Song):
    return len(_valid_song(song).bars) * 240 / song.bpm

def write_song_wav(song: Song, destination, rate=RATE, stem=None):
    """Atomic full-song bounce, keeps the source project and past export safe."""
    validated = _valid_song(song)
    if not validated.bars:
        raise ValueError("Add at least one bar before exporting")
    if not 8000 <= rate <= 96000:
        raise ValueError("Invalid output sample rate")
    if stem is not None and stem not in TRACKS:
        raise ValueError("Unknown stem")
    target = Path(destination)
    if not target.parent.is_dir():
        raise FileNotFoundError("Output directory is missing")
    tmp = None
    try:
        descriptor, tmp = tempfile.mkstemp(prefix=".spider-audio-", suffix=".wav.tmp",
                                          dir=str(target.parent))
        with os.fdopen(descriptor, "wb") as stream:
            with wave.open(stream, "wb") as output:
                output.setnchannels(2)
                output.setsampwidth(2)
                output.setframerate(rate)
                for block in render_song_chunks(validated, rate, stem):
                    output.writeframesraw(block)
                output.writeframes(b"")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, target)
    finally:
        if tmp is not None:
            Path(tmp).unlink(missing_ok=True)

def export_stems(song: Song, directory, rate=RATE):
    """Export seven independent stereo stems with descriptive filenames."""
    validated = _valid_song(song)
    if not validated.bars:
        raise ValueError("Song is empty")
    folder = Path(directory)
    if not folder.is_dir():
        raise FileNotFoundError("Stem directory does not exist")
    # Prevent accidentally clobbering previous exports.
    paths = {track: folder / ("Spider-Stem-" + track + ".wav") for track in TRACKS}
    if any(p.exists() for p in paths.values()):
        raise FileExistsError("Some stem exports already exist in this folder")
    created = []
    try:
        for track, path in paths.items():
            write_song_wav(validated, path, rate=rate, stem=track)
            created.append(path)
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    return list(paths.values())

def save_song(song: Song, destination):
    validated = _valid_song(song)
    path = Path(destination)
    if not path.parent.is_dir():
        raise FileNotFoundError("Project directory missing")
    tmp = None
    try:
        descriptor, tmp = tempfile.mkstemp(prefix=".spider-song-",
                                          suffix=".json.tmp", dir=str(path.parent))
        with os.fdopen(descriptor, "w", encoding="utf-8") as f:
            json.dump(validated.as_dict(), f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if tmp:
            Path(tmp).unlink(missing_ok=True)

def load_song(filename):
    target = Path(filename)
    if target.stat().st_size > 1_000_000:
        raise ValueError("Song project is too large")
    return Song.from_dict(json.loads(target.read_text("utf-8")))
