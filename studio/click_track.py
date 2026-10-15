"""Offline Spider Studio recording click WAV with count-in and bar markers.

This is a tracking/reference guide, not an AI drum performance. No external
engine, packages, microphone, files or system services are touched.
"""
import json
import math
import os
from pathlib import Path
import struct
import tempfile
import threading
import wave

try:
    from .multitrack import SessionError
except ImportError:
    from multitrack import SessionError


DEFAULT_OUTPUT = Path.home() / "Documents/Spider Studio/Music/Recording Guides"
RATE = 48000
METERS = {"4/4": (4, 1), "3/4": (3, 1), "6/8": (6, 2)}


def validate(tempo, bars, countin_bars, meter):
    if type(tempo) is not int or not 40 <= tempo <= 240:
        raise SessionError("Choose a quarter-note tempo from 40 to 240 BPM.")
    if type(bars) is not int or not 1 <= bars <= 300:
        raise SessionError("Choose 1 to 300 musical bars.")
    if type(countin_bars) is not int or not 0 <= countin_bars <= 4:
        raise SessionError("Count-in must be 0 to 4 bars.")
    if meter not in METERS:
        raise SessionError("Choose a supported recording meter.")
    pulses, subdivisions = METERS[meter]
    seconds_per_pulse = 60 / (tempo * subdivisions)
    length = (bars + countin_bars) * pulses * seconds_per_pulse
    if length > 600:
        raise SessionError("Recording click must be ten minutes or less.")
    return {"tempo_bpm_quarter": tempo, "bars": bars, "countin_bars": countin_bars,
            "meter": meter, "pulses_per_bar": pulses,
            "seconds_per_pulse": seconds_per_pulse,
            "length_seconds": round(length, 4)}


def _pulse(frequency):
    length = int(RATE * 0.042)
    out = bytearray()
    for index in range(length):
        t = index / RATE
        value = int(16000 * math.sin(2 * math.pi * frequency * t)
                    * math.exp(-t * 72))
        out.extend(struct.pack("<hh", value, value))
    return bytes(out)


def write_guide(*, tempo=120, bars=32, countin_bars=2,
                meter="4/4", output_root=None, stop=None):
    """Write owner-private PCM WAV and zero-offset bar chart into a new folder."""
    params = validate(tempo, bars, countin_bars, meter)
    stop = stop if stop is not None else threading.Event()
    if stop.is_set():
        raise SessionError("Click export cancelled; no recording was changed.")
    root = Path(output_root).expanduser() if output_root else DEFAULT_OUTPUT
    if root.is_symlink() or (root.exists() and not root.is_dir()):
        raise SessionError("Select a real, non-symlink recording guide folder.")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    output = Path(tempfile.mkdtemp(prefix="guide-", dir=root))
    os.chmod(output, 0o700)
    destination = output / "click-guide.wav"
    pulses = params["pulses_per_bar"]
    count = pulses * (bars + countin_bars)
    frames_per_pulse = RATE * params["seconds_per_pulse"]
    accent, ordinary = _pulse(1200), _pulse(720)
    positions = []
    try:
        with destination.open("xb") as raw:
            os.chmod(destination, 0o600)
            with wave.open(raw, "wb") as writer:
                writer.setnchannels(2)
                writer.setsampwidth(2)
                writer.setframerate(RATE)
                for pulse in range(count):
                    if stop.is_set():
                        raise SessionError("Click export cancelled; no recording was changed.")
                    start = round(pulse * frames_per_pulse)
                    end = round((pulse + 1) * frames_per_pulse)
                    length = end - start
                    wavelet = accent if pulse % pulses == 0 else ordinary
                    used = min(length, len(wavelet) // 4)
                    writer.writeframesraw(wavelet[:used * 4])
                    writer.writeframesraw(bytes(max(0, length - used) * 4))
                    if pulse % pulses == 0:
                        index = pulse // pulses
                        positions.append({
                            "bar": (index - countin_bars + 1
                                    if index >= countin_bars else None),
                            "countin": index < countin_bars,
                            "seconds_from_start": round(start / RATE, 4),
                        })
        receipt = {
            "schema": 1, **params, "sample_rate": RATE,
            "format": "stereo_pcm_16", "guide_only": True,
            "not_for_final_mix": True, "source_audio_untouched": True,
            "music_begins_seconds": round(
                countin_bars * pulses * frames_per_pulse / RATE, 4),
            "bar_markers": positions,
        }
        with (output / "guide.json").open("x", encoding="utf-8") as stream:
            os.chmod(output / "guide.json", 0o600)
            json.dump(receipt, stream, indent=2)
        return destination
    except BaseException:
        import shutil
        shutil.rmtree(output, ignore_errors=True)
        raise
