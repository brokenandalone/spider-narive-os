"""Offline multi-bank score production for Spider Audio Studio.

Render each part using its chosen user-owned licensed SoundFont, then mix
validated stereo PCM streams in bounded chunks. Supports gain/pan/mute/solo;
no shell, live device access, audio service restart or sample distribution.
Existing source notation and SF banks are protected from export overwrite.
"""
from __future__ import annotations

from array import array
from dataclasses import dataclass
from fractions import Fraction
import math
import os
from pathlib import Path
import sys
import tempfile
import wave

try:
    from .score_performer import Performance, Note
    from .soundfont_render import render_soundfont, validate_soundfont
except ImportError:
    from score_performer import Performance, Note
    from soundfont_render import render_soundfont, validate_soundfont

BLOCK = 4096

@dataclass(frozen=True)
class MixChannel:
    gain: int = 90
    pan: int = 0
    mute: bool = False
    solo: bool = False

    def validate(self):
        if type(self.gain) is not int or not 0 <= self.gain <= 120:
            raise ValueError("Score channel gain must be 0–120 percent")
        if type(self.pan) is not int or not -100 <= self.pan <= 100:
            raise ValueError("Score channel pan must be -100..100")
        if type(self.mute) is not bool or type(self.solo) is not bool:
            raise ValueError("Score mute/solo must be booleans")
        return self

def _isolated_part(performance, index):
    """Produce a monophonic CHANNEL stream while retaining its polyphonic notes."""
    from dataclasses import replace
    part = performance.parts[index]
    notes = [Note(0, n.pitch, n.start, n.duration, n.velocity)
             for n in performance.notes if n.part == index]
    # A silent part must not be passed to the SoundFont renderer.
    if not notes:
        return None
    return replace(performance, parts=[part], notes=notes, origin=performance.origin).validated()

def _audio_layout(path, rate):
    with wave.open(str(path), "rb") as reader:
        if reader.getnchannels() != 2 or reader.getsampwidth() != 2 or reader.getframerate() != rate:
            raise ValueError("SoundFont part did not render stereo 16-bit audio at matching sample rate")
        return reader.getnframes()

def _mix_readers(readers, settings, total_frames):
    """Emit compressed PCM bytes per chunk; read files instead of loading all stems."""
    solo_active = any(m.solo and not m.mute for m in settings)
    for offset in range(0, total_frames, BLOCK):
        count = min(BLOCK, total_frames - offset)
        accum_l = [0.] * count
        accum_r = [0.] * count
        for reader, channel in zip(readers, settings):
            channel.validate()
            raw = reader.readframes(count)
            if (channel.mute or not channel.gain or
                    (solo_active and not channel.solo)):
                continue
            data = array("h")
            data.frombytes(raw)
            if sys.byteorder != "little":
                data.byteswap()
            # constant-power pan balances the individual stereo track's L/R
            angle = math.pi * (channel.pan + 100) / 400
            gl = (channel.gain / 100) * math.cos(angle) * 1.41421356237
            gr = (channel.gain / 100) * math.sin(angle) * 1.41421356237
            frames = min(count, len(data) // 2)
            for k in range(frames):
                accum_l[k] += data[2*k] / 32768 * gl
                accum_r[k] += data[2*k+1] / 32768 * gr
        samples = array("h")
        for l, r in zip(accum_l, accum_r):
            samples.append(round(32767 * math.tanh(l * 0.72)))
            samples.append(round(32767 * math.tanh(r * 0.72)))
        if sys.byteorder != "little":
            samples.byteswap()
        yield samples.tobytes()

def render_score_mix(performance, default_bank, destination, part_banks=None,
                     channels=None, rate=48000, part_renderer=None):
    """Render + master a score from individual instrument banks (atomic output).

    part_banks is {score-part-index: path-to-bank}. Unspecified parts use
    default_bank. Multi-pass rendering is slower but lets each instrument use
    its own specialized sample library, with deterministic stereo mixing.
    """
    p = performance.validated()
    if rate not in (44100, 48000):
        raise ValueError("Studio mixing supports 44.1 or 48 kHz")
    if not p.notes:
        raise ValueError("No notes to perform")
    if p.duration_seconds > 300:
        raise ValueError("Studio mix supports scores up to five minutes")
    selected = dict(part_banks or {})
    if any(type(i) is not int or i < 0 or i >= len(p.parts) for i in selected):
        raise ValueError("Invalid score part bank assignment")
    mixer = list(channels) if channels is not None else [MixChannel() for _ in p.parts]
    if len(mixer) != len(p.parts):
        raise ValueError("Mixer channel count must match score parts")
    for ch in mixer:
        if not isinstance(ch, MixChannel):
            raise ValueError("Invalid score mixer channel")
        ch.validate()
    bank_paths = [validate_soundfont(selected.get(i, default_bank)).resolve()
                  for i in range(len(p.parts))]
    dest = Path(destination)
    if not dest.parent.is_dir():
        raise FileNotFoundError("Output directory missing")
    if any(dest.resolve() == bank for bank in bank_paths):
        raise ValueError("Refusing to overwrite an instrument soundbank")
    if p.origin is not None and dest.resolve() == p.origin.resolve():
        raise ValueError("Refusing to overwrite imported notation")
    perform_part = part_renderer or render_soundfont
    temporary = None
    with tempfile.TemporaryDirectory(prefix="spider-studio-mix-") as folder:
        soundfiles = []
        for i in range(len(p.parts)):
            isolate = _isolated_part(p, i)
            if isolate is None:
                soundfiles.append(None)
                continue
            target = Path(folder) / f"part-{i:02d}.wav"
            perform_part(isolate, bank_paths[i], target, rate=rate)
            _audio_layout(target, rate)
            soundfiles.append(target)
        from contextlib import ExitStack
        with ExitStack() as stack:
            readers = [
                stack.enter_context(wave.open(str(f), "rb")) if f is not None else None
                for f in soundfiles
            ]
            # Every part is time-aligned to score time zero.
            frames = max((r.getnframes() for r in readers if r is not None), default=0)
            if frames <= 0:
                raise RuntimeError("SoundFont tracks contained no playable frames")
            # Empty tracks use a no-op reader to keep 1:1 mixer association.
            class Silence:
                def readframes(self, amount): return b""
            aligned = [reader if reader is not None else Silence() for reader in readers]
            fd, temporary = tempfile.mkstemp(
                prefix=".spider-studio-", suffix=".wav.tmp", dir=str(dest.parent))
            try:
                with os.fdopen(fd, "wb") as stream:
                    with wave.open(stream, "wb") as output:
                        output.setnchannels(2)
                        output.setsampwidth(2)
                        output.setframerate(rate)
                        for block in _mix_readers(aligned, mixer, frames):
                            output.writeframesraw(block)
                        output.writeframes(b"")
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, dest)
                temporary = None
            finally:
                if temporary is not None:
                    Path(temporary).unlink(missing_ok=True)
    return dest
