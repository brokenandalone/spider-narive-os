"""Explicit owner-triggered LOCAL 3-second Webbie hearing self-test.

Never automatic. Consent must be obtained in the GUI BEFORE calling this
module. Captures a single WAV in owner-only XDG_RUNTIME_DIR (tmpfs on normal
Linux setups), transcribes with existing local Whisper, then removes ALL
temporary files. No speech identity/authentication or desktop command.
The resident listener may be using the microphone concurrently.
"""
from __future__ import annotations
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile

CAPTURE_SECONDS=3
CAPTURE_TIMEOUT=8
WHISPER_TIMEOUT=35
DEFAULT_RUNTIME=Path(os.environ.get("XDG_RUNTIME_DIR",
                                     f"/run/user/{os.getuid()}"))/"spider-os"
DEFAULT_MODEL=Path(os.environ.get(
    "WEBBIE_WHISPER_MODEL",
    "/usr/local/share/spider-os/whisper/ggml-base.en.bin"))


def run_hearing_test(*, approved=False, runtime=DEFAULT_RUNTIME,
                     whisper_bin=None, model=DEFAULT_MODEL,
                     recorder=None, runner=None):
    """Return the live local Whisper result only, NEVER a voice authorization."""
    if approved is not True:
        raise PermissionError("Hearing test needs a fresh owner GUI confirmation")
    runtime=Path(runtime)
    model=Path(model)
    whisper_bin=whisper_bin or shutil.which("whisper-cli")
    recorder=recorder or shutil.which("arecord")
    runner=runner or subprocess.run
    if not whisper_bin or not recorder or not model.is_file():
        return "Cannot test hearing: local arecord, Whisper or its model is missing."
    if (runtime.is_symlink() or not runtime.is_dir()):
        return "Cannot test hearing: private runtime directory is missing."
    info=runtime.stat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid()
            or info.st_mode & 0o077):
        return "Cannot test hearing: runtime directory is not private."
    try:
        # TemporaryDirectory uses mode 0700, and the actual WAV is on the
        # runtime filesystem. None of this is stored in long-term memory.
        with tempfile.TemporaryDirectory(
                prefix=".webbie-hearing-",dir=runtime) as folder:
            folder=Path(folder)
            wav=folder/"input.wav"
            base=folder/"recognized"
            record_cmd=[str(recorder),"-q","-f","S16_LE",
                        "-r","16000","-c","1","-d",str(CAPTURE_SECONDS),str(wav)]
            try:
                recorded=runner(
                    record_cmd,stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,timeout=CAPTURE_TIMEOUT,
                    check=False)
            except (OSError,subprocess.TimeoutExpired):
                return ("Microphone capture failed or timed out. "
                        "The resident Webbie listener may already be using the device.")
            if recorded.returncode!=0 or not wav.is_file():
                return ("The microphone did not provide a three-second sample. "
                        "Check input-device selection and concurrent capture.")
            # Never follow a symlink or transcribe oversized unexpected data.
            if wav.is_symlink() or not 44<=wav.stat().st_size<=1_000_000:
                return "The captured audio format was invalid."
            speak_cmd=[str(whisper_bin),"-m",str(model),"-f",str(wav),
                       "-l","en","-nt","-otxt","-of",str(base)]
            try:
                recognized=runner(
                    speak_cmd,stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,timeout=WHISPER_TIMEOUT,
                    check=False)
            except (OSError,subprocess.TimeoutExpired):
                return "Local speech transcription failed or timed out."
            result=folder/"recognized.txt"
            if recognized.returncode!=0 or not result.is_file():
                return "Whisper did not return a transcript from this sample."
            if result.is_symlink() or result.stat().st_size>4096:
                return "Whisper returned an invalid transcript."
            text=result.read_text(encoding="utf-8",errors="replace").strip()
            if not text or text.lower() in ("[blank_audio]","[silence]","(silence)"):
                return "Microphone capture completed, but Whisper heard no clear words."
            clean=" ".join(text.split())[:240]
            return (f'Webbie heard: "{clean}". This is only a '
                    "temporary hearing test, not speaker verification.")
    except (OSError,ValueError):
        return "Hearing test could not complete in the private runtime directory."
