"""Webbie Voice Lab: read-only microphone pipeline and trust readiness.

No audio capture, microphone enumeration requiring permissions, cloud calls,
OS service restart, enrollment, transcription, voiceprint material or changes
to models. This checks whether static components appear present only.
"""
from __future__ import annotations
import json
from pathlib import Path
import shutil
import os
import stat
from runtime_readiness import DEFAULT_AGENT, _private_json
from voice_metrics import display_meter
from speaker_provider_loader import _pinned_source

DEFAULT_CONFIG=Path(__file__).resolve().parents[1]/"config/default.json"
DEFAULT_MODEL=Path("/usr/local/share/spider-os/whisper/ggml-base.en.bin")
DEFAULT_VOICE=Path(__file__).resolve().parents[1]/"voice"

def inspect_voice_lab(*, config_path=DEFAULT_CONFIG, model_path=None,
                      voice_path=DEFAULT_VOICE, executable=None, which=None,
                      agent_path=DEFAULT_AGENT):
    which=which or shutil.which
    config={}
    try:
        target=Path(config_path)
        if (not target.is_symlink() and target.is_file()
                and target.stat().st_size<20000):
            data=json.loads(target.read_text(encoding="utf-8"))
            if isinstance(data,dict):
                config=data
    except (OSError,ValueError,UnicodeError):
        pass
    audio=config.get("speech_recognition")
    audio=audio if isinstance(audio,dict) else {}
    voice=config.get("speaker_verification")
    voice=voice if isinstance(voice,dict) else {}
    model=Path(model_path) if model_path is not None else Path(
        os.environ.get("WEBBIE_WHISPER_MODEL",
                       str(audio.get("model_path") or DEFAULT_MODEL)))
    engine=executable if executable is not None else which("whisper-cli")
    alsa=which("arecord")
    provider=Path(voice_path)/"speaker_voice_provider.py"
    configured=voice.get("enabled") is True
    pinned=_pinned_source(Path(voice_path),voice.get("provider_sha256")) is not None
    return {
        "whisper_available":bool(engine and Path(engine).is_file()),
        "whisper_model_available":bool(model.is_file() and not model.is_symlink()),
        "arecord_available":bool(alsa and Path(alsa).is_file()),
        "voiceprint_opted_in":configured,
        "voiceprint_file_present":bool(provider.is_file() and not provider.is_symlink()),
        "voiceprint_source_pinned":pinned,
        "voiceprint_verified":False,
        "engine":"whisper.cpp",
        "intake":_private_json(agent_path).get("voice_intake"),
        "message":"Presence checks only. No microphone audio was sampled.",
    }

def voice_lab_report(result):
    def report(k):
        return "PRESENT" if result.get(k) is True else "NOT CONFIRMED"
    lines=["WEBBIE VOICE LAB · READ-ONLY",
        "Whisper executable: "+report("whisper_available"),
        "Whisper language model: "+report("whisper_model_available"),
        "ALSA recording utility: "+report("arecord_available"),
        "Owner opted into local speaker verifier: "+(
            "YES" if result.get("voiceprint_opted_in") else "NO"),
        "Offline verifier module installed: "+report("voiceprint_file_present"),
        "Owner-approved verifier code hash matches: "+report("voiceprint_source_pinned"),
        "Cory/Shayna speaker identity: NOT VERIFIED BY THIS CHECK",
        "Emergency STOP remains available even without speaker identity.",
        "The voice model provider is not bundled or auto-installed.",
        "No microphone audio, voiceprints or conversations were read.",
        "",display_meter(result.get("intake"))]
    return "\n".join(lines)
