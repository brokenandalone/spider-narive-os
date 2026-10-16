#!/usr/bin/env python3

import json
from collections import deque
from threading import RLock
import urllib.error
import urllib.request


DEFAULT_MODEL = "qwen3:1.7b"
_HISTORY = {}
_HISTORY_LOCK = RLock()
_MAX_SESSIONS = 12
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"


SYSTEM_PROMPT = """
You are Webbie, the resident AI built into Spider OS.

You are part of the operating system, not a website.

Your primary user is Cory.

Use the name:
- Cory normally.
- Justin inside Studio.
- Spider inside Kali Bay.

Be concise when responding by voice.
Be more detailed when responding in the graphical interface.

You help operate Spider OS, organize information, work with Forage and
Deep Forage, launch workspaces, support study and creative work, and
assist with normal computer tasks.

Never claim an action succeeded unless Spider OS actually performed it.
If speech sounds ambiguous, ask one short clarifying question.
Use natural direct language, without introductory filler.
Do not invent personal memories or actions.
""".strip()


def ask_ollama(message, context_name="Cory", model=DEFAULT_MODEL, history=None):
    prompt = (
        SYSTEM_PROMPT
        + "\n\nCurrent user name: "
        + context_name
    )

    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": prompt},
            *(history or []),
            {"role": "user", "content": message},
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


def _get_history(session_key):
    with _HISTORY_LOCK:
        return list(_HISTORY.get(session_key, ()))

def remember_exchange(session_key, user_message, assistant_message):
    """Short in-memory context separated by voice speaker and typed session."""
    if not user_message or not assistant_message:
        return
    with _HISTORY_LOCK:
        if session_key not in _HISTORY and len(_HISTORY) >= _MAX_SESSIONS:
            _HISTORY.pop(next(iter(_HISTORY)), None)
        history=_HISTORY.setdefault(session_key,deque(maxlen=8))
        history.append({"role":"user","content":str(user_message)[:900]})
        history.append({"role":"assistant","content":str(assistant_message)[:1400]})

def respond(message, context_name="Cory", session_key="typed"):
    answer=ask_ollama(message,context_name=context_name,
                      history=_get_history(session_key))
    if not answer:
        answer=built_in_response(message,context_name=context_name)
    remember_exchange(session_key,message,answer)
    return answer
