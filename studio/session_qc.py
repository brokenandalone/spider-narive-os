"""Quick, non-destructive PCM audio checks for an audited Studio session.

Preview only: inspect up to the first and last five seconds of each WAV, not the
full recording. No claim of complete clipping, phase, pitch or fidelity analysis.
"""
from array import array
import math
from pathlib import Path
import sys
import threading
import wave

try:
    from .session_project import inspect_session
    from .multitrack import SessionError
except ImportError:
    from session_project import inspect_session
    from multitrack import SessionError

EDGE_SECONDS = 5


def _normalized_samples(raw, width):
    """Return sample values between -1 and 1 for ordinary little-endian PCM."""
    if width == 1:
        return ((byte - 128) / 128.0 for byte in raw)
    if width in (2, 4):
        unit = "h" if width == 2 else "i"
        values = array(unit)
        values.frombytes(raw)
        if sys.byteorder != "little":
            values.byteswap()
        scale = float(1 << (8 * width - 1))
        return (value / scale for value in values)
    if width == 3:
        scale = float(1 << 23)
        return (int.from_bytes(raw[i:i + 3], "little", signed=True) / scale
                for i in range(0, len(raw), 3))
    raise SessionError("Quick audio QC supports only 8-, 16-, 24- and 32-bit PCM WAV.")


def analyze_wav(path, *, edge_seconds=EDGE_SECONDS, stop=None):
    """Scan bounded head/tail windows without modifying or storing PCM."""
    if type(edge_seconds) not in (int, float) or not 0 < edge_seconds <= 10:
        raise SessionError("Choose 0 to 10 seconds per preview edge.")
    stop = stop or threading.Event()
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.suffix.lower() != ".wav":
        raise SessionError("Quick QC requires a regular WAV file.")
    sum_squares = 0.0
    sum_values = 0.0
    peak = 0.0
    clip_count = 0
    sample_count = 0
    try:
        with wave.open(str(path), "rb") as handle:
            if handle.getcomptype() != "NONE":
                raise SessionError("Compressed WAV is unsupported.")
            rate, frames, width, channels = (
                handle.getframerate(), handle.getnframes(),
                handle.getsampwidth(), handle.getnchannels())
            if rate <= 0 or frames <= 0 or width not in (1, 2, 3, 4) or channels not in (1, 2):
                raise SessionError("Unsupported or empty PCM WAV.")
            span = max(1, min(frames, round(rate * edge_seconds)))
            windows = [(0, min(span, frames))]
            if frames > span:
                second = max(span, frames - span)
                if second < frames:
                    windows.append((second, frames - second))
            for start, count in windows:
                handle.setpos(start)
                remaining = count
                while remaining > 0:
                    if stop.is_set():
                        raise SessionError("Audio quality check cancelled.")
                    samples = min(4096, remaining)
                    raw = handle.readframes(samples)
                    if len(raw) != samples * channels * width:
                        raise SessionError("WAV file ended unexpectedly during quick QC.")
                    remaining -= samples
                    for value in _normalized_samples(raw, width):
                        magnitude = abs(value)
                        peak = max(peak, magnitude)
                        sum_squares += value * value
                        sum_values += value
                        clip_count += magnitude >= 0.995
                        sample_count += 1
    except (OSError, EOFError, wave.Error) as error:
        raise SessionError("Could not read an audio preview for quality checking.") from error
    if sample_count <= 0:
        raise SessionError("No audio samples available for preview.")
    rms = math.sqrt(sum_squares / sample_count)
    result = {
        "sampled_seconds": round(sample_count / (rate * channels), 3),
        "total_seconds": round(frames / rate, 3),
        "complete_file_scanned": sample_count == frames * channels,
        "sample_rate": rate,
        "channels": channels,
        "peak_dbfs": round(20 * math.log10(max(peak, 1e-12)), 2),
        "rms_dbfs": round(20 * math.log10(max(rms, 1e-12)), 2),
        "dc_offset": round(sum_values / sample_count, 6),
        "near_clip_samples": clip_count,
        "samples_checked": sample_count,
        "warnings": [],
    }
    if result["rms_dbfs"] < -55:
        result["warnings"].append("Sampled regions are nearly silent.")
    if peak >= 0.995:
        result["warnings"].append("Near-full-scale peaks found in sampled regions.")
    if abs(result["dc_offset"]) > 0.05:
        result["warnings"].append("Elevated DC offset in sampled regions.")
    return result


def audit_session_audio(folder, *, stop=None):
    """Verify original WAV hashes then run bounded audio QC across all tracks."""
    stop = stop or threading.Event()
    session = inspect_session(folder, stop=stop)
    report = []
    for track in session["tracks"]:
        if stop.is_set():
            raise SessionError("Audio quality check cancelled.")
        measured = analyze_wav(track["path"], stop=stop)
        report.append({"filename": track["filename"],
                       "role": track["role"], **measured})
    warnings = []
    if len(session["sample_rates"]) > 1:
        warnings.append("Source sample rates differ; the mixer resamples to 48 kHz.")
    warnings.extend(f"{track['filename']}: {warning}" for track in report
                    for warning in track["warnings"])
    return {"schema": 1, "session_title": session["title"],
            "quick_preview_only": True, "tracks": report,
            "warnings": warnings, "source_audio_untouched": True}
