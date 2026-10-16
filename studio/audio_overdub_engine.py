"""Opt-in full-duplex cue playback and aligned PCM take capture for Spider Studio.

A single PortAudio RawStream callback drives both backing-track output and
input capture on a shared stream sample-frame timeline. This provides a
*stream-clock reference*, not a claim of physically calibrated device latency.
No input or output device is opened until the user clicks Record Overdub.
No input monitoring is played back, avoiding accidental mic feedback.

The user chooses a regular PCM backing WAV (mono/stereo 16-bit at 44.1/48k),
an explicit input and output device, and may apply +/- 250 ms compensation.
Capture is 16-bit mono/stereo. Files are committed only after success, using
a create-new-only hard link. Existing music and source cue are never modified.
"""
from __future__ import annotations

from array import array
import os
from pathlib import Path
import queue
import sys
import tempfile
import threading
import time
import wave

try:
    from .audio_capture_engine import (
        _backend, _levels, _validate, CaptureError, MAX_SECONDS, QUEUE_LIMIT,
        BLOCK_FRAMES, RATES)
    from .overdub_transport import transport_plan, write_aligned_punch
except ImportError:
    from audio_capture_engine import (
        _backend, _levels, _validate, CaptureError, MAX_SECONDS, QUEUE_LIMIT,
        BLOCK_FRAMES, RATES)
    from overdub_transport import transport_plan, write_aligned_punch

MAX_CUE_BYTES = MAX_SECONDS * 48000 * 2 * 2
CHUNK = 32768
CALLBACK_WATCHDOG_SECONDS = 4.0

def available_outputs(backend=None):
    """List devices on explicit request, without opening audio streams."""
    api = _backend(backend)
    try:
        devices = api.query_devices()
        return [(i, str(d.get("name", "Output"))[:110],
                 int(d["max_output_channels"]))
                for i, d in enumerate(devices)
                if int(d.get("max_output_channels", 0)) >= 2]
    except (OSError, ValueError, TypeError, RuntimeError, KeyError) as exc:
        raise CaptureError("Unable to list stereo playback devices") from exc

def _read_cue(path, rate, destination):
    source = Path(path)
    if (source.is_symlink() or not source.is_file()
            or source.suffix.lower() != ".wav"):
        raise CaptureError("Select a regular, local stereo or mono PCM cue WAV")
    if source.resolve() == destination.resolve():
        raise CaptureError("Backing WAV and recorded take cannot be the same file")
    if source.stat().st_size > MAX_CUE_BYTES + 1024 * 1024:
        raise CaptureError("Backing WAV exceeds the five-minute size limit")
    try:
        with wave.open(str(source), "rb") as wav:
            channels = wav.getnchannels()
            frames = wav.getnframes()
            if (wav.getcomptype() != "NONE" or wav.getsampwidth() != 2
                or channels not in (1, 2) or wav.getframerate() != rate
                or not 1 <= frames <= rate * MAX_SECONDS):
                raise CaptureError(
                    "Cue must be 16-bit mono/stereo PCM at the chosen 44.1/48 kHz rate "
                    "and no longer than five minutes")
            data = wav.readframes(frames)
            if len(data) != frames * channels * 2:
                raise CaptureError("Backing WAV has truncated PCM frames")
    except (OSError, EOFError, wave.Error, ZeroDivisionError) as exc:
        raise CaptureError("The selected backing WAV is invalid") from exc
    if channels == 1:
        stereo = bytearray(frames * 4)
        for i in range(frames):
            sample = data[i*2:i*2+2]
            stereo[i*4:i*4+4] = sample + sample
        data = bytes(stereo)
    return data, frames

def _aligned_copy(raw_path, wav, captured_frames, total_frames, shift,
                  *, punch_start=0, punch_end=None):
    # Compatibility wrapper for earlier exported recording sessions.
    return write_aligned_punch(
        raw_path,wav,captured_frames,total_frames,shift,
        punch_start=punch_start,punch_end=punch_end)

