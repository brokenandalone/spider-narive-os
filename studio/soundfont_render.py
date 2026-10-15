"""Optional high-quality SoundFont renderer for Spider Auto Performer.

Uses the independently installed FluidSynth executable and a soundbank that
the owner selects. No samples or third-party SoundFonts are embedded or
downloaded. Never touches a live audio device, Nova or installed sound servers.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import wave

try:
    from .score_midi import export_performance_midi
except ImportError:
    from score_midi import export_performance_midi

MAX_RENDER_SECONDS = 300
MAX_SF_BYTES = 2_000_000_000

def quality_backend_available():
    return shutil.which("fluidsynth") is not None

def validate_soundfont(path):
    file = Path(path)
    if not file.is_file() or file.suffix.lower() not in (".sf2", ".sf3"):
        raise ValueError("Select a local .sf2 or .sf3 SoundFont file")
    size = file.stat().st_size
    if not 64 <= size <= MAX_SF_BYTES:
        raise ValueError("SoundFont size outside supported limits")
    # SF2 is RIFF/sfbk; SF3 is SoundFont-compatible, also RIFF/sfbk.
    with file.open("rb") as stream:
        head = stream.read(12)
    if not (head.startswith(b"RIFF") and head[8:12] == b"sfbk"):
        raise ValueError("Selected file does not have a SoundFont header")
    return file

def render_soundfont(performance, soundfont, destination, rate=44100, runner=None):
    """Render a Score to new stereo 16-bit WAV, atomically.

    Never invokes a shell. A result must be recognizable PCM WAV before it is
    committed to the requested path. Creates only disposable temp files.
    """
    p = performance.validated()
    if p.duration_seconds > MAX_RENDER_SECONDS:
        raise ValueError("SoundFont preview/export supports up to five minutes")
    if rate not in (44100, 48000):
        raise ValueError("Unsupported SoundFont output sample rate")
    binary = shutil.which("fluidsynth")
    if binary is None:
        raise RuntimeError("FluidSynth command-line executable is not installed")
    sf = validate_soundfont(soundfont)
    dest = Path(destination)
    if not dest.parent.is_dir():
        raise FileNotFoundError("WAV output directory does not exist")
    if sf.resolve() == dest.resolve():
        raise ValueError("Cannot overwrite the selected SoundFont")
    execute = runner or subprocess.run
    temp_output = None
    try:
        with tempfile.TemporaryDirectory(prefix="spider-score-") as folder:
            midi = Path(folder) / "notation.mid"
            wav = Path(folder) / "render.wav"
            export_performance_midi(p, midi)
            args = [
                binary, "-n", "-i", "-F", str(wav),
                "-T", "wav", "-O", "s16", "-r", str(rate),
                "-g", "0.6", str(sf), str(midi),
            ]
            # Forbid unbounded CLI hangs; no caller shell, no privileged access.
            try:
                finished = execute(args, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, timeout=180,
                                   check=False)
            except subprocess.TimeoutExpired:
                raise RuntimeError("FluidSynth exceeded its 180-second rendering limit") from None
            if finished.returncode:
                raise RuntimeError(
                    "FluidSynth could not render these notes with the selected SoundFont")
            if not wav.is_file() or wav.stat().st_size < 44:
                raise RuntimeError("FluidSynth did not produce a playable WAV file")
            with wave.open(str(wav), "rb") as audio:
                if audio.getnchannels() != 2 or audio.getsampwidth() != 2 or audio.getframerate() != rate:
                    raise RuntimeError("FluidSynth produced an unsupported PCM format")
                if audio.getnframes() == 0:
                    raise RuntimeError("Rendered WAV contains no frames")
            fd, temp_output = tempfile.mkstemp(prefix=".spider-score-", suffix=".wav.tmp",
                                               dir=str(dest.parent))
            with os.fdopen(fd, "wb") as stream, wav.open("rb") as src:
                shutil.copyfileobj(src, stream, 1024 * 1024)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_output, dest)
    finally:
        if temp_output is not None:
            Path(temp_output).unlink(missing_ok=True)
    return dest
