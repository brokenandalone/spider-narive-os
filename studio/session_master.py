"""Private, reversible two-pass loudness mastering for PCM WAV music.

Applies FFmpeg EBU R128 loudnorm to a user-selected completed mix; not a
replacement for creative EQ, compression, listening or professional mastering.
No cloud services, shell, model downloads, mutation of source audio or file
overwrites. Real measured output loudness is preserved in a private receipt.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import threading
import time
import wave

try:
    from .multitrack import SessionError
except ImportError:
    from multitrack import SessionError


class MasterError(SessionError):
    pass


DEFAULT_ROOT = Path.home() / "Documents/Spider Studio/Music/Masters"
PRESETS = {
    "balanced_stream": {"integrated_lufs": -14.0, "true_peak_dbtp": -1.0, "lra": 11.0},
    "dynamic_album": {"integrated_lufs": -16.0, "true_peak_dbtp": -2.0, "lra": 12.0},
    "modern_rock": {"integrated_lufs": -11.0, "true_peak_dbtp": -1.0, "lra": 8.0},
}
MAX_BYTES = 2 * 1024 ** 3
MAX_SECONDS = 7200.0
_REQUIRED_INPUT = ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")


def source_wav(path):
    if not isinstance(path, (str, Path)) or not str(path).strip():
        raise MasterError("Select a finished PCM WAV mix first.")
    source = Path(path).expanduser()
    if (source.is_symlink() or not source.is_file() or source.suffix.lower() != ".wav"
            or not 44 <= source.stat().st_size <= MAX_BYTES):
        raise MasterError("Mastering requires a regular nonempty WAV, 2 GiB maximum.")
    try:
        with wave.open(str(source), "rb") as stream:
            rate, frames = stream.getframerate(), stream.getnframes()
            if (stream.getcomptype() != "NONE" or rate <= 0 or frames <= 0
                    or stream.getnchannels() not in (1, 2)
                    or stream.getsampwidth() not in (1, 2, 3, 4)
                    or frames / rate > MAX_SECONDS):
                raise MasterError("Choose mono or stereo PCM WAV under two hours.")
    except (OSError, wave.Error, EOFError) as error:
        raise MasterError("The selected WAV is damaged or unsupported.") from error
    return source.resolve()


def settings(*, preset="balanced_stream", integrated_lufs=None,
             true_peak_dbtp=None, lra=None):
    if preset not in PRESETS:
        raise MasterError("Select a known mastering preset.")
    result = dict(PRESETS[preset])
    for name, value in (("integrated_lufs", integrated_lufs),
                        ("true_peak_dbtp", true_peak_dbtp), ("lra", lra)):
        if value is not None:
            if type(value) not in (int, float) or not math.isfinite(value):
                raise MasterError(f"{name} must be a finite number.")
            result[name] = float(value)
    if not -24 <= result["integrated_lufs"] <= -8:
        raise MasterError("Target loudness must be -24 to -8 LUFS.")
    if not -3 <= result["true_peak_dbtp"] <= -0.5:
        raise MasterError("True-peak ceiling must be -3 to -0.5 dBTP.")
    if not 5 <= result["lra"] <= 20:
        raise MasterError("Loudness range must be 5 to 20 LU.")
    return result


def _hash(path, stop):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while True:
            if stop.is_set():
                raise MasterError("Mastering cancelled; source mix left untouched.")
            block = stream.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def _run(command, *, stop, timeout):
    """Run FFmpeg without a shell and keep the UI cancellable."""
    if stop.is_set():
        raise MasterError("Mastering cancelled; source mix left untouched.")
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    deadline = time.monotonic() + timeout
    while True:
        try:
            _, error = process.communicate(timeout=0.25)
            break
        except subprocess.TimeoutExpired:
            if stop.is_set() or time.monotonic() >= deadline:
                process.terminate()
                try:
                    process.communicate(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate()
                raise MasterError("Mastering stopped or timed out; source remains unchanged.")
    # Filter graph reports are in stderr; do not export long logs that include
    # user paths or private singer names to any remote location.
    result = error.decode("utf-8", errors="replace")[-131072:]
    if process.returncode != 0:
        raise MasterError("Local FFmpeg mastering failed; inspect the selected WAV and engine.")
    return result


def _report(stderr, *, first):
    needed = _REQUIRED_INPUT if first else ("output_i", "output_tp", "output_lra")
    for match in reversed(list(re.finditer(r"\{[^{}]{1,8192}\}", stderr))):
        try:
            data = json.loads(match.group())
            if not isinstance(data, dict) or not all(key in data for key in needed):
                continue
            converted = {}
            for key, raw in data.items():
                if key in _REQUIRED_INPUT or key.startswith("output_"):
                    value = float(raw)
                    if not math.isfinite(value):
                        raise MasterError("Silent or unmeasurable audio cannot be mastered.")
                    converted[key] = value
                elif key == "normalization_type":
                    converted[key] = str(raw)[:80]
            if all(key in converted for key in needed):
                return converted
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
    raise MasterError("Local loudness analyzer did not return valid measurable results.")


def _loudnorm(params, measurements=None):
    graph = (f"loudnorm=I={params['integrated_lufs']:.1f}:"
             f"TP={params['true_peak_dbtp']:.1f}:LRA={params['lra']:.1f}")
    if measurements is not None:
        fields = (
            ("measured_I", "input_i"), ("measured_TP", "input_tp"),
            ("measured_LRA", "input_lra"), ("measured_thresh", "input_thresh"),
            ("offset", "target_offset"),
        )
        graph += "".join(f":{parameter}={measurements[field]:.3f}"
                         for parameter, field in fields)
        graph += ":linear=true"
    return graph + ":print_format=json"


def _transcode(ffmpeg, source, target, codec, stop, timeout):
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y"]
    if codec == "flac":
        command = command[:-1] + ["-n", "-i", str(source), "-c:a", "flac",
                                  "-compression_level", "5", str(target)]
    elif codec == "mp3":
        command = command[:-1] + ["-n", "-i", str(source), "-c:a", "libmp3lame",
                                  "-q:a", "2", str(target)]
    else:
        raise MasterError("Unknown export audio codec.")
    _run(command, stop=stop, timeout=timeout)
    if target.is_symlink() or not target.is_file() or target.stat().st_size == 0:
        raise MasterError("Optional audio format export failed.")
    os.chmod(target, 0o600)


def master_wav(path, *, preset="balanced_stream", integrated_lufs=None,
               true_peak_dbtp=None, lra=None, flac=False, mp3=False,
               output_root=None, stop=None, timeout=2400):
    """Measure, render and verify a new WAV, with optional FLAC/MP3 copies."""
    if type(flac) is not bool or type(mp3) is not bool:
        raise MasterError("Export formats must be explicit choices.")
    if type(timeout) not in (int, float) or not 1 <= timeout <= 7200:
        raise MasterError("Mastering timeout must be between 1 and 7200 seconds.")
    stop = stop if stop is not None else threading.Event()
    if stop.is_set():
        raise MasterError("Mastering cancelled; source mix left untouched.")
    source = source_wav(path)
    opts = settings(preset=preset, integrated_lufs=integrated_lufs,
                    true_peak_dbtp=true_peak_dbtp, lra=lra)
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise MasterError("Local FFmpeg is needed for two-pass loudness mastering.")
    before = source.stat()
    signature = _hash(source, stop)
    # A silent first pass is rejected rather than converted to a false loudness.
    analyze = [ffmpeg, "-hide_banner", "-nostdin", "-nostats", "-loglevel",
               "info", "-i", str(source), "-vn", "-af", _loudnorm(opts),
               "-f", "null", "-"]
    first = _report(_run(analyze, stop=stop, timeout=timeout), first=True)
    root = Path(output_root).expanduser() if output_root else DEFAULT_ROOT
    if root.is_symlink() or (root.exists() and not root.is_dir()):
        raise MasterError("Master output must be a real private directory.")
    try:
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        directory = Path(tempfile.mkdtemp(prefix="master-", dir=root))
        os.chmod(directory, 0o700)
        try:
            dest = directory / "master.wav"
            render = [ffmpeg, "-hide_banner", "-nostdin", "-nostats",
                      "-loglevel", "info", "-n", "-i", str(source), "-vn",
                      "-af", _loudnorm(opts, first), "-ac", "2", "-ar", "48000",
                      "-c:a", "pcm_s24le", str(dest)]
            output_result = _report(_run(render, stop=stop, timeout=timeout), first=False)
            if dest.is_symlink() or not dest.is_file() or dest.stat().st_size == 0:
                raise MasterError("FFmpeg did not produce a valid master.")
            with wave.open(str(dest), "rb") as stream:
                if (stream.getframerate() != 48000 or stream.getnchannels() != 2
                        or stream.getsampwidth() != 3 or stream.getnframes() == 0):
                    raise MasterError("Master must be nonempty, 24-bit, 48 kHz stereo WAV.")
            os.chmod(dest, 0o600)
            formats = {"wav": dest.name}
            if flac:
                _transcode(ffmpeg, dest, directory / "master.flac", "flac", stop, timeout)
                formats["flac"] = "master.flac"
            if mp3:
                _transcode(ffmpeg, dest, directory / "master.mp3", "mp3", stop, timeout)
                formats["mp3"] = "master.mp3"
            after = source.stat()
            if ((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
                    != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
                    or signature != _hash(source, stop)):
                raise MasterError("Source WAV changed while mastering; exports discarded.")
            receipt = {
                "schema": 1, "source": str(source), "source_sha256": signature,
                "preset": preset, "target": opts, "input_measurements": first,
                "output_measurements": output_result, "file_formats": formats,
                "source_preserved": True, "two_pass": True,
                "peak_ceiling_is_target_not_independent_true_peak_validation": True,
                "quality_requires_owner_listening": True,
            }
            with (directory / "master-receipt.json").open("x", encoding="utf-8") as out:
                os.chmod(directory / "master-receipt.json", 0o600)
                json.dump(receipt, out, indent=2)
            return dest
        except BaseException:
            shutil.rmtree(directory, ignore_errors=True)
            raise
    except OSError as error:
        raise MasterError("Could not complete private mastering export.") from error