def capture_overdub(destination, *, cue, input_device, output_device,
                    role, channels=1, rate=48000, latency_ms=0, max_seconds=300,
                    stop=None, on_level=None, backend=None,
                    tempo=120, beats_per_bar=4, count_in_bars=0,
                    punch_start_ms=None, punch_end_ms=None):
    """Full-duplex 16-bit capture, sample-indexed to a chosen cue WAV.

    Playback and capture share one PortAudio callback. The returned WAV
    includes silence to cue length, so session files all begin at beat zero.
    No automatic loudspeaker, headphone or input monitoring is configured.
    Physical ADC/DAC latency and acoustic spill require owner calibration.
    """
    dest = _validate(destination, input_device, channels, rate, max_seconds, role, 16)
    if (type(output_device) is not int or not 0 <= output_device <= 1024):
        raise CaptureError("Choose a valid stereo playback output")
    if type(latency_ms) is not int or not -250 <= latency_ms <= 250:
        raise CaptureError("Manual input timing compensation must be -250 to +250 ms")
    cue_data, cue_frames = _read_cue(cue, rate, dest)
    if cue_frames > int(max_seconds * rate):
        raise CaptureError("Selected maximum recording time must cover the entire cue")
    if cue_frames > 48000 * MAX_SECONDS:
        raise CaptureError("Backing cue is too long")
    transport=transport_plan(
        rate=rate,cue_frames=cue_frames,tempo=tempo,
        beats_per_bar=beats_per_bar,count_in_bars=count_in_bars,
        punch_start_ms=punch_start_ms,punch_end_ms=punch_end_ms)
    stopped = stop if stop is not None else threading.Event()
    if stopped.is_set():
        raise CaptureError("Overdub was cancelled before opening devices")
    api = _backend(backend)
    raw_queue = queue.Queue(maxsize=QUEUE_LIMIT)
    cue_view = memoryview(cue_data)
    state = {"sent": 0, "fault": None, "last_callback": time.monotonic()}
    # The callback must never block on disk writes or synthesize metronome.
    # Intro frames have NO recorded content and do not shift song timeline.
    def callback(indata, outdata, frames, stream_time, status):
        outdata[:] = bytes(len(outdata))
        if status:
            state["fault"] = "Full-duplex input/output underflow or overflow; discard take"
            stopped.set()
            return
        if (type(frames) is not int or frames <= 0 or frames > 8192
                or len(outdata) != frames*4 or len(indata) != frames*channels*2):
            state["fault"] = "Invalid full-duplex audio callback frame layout"
            stopped.set()
            return
        state["last_callback"]=time.monotonic()
        remaining=max(0,transport.total_frames-state["sent"])
        wanted=min(frames,remaining) if not stopped.is_set() else 0
        if not wanted:
            return
        begin=state["sent"]
        # Pre-count is audible only in headphone cue, never recorded.
        intro=min(wanted,max(0,transport.intro_frames-begin))
        if intro:
            outdata[:intro*4]=transport.intro_pcm[begin*4:(begin+intro)*4]
        active=wanted-intro
        if active:
            cue_offset=begin+intro-transport.intro_frames
            outdata[intro*4:wanted*4]=cue_view[
                cue_offset*4:(cue_offset+active)*4]
            try:
                offset=intro*channels*2
                block=bytes(indata[offset:offset+active*channels*2])
                raw_queue.put_nowait((cue_offset,block,active))
            except (queue.Full,MemoryError,BufferError,ValueError):
                state["fault"]="Recording input queue overflow; discard take"
                stopped.set()
                return
        state["sent"]+=wanted
        if state["sent"]>=transport.total_frames:
            stopped.set()

    raw_tmp = None
    wav_tmp = None
    frames_written = 0
    try:
        fd, raw_tmp = tempfile.mkstemp(prefix=".spider-duplex-",
                                       suffix=".pcm.part", dir=str(dest.parent))
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as raw_file:
            try:
                with api.RawStream(
                    samplerate=rate, blocksize=BLOCK_FRAMES,
                    device=(input_device, output_device),
                    channels=(channels, 2), dtype="int16", callback=callback):
                    last_level = time.monotonic()
                    while True:
                        if (not stopped.is_set()
                                and time.monotonic()-state["last_callback"]
                                > CALLBACK_WATCHDOG_SECONDS):
                            state["fault"] = (
                                "Audio device stopped providing full-duplex frames; "
                                "the incomplete take was rejected")
                            stopped.set()
                        if stopped.is_set() and raw_queue.empty():
                            break
                        try:
                            start, block, count = raw_queue.get(timeout=.08)
                        except queue.Empty:
                            continue
                        if start != frames_written:
                            raise CaptureError("Missing input audio frames; retake required")
                        raw_file.write(block)
                        frames_written += count
                        now = time.monotonic()
                        if on_level is not None and now-last_level >= .12:
                            peak, rms = _levels(block,16)
                            on_level(peak,rms,frames_written/rate)
                            last_level = now
            except (OSError, RuntimeError, ValueError) as exc:
                raise CaptureError("Cannot open/capture with the chosen duplex devices: "
                                   +str(exc)[:160]) from exc
            raw_file.flush()
            os.fsync(raw_file.fileno())
        if state["fault"]:
            raise CaptureError(state["fault"])
        if frames_written <= 0:
            raise CaptureError("No overdub audio frames recorded")
        shift = round(latency_ms * rate / 1000)
        fd, wav_tmp = tempfile.mkstemp(prefix=".spider-overdub-",
                                       suffix=".wav.part", dir=str(dest.parent))
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as final:
            with wave.open(final,"wb") as wav:
                wav.setnchannels(channels)
                wav.setsampwidth(2)
                wav.setframerate(rate)
                _aligned_copy(raw_tmp, wav, frames_written, cue_frames, shift,
                              punch_start=transport.punch_start,
                              punch_end=transport.punch_end)
                wav.writeframes(b"")
            final.flush()
            os.fsync(final.fileno())
        if dest.exists() or dest.is_symlink():
            raise FileExistsError("The recorded take name already exists")
        os.link(wav_tmp, dest, follow_symlinks=False)
        return {
            "path":str(dest), "role":role, "channels":channels,
            "sample_rate":rate, "sample_width_bits":16,
            "frames":cue_frames, "captured_frames":frames_written,
            "duration_seconds":round(cue_frames/rate,3),
            "capture_seconds":round(frames_written/rate,3),
            "timing":"single_duplex_callback_stream_clock",
            "compensation_ms":latency_ms,
            "cue_name":Path(cue).name,
            "count_in_bars":count_in_bars,
            "count_in_tempo":tempo,
            "punch_start_ms":round(transport.punch_start*1000/rate),
            "punch_end_ms":round(transport.punch_end*1000/rate),
            "preroll_seconds":round(transport.intro_frames/rate,3),
        }
    finally:
        for path in (raw_tmp,wav_tmp):
            if path is not None:
                Path(path).unlink(missing_ok=True)
