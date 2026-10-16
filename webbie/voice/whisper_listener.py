#!/usr/bin/env python3

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from audio_gate import wav_has_activity, normalize_transcript, TranscriptDeduper


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
            str(seconds or CHUNK_SECONDS),
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

        return normalize_transcript(text)

    except Exception:
        return ""

    finally:
        try:
            output_file.unlink()
        except OSError:
            pass


def listen_forever(on_text, should_continue):
    if not ready():
        raise RuntimeError("whisper.cpp or its model is not installed")
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    deduper = TranscriptDeduper()
    # Always pass a recording to speaker_guard, including during barge-in.
    allow_barge_in = os.environ.get("WEBBIE_ALLOW_BARGE_IN", "1") == "1"

    while should_continue():
        speaking_at_start = SPEAKING_MARKER.exists()
        if speaking_at_start and not allow_barge_in:
            time.sleep(.15)
            continue
        audio_path = None
        try:
            with tempfile.NamedTemporaryFile(prefix="webbie-",suffix=".wav",delete=False) as temp:
                audio_path = temp.name
            # Shorter microphone sample while Webbie speaks for "Webbie, stop".
            duration = 2 if speaking_at_start else CHUNK_SECONDS
            if not record_chunk(audio_path, duration):
                time.sleep(.5)
                continue
            during_speech = speaking_at_start or SPEAKING_MARKER.exists()
            if during_speech and not allow_barge_in:
                continue
            if not wav_has_activity(audio_path):
                continue
            phrase = transcribe(audio_path)
            if phrase and deduper.accept(phrase):
                on_text(phrase, audio_path, during_speech)
        finally:
            if audio_path:
                try:
                    Path(audio_path).unlink()
                except OSError:
                    pass

if __name__ == "__main__":
    print("whisper.cpp ready:" if ready() else "whisper.cpp unavailable")
