#!/usr/bin/env python3

import json
from pathlib import Path
import re
import urllib.error
import urllib.request


DEFAULT_MODEL = "qwen3:1.7b"
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
CONFIG_FILE = Path(__file__).resolve().parents[1] / 'config/default.json'


def preferred_model(path=CONFIG_FILE):
    """Use the owner's local Ollama model choice; do not pull new models."""
    try:
        config = json.loads(Path(path).read_text(encoding='utf-8'))
        name = config.get('ollama', {}).get('model')
        if isinstance(name, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,99}', name):
            return name
    except (OSError, UnicodeError, ValueError, AttributeError, TypeError):
        pass
    return DEFAULT_MODEL


SYSTEM_PROMPT = """
You are Webbie, the resident AI built into Spider OS.

You are part of the operating system, not a website.

Your primary user is Cory.

Use the name:
- Cory normally.
- Justin inside Studio.
- Spider inside Kali Bay.
- Writer inside Author Bay.
- Student inside School/Study.

Be concise when responding by voice.
Be more detailed when responding in the graphical interface.

You help operate Spider OS, organize information, work with Forage and
Deep Forage, launch workspaces, support study and creative work, and
assist with normal computer tasks.

Never claim an action succeeded unless Spider OS actually performed it.
""".strip()


def ask_ollama(message, context_name="Cory", model=None):
    prompt = (
        SYSTEM_PROMPT
        + "\n\nCurrent user name: "
        + context_name
    )

    payload = {
        "model": preferred_model() if model is None else model,
        "stream": False,
        "messages": [
            {
                "role": "system",
                "content": prompt,
            },
            {
                "role": "user",
                "content": message,
            },
        ],
    }

    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json"
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=120,
        ) as response:
            data = json.loads(
                response.read().decode("utf-8")
            )

        return (
            data.get("message", {})
            .get("content", "")
            .strip()
        )

    except (
        urllib.error.URLError,
        TimeoutError,
        ValueError,
        KeyError,
    ):
        return None


def built_in_response(message, context_name="Cory"):
    lower = message.lower().strip()

    if lower in {
        "hello",
        "hi",
        "hey",
    }:
        return f"Hey {context_name}. I'm here."

    if "who are you" in lower:
        return (
            "I'm Webbie, the resident AI inside Spider OS."
        )

    if "what are you" in lower:
        return (
            "I'm Webbie, the resident AI layer of Spider OS."
        )

    return (
        f"I heard you, {context_name}. "
        "My local language model is not online yet, "
        "but my Spider OS controls are available."
    )


def respond(message, context_name="Cory"):
    answer = ask_ollama(
        message,
        context_name=context_name,
    )

    if answer:
        return answer

    return built_in_response(
        message,
        context_name=context_name,
    )
