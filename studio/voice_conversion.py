"""Offline RVC conversion for an explicitly selected and trained voice model.

Converts an *isolated* original/AI vocal WAV. Do not feed a mastered mix or
claim song stems, pitch correction, voice training, or remixing occurred.
Official CLI: https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI/blob/main/docs/en/cli.md
"""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import threading
import time
import wave


class ConversionError(ValueError):
    pass


DEFAULT_RVC = Path.home() / ".local/share/spider-os/voice-engine/Retrieval-based-Voice-Conversion-WebUI"
DEFAULT_OUTPUT = Path.home() / "Documents/Spider Studio/Music/My Voice/Converted"


def valid_file(path, suffixes, label):
    file = Path(path).expanduser()
    if not file.is_file() or file.is_symlink() or file.suffix.lower() not in suffixes:
        raise ConversionError(f"Select a valid {label} file.")
    if not 0 < file.stat().st_size <= 2 * 1024 * 1024 * 1024:
        raise ConversionError(f"{label} file is empty or too large.")
    return file.resolve()


def conversion_command(rvc_dir, python_bin, model, src, dest, index=None, pitch=0):
    """Create a fixed argument vector for the documented RVC CLI, never a shell."""
    root = Path(rvc_dir)
    script = root / "infer/cli.py"
    if root.is_symlink() or not script.is_file() or script.is_symlink():
        raise ConversionError("Verified local RVC infer/cli.py is not installed.")
    python = Path(python_bin)
    if python.is_symlink() or not python.is_file():
        raise ConversionError("RVC's isolated Python environment is not ready.")
    model_path = valid_file(model, {".pth"}, "trained voice model")
    src_path = valid_file(src, {".wav"}, "isolated vocal WAV")
    if not isinstance(pitch, int) or abs(pitch) > 12:
        raise ConversionError("Pitch transposition must be between -12 and +12 semitones.")
    output = Path(dest)
    if output.suffix.lower() != ".wav" or output.exists() or output.is_symlink():
        raise ConversionError("Choose a new WAV output, never overwrite a recorded voice.")
    if output.parent.is_symlink():
        raise ConversionError("Converted output cannot go into a symlinked directory.")
    args = [str(python), str(script), "--model", str(model_path),
            "--input", str(src_path), "--output", str(output), "--pitch", str(pitch),
            "--f0-method", "rmvpe", "--index-rate", "0.75" if index else "0"]
    if index:
        idx = valid_file(index, {".index"}, "RVC index")
        args += ["--index", str(idx)]
    return args


def convert_vocal(model, vocal, *, index=None, pitch=0, rvc_dir=None, output_root=None,
                  python_bin=None, timeout=1800, stop=None):
    root = Path(rvc_dir) if rvc_dir else DEFAULT_RVC
    interpreter = Path(python_bin) if python_bin else root / ".venv/bin/python"
    destination = Path(output_root) if output_root else DEFAULT_OUTPUT
    if destination.is_symlink():
        raise ConversionError("Output folder must not be a symlink.")
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(destination, 0o700)
    folder = Path(tempfile.mkdtemp(prefix="converted-", dir=destination))
    target = folder / "my-voice.wav"
    log = folder / "conversion.log"
    try:
        args = conversion_command(root, interpreter, model, vocal, target, index=index, pitch=pitch)
        stop = stop if stop is not None else threading.Event()
        if stop.is_set():
            raise ConversionError("Conversion was cancelled before model access.")
        with log.open("xb") as stream:
            os.chmod(log, 0o600)
            proc = subprocess.Popen(args, cwd=root, stdin=subprocess.DEVNULL,
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
                    raise ConversionError("Voice conversion stopped or timed out. Original vocal preserved.")
                stop.wait(0.2)
        if proc.returncode:
            raise ConversionError("Local RVC conversion failed. See the private conversion log.")
        if target.is_symlink() or not target.is_file():
            raise ConversionError("RVC finished without producing a WAV vocal.")
        with wave.open(str(target), "rb") as audio:
            if audio.getnframes() == 0 or not audio.getframerate():
                raise ConversionError("RVC produced empty WAV audio.")
        os.chmod(target, 0o600)
        return target
    except (OSError, subprocess.TimeoutExpired, wave.Error, EOFError) as error:
        raise ConversionError("Local RVC conversion could not complete.") from error
