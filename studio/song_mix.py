"""Offline vocal+instrumental WAV assembly with bounded, non-shell FFmpeg.

This is the final mix stage after an owner voice was converted from an isolated
vocal stem. A mastered-song file is not equivalent to separate stems.
"""
from pathlib import Path
import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
import wave


class MixError(ValueError):
    pass


DEFAULT_OUTPUT = Path.home() / "Documents/Spider Studio/Music/My Voice/Final Mixes"
MAX_AUDIO_BYTES = 2 * 1024 ** 3


def valid_wav(path, name):
    source = Path(path).expanduser()
    if (source.is_symlink() or not source.is_file() or source.suffix.lower() != ".wav"
            or not 0 < source.stat().st_size <= MAX_AUDIO_BYTES):
        raise MixError(f"Choose a regular, nonempty WAV for {name}.")
    return source.resolve()


def mix_command(ffmpeg, instrumental, vocal, output, vocal_gain=1.0, backing_gain=1.0):
    """Build the exact FFmpeg argument vector without a shell or a destructive overwrite."""
    for name, gain in (("Vocal", vocal_gain), ("Backing", backing_gain)):
        if isinstance(gain, bool) or not isinstance(gain, (int, float)) or not 0 <= gain <= 2:
            raise MixError(f"{name} gain must be between 0 and 2.")
    bed = valid_wav(instrumental, "instrumental backing")
    singer = valid_wav(vocal, "converted vocal")
    if singer == bed:
        raise MixError("Select two different files for the vocal and backing.")
    target = Path(output).expanduser()
    if target.is_symlink() or target.exists() or target.suffix.lower() != ".wav":
        raise MixError("Output must be a new WAV file, not an existing file.")
    filter_graph = (
        f"[0:a:0]volume={backing_gain:.3f}[bed];"
        f"[1:a:0]volume={vocal_gain:.3f}[singer];"
        "[bed][singer]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0,"
        "alimiter=limit=0.95[out]"
    )
    return [str(ffmpeg), "-hide_banner", "-loglevel", "error", "-nostdin", "-n",
            "-i", str(bed), "-i", str(singer),
            "-filter_complex", filter_graph, "-map", "[out]",
            "-ac", "2", "-ar", "48000", "-c:a", "pcm_s24le", str(target)]


def mix_vocals(instrumental, vocal, *, output_root=None, vocal_gain=1.0,
               backing_gain=1.0, timeout=1200, stop=None):
    """Create a new final mix while never touching original audio files."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise MixError("Install FFmpeg or activate its existing Spider Studio tool.")
    if isinstance(timeout, bool) or not isinstance(timeout, (float, int)) or not 1 <= timeout <= 7200:
        raise MixError("Invalid mix timeout.")
    stop = stop if stop is not None else threading.Event()
    if stop.is_set():
        raise MixError("Mix cancelled before processing.")
    parent = Path(output_root) if output_root else DEFAULT_OUTPUT
    if parent.is_symlink():
        raise MixError("The output folder must not be a symlink.")
    # Validate all inputs before creating any output.
    bed = valid_wav(instrumental, "instrumental backing")
    singer = valid_wav(vocal, "converted vocal")
    if bed == singer:
        raise MixError("Vocal and backing must be different audio files.")
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(parent, 0o700)
    folder = Path(tempfile.mkdtemp(prefix="mix-", dir=parent))
    os.chmod(folder, 0o700)
    output = folder / "final-mix.wav"
    log = folder / "mix.log"
    command = mix_command(ffmpeg, bed, singer, output, vocal_gain, backing_gain)
    try:
        with log.open("xb") as stream:
            os.chmod(log, 0o600)
            proc = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                                    stdout=stream, stderr=subprocess.STDOUT)
            deadline = time.monotonic() + timeout
            while proc.poll() is None:
                if stop.is_set() or time.monotonic() >= deadline:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=5)
                    raise MixError("Mix was stopped or timed out. Source audio remains unchanged.")
                stop.wait(0.15)
        if proc.returncode != 0 or output.is_symlink() or not output.is_file():
            raise MixError("Mix failed. Check the local private mix.log file.")
        try:
            with wave.open(str(output), "rb") as reader:
                if reader.getnframes() <= 0 or reader.getframerate() != 48000:
                    raise MixError("FFmpeg did not create the requested 48 kHz WAV.")
        except (wave.Error, EOFError) as exc:
            raise MixError("FFmpeg returned an invalid final WAV.") from exc
        os.chmod(output, 0o600)
        receipt = {
            "schema": 1,
            "original_instrumental": str(bed),
            "converted_vocal": str(singer),
            "final_wav": output.name,
            "vocal_gain": round(float(vocal_gain), 3),
            "backing_gain": round(float(backing_gain), 3),
            "trained_voice_checked": False,
            "source_tracks_preserved": True,
        }
        receipt_file = folder / "mix.json"
        with receipt_file.open("x", encoding="utf-8") as stream:
            os.chmod(receipt_file, 0o600)
            json.dump(receipt, stream, indent=2)
        return output
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise MixError("Could not finish the local mix. Source audio was not modified.") from exc
