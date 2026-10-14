"""Resident AI readiness without changing Webbie's installed brain or voice."""
from __future__ import annotations
from pathlib import Path
import shutil

from operations_services import _command, DEFAULT_ROOT


def assistant_readiness(root=DEFAULT_ROOT):
    root = Path(root)
    # Read only presence/availability, never the private voice identity store.
    files = {
        "resident_agent": "webbie/agent/webbie.py",
        "speaker_trust": "webbie/agent/voice_trust.py",
        "audio_listener": "webbie/voice/whisper_listener.py",
        "screen_panel": "the-web/shell/webbie_computer_panel.py",
        "cognitive_center": "the-web/shell/webbie_cognitive_center.py",
        "local_model_config": "webbie/brain/local_models.py",
    }
    availability = {}
    for name, relative in files.items():
        source = root / relative
        availability[name] = source.is_file() and not source.is_symlink()
    raw = _command("ollama", "list", timeout=8) if shutil.which("ollama") else None
    models = []
    if raw:
        # Ollama model tags only; never requests prompts or model downloads.
        for line in raw.splitlines()[1:101]:
            parts = line.split()
            if parts and len(parts[0]) <= 130:
                models.append(parts[0])
    return {
        "workspace": "Webbie",
        "mode": "read_only",
        "operation": "assistant_readiness",
        "resident_service": _command("systemctl", "--user", "show", "webbie.service",
                                    "--property=ActiveState", "--value") or "unavailable",
        "installed_modules": availability,
        "ollama_available": bool(shutil.which("ollama")),
        "local_models_advertised": models,
        "installed_qwen3_8b_advertised": "qwen3:8b" in models,
        "online_natasha_config_not_modified": True,
        "note": "Module presence and local model inventory only. This does not "
                "test voice identity, wake/STOP, camera consent, TTS, Webbie's "
                "model configuration or real computer-control permissions.",
    }
