"""Deterministic, device-free Spider Studio overdub transport planning.

This module prepares headphone-only metronome count-ins and validates
sample-accurate punch windows *before* PortAudio opens a device. No audio is
recorded during the count-in. Tempo is fixed for the count-in, not an
interpretation of a score's possibly variable tempo map.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

try:
    from .audio_capture_engine import CaptureError
except ImportError:
    from audio_capture_engine import CaptureError

MAX_INTRO_SECONDS = 35

@dataclass(frozen=True)
class TransportPlan:
    rate: int
    cue_frames: int
    intro_frames: int
    intro_pcm: bytes
    punch_start: int
    punch_end: int
    tempo: int
    beats_per_bar: int
    count_in_bars: int

    @property
    def total_frames(self):
        return self.intro_frames + self.cue_frames

def transport_plan(*,rate,cue_frames,tempo=120,beats_per_bar=4,
                   count_in_bars=0,punch_start_ms=None,punch_end_ms=None):
    if type(rate) is not int or rate not in (44100,48000):
        raise CaptureError("Overdub transport requires 44.1 or 48 kHz")
    if type(cue_frames) is not int or not 1 <= cue_frames <= rate*300:
        raise CaptureError("Backing WAV duration is outside the five-minute limit")
    if type(tempo) is not int or not 30 <= tempo <= 300:
        raise CaptureError("Count-in tempo must be 30–300 BPM")
    if type(beats_per_bar) is not int or beats_per_bar not in (3,4):
        raise CaptureError("Count-in supports 3/4 or 4/4")
    if type(count_in_bars) is not int or not 0 <= count_in_bars <= 4:
        raise CaptureError("Choose zero to four count-in bars")
    if (punch_start_ms is None) != (punch_end_ms is None):
        raise CaptureError("Punch requires both start and end boundaries")
    if punch_start_ms is None:
        punch_start,punch_end=0,cue_frames
    else:
        if (type(punch_start_ms) is not int or type(punch_end_ms) is not int
                or punch_start_ms<0 or punch_end_ms<=punch_start_ms):
            raise CaptureError("Punch boundaries must be increasing whole milliseconds")
        punch_start=round(punch_start_ms*rate/1000)
        punch_end=round(punch_end_ms*rate/1000)
        if not 0 <= punch_start < punch_end <= cue_frames:
            raise CaptureError("Punch-in/out must fit the selected backing WAV")
    beats=beats_per_bar*count_in_bars
    frames=round(beats*rate*60/tempo)
    if frames>rate*MAX_INTRO_SECONDS:
        raise CaptureError("Count-in exceeds the bounded headphone preview")
    if not frames:
        return TransportPlan(rate,cue_frames,0,b"",punch_start,punch_end,
                             tempo,beats_per_bar,count_in_bars)
    # Fixed, rate-independent sinusoidal metronome. Render once on worker
    # thread so the PortAudio callback performs no synthesis or disk I/O.
    pcm=bytearray(frames*4)
    pulse=min(round(rate*.018),round(rate*60/tempo*.15))
    for index in range(beats):
        begin=round(index*rate*60/tempo)
        strong=index%beats_per_bar==0
        volume=14000 if strong else 9500
        freq=1100 if strong else 820
        for j in range(min(pulse,frames-begin)):
            # Envelope reaches exact zero; no output clipping or jumps.
            envelope=(1-j/pulse)**2
            value=int(volume*envelope*math.sin(2*math.pi*freq*j/rate))
            pos=(begin+j)*4
            sample=value.to_bytes(2,"little",signed=True)
            pcm[pos:pos+4]=sample+sample
    return TransportPlan(rate,cue_frames,frames,bytes(pcm),
                         punch_start,punch_end,tempo,beats_per_bar,count_in_bars)

def write_aligned_punch(raw_path,writer,captured_frames,total_frames,shift,
                        *,punch_start=0,punch_end=None,chunk_frames=32768):
    """Write exactly cue length, gating all audio outside the punch window.

    Positive shift advances a take (input[n+shift] mapped to output[n]).
    The algorithm uses bounded disk reads, never copies the cue into the
    take, and does not allocate a full-length PCM buffer.
    """
    from pathlib import Path
    if type(captured_frames) is not int or captured_frames<0:
        raise CaptureError("Captured frame length is invalid")
    if type(total_frames) is not int or total_frames<1:
        raise CaptureError("Backing frame length is invalid")
    if type(shift) is not int or abs(shift)>total_frames:
        raise CaptureError("Latency compensation exceeds cue length")
    if punch_end is None:
        punch_end=total_frames
    if not (type(punch_start) is int and type(punch_end) is int
            and 0 <= punch_start < punch_end <= total_frames):
        raise CaptureError("Invalid punch alignment window")
    unit=writer.getnchannels()*writer.getsampwidth()
    if unit not in (2,4):
        raise CaptureError("This transport writes only 16-bit mono or stereo input")
    with Path(raw_path).open("rb") as raw:
        for out_start in range(0,total_frames,chunk_frames):
            count=min(chunk_frames,total_frames-out_start)
            block=bytearray(count*unit)
            # Read only where recorded data, output duration and punch
            # window overlap. Everything else is absolute digital silence.
            first=max(out_start,punch_start,-shift)
            last=min(out_start+count,punch_end,captured_frames-shift)
            if first<last:
                raw.seek((first+shift)*unit)
                take=raw.read((last-first)*unit)
                if len(take)!=(last-first)*unit:
                    raise CaptureError("Incomplete recorded PCM during punch rendering")
                offset=(first-out_start)*unit
                block[offset:offset+len(take)]=take
            writer.writeframesraw(block)
