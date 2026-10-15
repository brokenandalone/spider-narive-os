"""Shared Australian voice engine for Nova's one native BCN DJ service.

Uses Webbie's existing per-user Piper installation, not a second voice daemon.
Never plays sound: generated files are returned for Media Center's audio mixer.
"""
import os
import shutil
import subprocess
import wave
from pathlib import Path

ONLINE_VOICE = "en-AU-NatashaNeural"
SPEAKERS = {
    "bindi": 1,
    "marlo": 2,
    "kirra": 3,
    "matilda": 7,
    "tully": 8,
    "willow": 9,
}
VOICES = ("auto", "natasha", *SPEAKERS)


def normalize_voice(value):
    """Reject arbitrary paths, subprocess switches or unknown speaker names."""
    name = str(value or "auto").strip().lower()[:32]
    return name if name in VOICES else "auto"


def configured_voice():
    return normalize_voice(os.environ.get("SPIDER_NOVA_VOICE", "auto"))


def piper_files(home=None):
    root = Path(home) if home is not None else Path.home()
    base = root / ".local/share/spider-os/webbie-neural-preview"
    model = base / "models/en_AU-librivox-medium.onnx"
    return base / "venv/bin/python3", model, Path(str(model) + ".json")


def available_profiles(home=None):
    python, model, meta = piper_files(home)
    offline = python.is_file() and os.access(python, os.X_OK) and model.is_file() and meta.is_file()
    return {
        "selected": configured_voice(),
        "voices": list(VOICES),
        "piperReady": offline,
        "fallback": "matilda" if offline else "espeak-ng",
    }


def valid_wav(file):
    try:
        if not file.is_file() or file.stat().st_size < 44:
            return False
        with wave.open(str(file), "rb") as audio:
            return audio.getnframes() > 0 and audio.getnchannels() >= 1
    except (OSError, EOFError, wave.Error):
        return False


def synthesize(text, ident, profile=None, cache=None, home=None, runner=None, which=None, allow_espeak=True, report=None):
    """Try chosen voice, then recover safely. Return validated audio Path.

    'auto': Matilda offline first, then Natasha online.
    Piper name: chosen speaker, Matilda fallback, then Natasha.
    When allow_espeak=False, NEVER output the robotic eSpeak voice.
    The report dictionary records the engine actually used, if provided.
    """
    text = str(text or "").strip()
    if not text or len(text) > 1200:
        raise ValueError("Nova voice requires short, nonempty announcement text")
    ident = str(ident or "")
    if not ident or not all(ch.isalnum() or ch in "-_" for ch in ident) or len(ident) > 100:
        raise ValueError("Invalid Nova voice audio identifier")
    cache = Path(cache) if cache is not None else Path.home() / ".cache/spider-os/ai-dj"
    cache.mkdir(parents=True, exist_ok=True)
    run = runner or subprocess.run
    find = which or shutil.which
    choice = normalize_voice(profile if profile is not None else configured_voice())
    wav = cache / (ident + ".wav")
    mp3 = cache / (ident + ".mp3")
    piper_python, model, config = piper_files(home)
    piper_ready = piper_python.is_file() and os.access(piper_python, os.X_OK) and model.is_file() and config.is_file()

    def piper(name):
        if not piper_ready:
            return None
        try:
            wav.unlink(missing_ok=True)
            run([str(piper_python), "-m", "piper", "-m", str(model),
                 "-s", str(SPEAKERS[name]), "-f", str(wav)],
                input=text + "\n", text=True, check=True, timeout=30,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if valid_wav(wav):
                return wav
        except (OSError, subprocess.SubprocessError):
            pass
        return None

    def natasha():
        edge = Path("/opt/spider-webbie/bin/edge-tts")
        binary = str(edge) if edge.is_file() and os.access(edge, os.X_OK) else find("edge-tts")
        if not binary:
            return None
        try:
            mp3.unlink(missing_ok=True)
            run([binary, "--voice", ONLINE_VOICE, "--text", text,
                 "--write-media", str(mp3)], check=True, timeout=22,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if mp3.is_file() and mp3.stat().st_size > 100:
                return mp3
        except (OSError, subprocess.SubprocessError):
            pass
        return None

    def espeak():
        binary = find("espeak-ng")
        if not binary:
            return None
        try:
            wav.unlink(missing_ok=True)
            run([binary, "-v", "en-au+f3", "-s", "165", "-w", str(wav), text],
                check=True, timeout=10, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL)
            if valid_wav(wav):
                return wav
        except (OSError, subprocess.SubprocessError):
            pass
        return None

    if choice in SPEAKERS:
        order = [(choice, lambda: piper(choice))]
        if choice != "matilda":
            order.append(("matilda", lambda: piper("matilda")))
        order.append(("natasha", natasha))
    elif choice == "natasha":
        order = [("natasha", natasha), ("matilda", lambda: piper("matilda"))]
    else:
        order = [("matilda", lambda: piper("matilda")), ("natasha", natasha)]
    if allow_espeak:
        order.append(("espeak-ng", espeak))

    for engine_name, engine in order:
        result = engine()
        if result is not None:
            if isinstance(report, dict):
                report.update({"engine": engine_name, "voiceProfileRequested": choice,
                               "usedFallback": engine_name != (choice if choice != "auto" else "matilda")})
            return result
    raise RuntimeError("Nova neural voices unavailable: verify Webbie's Australian Piper voice installation or Natasha network access; robotic eSpeak was not used.")
