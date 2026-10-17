"""Read-only local model selection for Webbie add-ons.

Never pulls, swaps, downloads or modifies Ollama models or owner config.
An explicitly configured name takes precedence; if unavailable, report the
failure rather than secretly replacing it. This is for new add-ons only.
The owner's customized running conversation engine stays authoritative.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request

TAGS_URL = 'http://127.0.0.1:11434/api/tags'
FALLBACK_VISION = 'gemma3:4b'
FALLBACK_BRAIN = 'qwen3:1.7b'
MODEL_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,99}$')


def installed_models(*, opener=None, timeout=2):
    opener = opener or urllib.request.urlopen
    try:
        with opener(TAGS_URL, timeout=timeout) as response:
            if response.geturl() != TAGS_URL:
                return ()
            packet = json.loads(response.read(200000).decode('utf-8'))
    except (OSError, UnicodeError, ValueError, urllib.error.URLError, TimeoutError):
        return ()
    models = []
    for row in packet.get('models', []) if isinstance(packet, dict) else []:
        name = row.get('name') if isinstance(row, dict) else None
        if isinstance(name, str) and MODEL_NAME.fullmatch(name):
            models.append(name)
    return tuple(models)


def configured_choice(kind, *, config_path=None, env=None):
    if kind not in ('vision', 'brain'):
        raise ValueError('Unknown model role')
    env = os.environ if env is None else env
    var = 'WEBBIE_VISION_MODEL' if kind == 'vision' else 'WEBBIE_BRAIN_MODEL'
    value = env.get(var)
    if value is None:
        config_path = (Path(config_path) if config_path is not None
                       else Path('/usr/local/lib/spider-os/webbie/config/default.json'))
        try:
            config = json.loads(config_path.read_text(encoding='utf-8'))
        except (OSError, UnicodeError, ValueError):
            config = {}
        if isinstance(config, dict):
            if kind == 'brain':
                value = config.get('ollama', {}).get('model') if isinstance(
                    config.get('ollama'), dict) else None
            else:
                vision = config.get('vision')
                value = vision.get('model') if isinstance(vision, dict) else None
    if value is None or value == '':
        return None
    if not isinstance(value, str) or not MODEL_NAME.fullmatch(value):
        raise ValueError('Configured Ollama model name is invalid')
    return value


def choose_local_model(kind, *, names=None, config_path=None, env=None):
    if kind not in ('brain', 'vision'):
        raise ValueError('Unknown model role')
    configured = configured_choice(kind, config_path=config_path, env=env)
    available = (installed_models() if names is None else tuple(names))
    if configured:
        if configured not in available:
            raise RuntimeError('Configured Webbie model is not currently installed')
        return configured
    preferred = (('qwen3-vl:2b-instruct', 'qwen3-vl:2b', 'gemma3:4b')
                 if kind == 'vision' else
                 ('qwen3:8b', 'qwen3:4b', 'qwen3:1.7b'))
    for name in preferred:
        if name in available:
            return name
    # No hidden pull or unexpected cloud fallback.
    raise RuntimeError('No compatible local Webbie ' + kind + ' model is available')
