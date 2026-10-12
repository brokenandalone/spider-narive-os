#!/usr/bin/env python3

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path


WHISPER_BIN = (
    shutil.which("whisper-cli")
    or "/usr/local/bin/whisper-cli"
)

MODEL_PATH = Path(
    os.environ.get(
        "WEBBIE_WHISPER_MODEL",
        "/usr/local/share/spider-os/whisper/ggml-base.en.bin",
    )
)

CHUNK_SECONDS = int(
    os.environ.get(
        "WEBBIE_WHISPER_CHUNK_SECONDS",
        "4",
    )
)

RUNTIME_DIR = Path(
    os.environ.get(
        "XDG_RUNTIME_DIR",
        f"/run/user/{os.getuid()}",
    )
) / "spider-os"

SPEAKING_MARKER = (
    RUNTIME_DIR
    / "webbie-speaking"
)

# Ephemeral visibility-only indicator, never used to authorize speech.
LISTENING_MARKER = RUNTIME_DIR / "webbie-listening"


def capture_indicator_start():
    """Create an owner-only capture marker; don't follow an existing symlink."""
    try:
        if LISTENING_MARKER.is_symlink():
            return False
        fd=os.open(str(LISTENING_MARKER), os.O_WRONLY | os.O_CREAT |
                   os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        os.close(fd)
        return True
    except OSError:
        return False


def capture_indicator_stop(created):
    if created:
        try:
            LISTENING_MARKER.unlink(missing_ok=True)
        except OSError:
            pass


def ready():
    return (
        Path(WHISPER_BIN).exists()
        and MODEL_PATH.exists()
        and shutil.which("arecord")
    )


def record_chunk(path, seconds=None):
    result = subprocess.run(
        [
            "arecord",
            "-q",
            "-f",
            "S16_LE",
            "-r",
            "16000",
            "-c",
            "1",
            "-d",
            str(CHUNK_SECONDS if seconds is None else seconds),
            path,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )

    return result.returncode == 0


def transcribe(path):
    output_base = (
        str(path)
        + ".webbie"
    )

    output_file = Path(
        output_base + ".txt"
    )

    command = [
        WHISPER_BIN,
        "-m",
        str(MODEL_PATH),
        "-f",
        str(path),
        "-l",
        "en",
        "-nt",
        "-otxt",
        "-of",
        output_base,
    ]

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=120,
            check=False,
        )

        if result.returncode != 0:
            return ""

        if not output_file.exists():
            return ""

        text = output_file.read_text(
            encoding="utf-8",
            errors="replace",
        ).strip()

        junk = {
            "",
            "[blank_audio]",
            "[silence]",
            "(silence)",
            "[music]",
            "(music)",
        }

        if text.lower() in junk:
            return ""

        return text

    except Exception:
        return ""

    finally:
        try:
            output_file.unlink()
        except OSError:
            pass


def listen_forever(
    on_text,
    should_continue,
    on_interrupt=None,
    verifier=None,
):
    if not ready():
        raise RuntimeError(
            "whisper.cpp or its model is not installed"
        )

    RUNTIME_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    while should_continue():

        # When available, the stop-only interrupt route continues listening
        # during playback. Everything but an explicit stop is discarded.
        talking_at_start = SPEAKING_MARKER.exists()
        if talking_at_start and on_interrupt is None:
            time.sleep(0.25)
            continue

        audio_path = None

        try:
            with tempfile.NamedTemporaryFile(
                prefix="webbie-",
                suffix=".wav",
                delete=False,
            ) as temp:
                audio_path = temp.name

            indicator = capture_indicator_start()
            try:
                recorded = record_chunk(
                    audio_path, seconds=2 if talking_at_start else None
                )
            finally:
                capture_indicator_stop(indicator)
            if not recorded:
                time.sleep(1)
                continue

            talking_during_capture = (
                talking_at_start or SPEAKING_MARKER.exists()
            )
            if talking_during_capture and on_interrupt is None:
                continue
            phrase = transcribe(audio_path)
            if phrase:
                if talking_during_capture:
                    # Never treat a TTS echo as a normal assistant command.
                    on_interrupt(phrase)
                else:
                    # The optional voiceprint provider receives the exact
                    # short WAV used for THIS transcription, not the words.
                    # A missing provider gives no trusted speaker evidence.
                    if verifier is None:
                        on_text(phrase)
                    else:
                        evidence=None
                        try:
                            evidence=verifier(audio_path)
                        except Exception:
                            # Do not leak audio metadata or provider errors.
                            pass
                        on_text(phrase, evidence)

        finally:
            if audio_path:
                try:
                    Path(
                        audio_path
                    ).unlink()
                except OSError:
                    pass


if __name__ == "__main__":
    print(
        "whisper.cpp ready:"
        if ready()
        else
        "whisper.cpp unavailable"
    )
