"""Local source separation using the documented RVC PyMSS CLI.

No system packages changed. The model can download weights on first use only
after the user explicitly requests separation. Outputs are inspected rather than
assuming file names or claiming that a model always isolates voices perfectly.
"""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import threading
import time
import wave

try:
    from .song_mix import valid_wav
except ImportError:
    from song_mix import valid_wav

DEFAULT_RVC = Path.home() / ".local/share/spider-os/voice-engine/Retrieval-based-Voice-Conversion-WebUI"
DEFAULT_OUTPUT = Path.home() / "Documents/Spider Studio/Music/Separated"
MODEL = "model_mel_band_roformer_karaoke_aufr33_viperx_sdr_10.1956.ckpt"


class SeparationError(ValueError):
    pass


def command(rvc_root, python, source, destination, device="cpu"):
    root, exe = Path(rvc_root), Path(python)
    if root.is_symlink() or not (root / "tools/pymss/cli.py").is_file():
        raise SeparationError("Local RVC PyMSS CLI is missing.")
    if exe.is_symlink() or not exe.is_file():
        raise SeparationError("Local RVC Python environment is missing.")
    if device not in ("cpu", "cuda", "auto"):
        raise SeparationError("Device must be cpu, cuda or auto.")
    audio = valid_wav(source, "generated song")
    target = Path(destination)
    if target.is_symlink() or not target.is_dir():
        raise SeparationError("Create a private output directory before starting.")
    return [str(exe), "-m", "tools.pymss.cli", "infer", MODEL,
            "--input", str(audio), "--output", str(target),
            "--device", device, "--format", "wav"]


def separate(source, *, rvc_root=None, output_root=None, device="cpu",
             timeout=2400, stop=None):
    root = Path(rvc_root) if rvc_root else DEFAULT_RVC
    python = root / ".venv/bin/python"
    destroot = Path(output_root) if output_root else DEFAULT_OUTPUT
    if destroot.is_symlink():
        raise SeparationError("Output parent cannot be a symlink.")
    source = valid_wav(source, "generated song")
    stop = stop or threading.Event()
    if stop.is_set():
        raise SeparationError("Separation cancelled before starting.")
    destroot.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(destroot, 0o700)
    destination = Path(tempfile.mkdtemp(prefix="stems-", dir=destroot))
    log = destination / "separate.log"
    args = command(root, python, source, destination, device)
    try:
        with log.open("xb") as stream:
            os.chmod(log, 0o600)
            process = subprocess.Popen(args, cwd=root, stdin=subprocess.DEVNULL,
                                       stdout=stream, stderr=subprocess.STDOUT)
            deadline = time.monotonic() + timeout
            while process.poll() is None:
                if stop.is_set() or time.monotonic() > deadline:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill(); process.wait(timeout=5)
                    raise SeparationError("Stem extraction stopped; original song preserved.")
                stop.wait(0.2)
        if process.returncode:
            raise SeparationError("PyMSS separation failed. Inspect the private job log.")
        # PyMSS versions name stems differently, so do not automatically choose
        # an ambiguous file as the 'isolated vocal' or 'instrumental' source.
        valid = []
        for file in destination.rglob("*.wav"):
            if file.is_symlink() or file.resolve() == source or not file.is_file():
                continue
            try:
                with wave.open(str(file), "rb") as reader:
                    if reader.getnframes() > 0 and reader.getframerate() > 0:
                        os.chmod(file, 0o600)
                        valid.append(file)
            except (wave.Error, EOFError, OSError):
                continue
        if len(valid) < 2:
            raise SeparationError("Expected vocal and instrumental outputs; inspect the job folder.")
        return destination, sorted(valid)
    except OSError as error:
        raise SeparationError("Could not run the local stem separator.") from error
