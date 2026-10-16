#!/usr/bin/env python3
"""Webbie AI V2: preserve full brain, bound stalls and use a local-only fallback.

Reconciled from the owner's tested source, with workspace advisory forwarding.
This is a subprocess of the existing user service, not an additional daemon.
"""
import atexit
import json
import os
import select
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRIMARY_PATH = HERE / "webbie_brain_primary.py"
_PRIMARY = None
_BUFFER = b""
_HISTORY = []


def _log(label, **fields):
    # No transcript, response, access token, memory text or speaker profile.
    tail = " ".join(f"{key}={value}" for key, value in fields.items())
    print(f"WEBBIE_AI_V2 {label} {tail}", file=sys.stderr, flush=True)


def _stop_primary():
    global _PRIMARY, _BUFFER
    proc = _PRIMARY
    _PRIMARY = None
    _BUFFER = b""
    if proc is None:
        return
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=1)
        except subprocess.TimeoutExpired:
            proc.kill()
            try:
                proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                pass
    for stream in (proc.stdin, proc.stdout):
        try:
            if stream:
                stream.close()
        except OSError:
            pass


def _ensure_primary():
    global _PRIMARY, _BUFFER
    if _PRIMARY is not None and _PRIMARY.poll() is None:
        return _PRIMARY
    _stop_primary()
    if not PRIMARY_PATH.is_file():
        raise RuntimeError("Missing primary brain worker")
    _PRIMARY = subprocess.Popen(
        [sys.executable, "-u", str(PRIMARY_PATH)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,
        bufsize=0,
        close_fds=True,
    )
    _BUFFER = b""
    _log("PRIMARY_STARTED", pid=_PRIMARY.pid)
    return _PRIMARY


def _primary_reply(request_id, message, context_name, advisory_context, seconds=14.0):
    global _BUFFER
    proc = _ensure_primary()
    data = json.dumps(
        {"id": request_id, "message": message, "context_name": context_name,
         "advisory_context": advisory_context}, ensure_ascii=False
    ) + "\n"
    try:
        proc.stdin.write(data.encode("utf-8"))
        proc.stdin.flush()
    except (OSError, BrokenPipeError) as exc:
        _stop_primary()
        raise RuntimeError("Primary brain disconnected") from exc
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if b"\n" in _BUFFER:
            raw, _BUFFER = _BUFFER.split(b"\n", 1)
            result = json.loads(raw)
            if result.get("id") != request_id:
                raise RuntimeError("Primary response ID mismatch")
            if not result.get("ok"):
                raise RuntimeError("Primary brain raised an exception")
            reply = str(result.get("reply") or "").strip()
            if reply:
                if "my local language model is not online yet" in reply.lower():
                    raise RuntimeError("Primary returned model-unavailable fallback")
                return reply
            raise RuntimeError("Primary brain returned an empty response")
        if proc.poll() is not None:
            raise RuntimeError("Primary brain exited unexpectedly")
        ready, _, _ = select.select(
            [proc.stdout], [], [],
            max(0.001, min(deadline - time.monotonic(), 0.5)),
        )
        if ready:
            chunk = os.read(proc.stdout.fileno(), 65536)
            if not chunk:
                raise RuntimeError("Primary brain closed stdout")
            _BUFFER += chunk
            if len(_BUFFER) > 1024 * 1024:
                raise RuntimeError("Primary response exceeds size limit")
    raise TimeoutError("Primary brain exceeded bounded wait")


def _fallback_reply(message, context_name):
    # Never accept a nonlocal endpoint: conversation stays on the PC.
    url = os.environ.get("WEBBIE_LOCAL_OLLAMA_CHAT_URL", "http://127.0.0.1:11434/api/chat")
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme, parsed.hostname, parsed.path) != ("http", "127.0.0.1", "/api/chat"):
        raise ValueError("Ollama fallback must use loopback /api/chat")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Unexpected Ollama URL components")
    recent = [
        {"role": role, "content": content[:900]}
        for role, content in _HISTORY[-6:]
    ]
    messages = [{"role": "system", "content": (
        "You are Webbie, the resident assistant for Spider OS. "
        f"Address the user in the {context_name} workspace naturally. "
        "Answer accurately and concisely. Do not claim to have run tools, "
        "changed files, controlled devices or obtained root access. "
        "You are responding using local Ollama while the full brain recovers."
    )}] + recent + [{"role": "user", "content": message[:6000]}]
    payload = {
        "model": "qwen3:8b", "stream": False, "think": False,
        "keep_alive": "30m",
        "options": {"num_predict": 120, "num_ctx": 4096},
        "messages": messages,
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    start = time.monotonic()
    with urllib.request.urlopen(request, timeout=10) as response:
        result_data = json.load(response)
    result = str(result_data.get("message", {}).get("content") or "").strip()
    _log("FALLBACK_RETURNED", seconds=round(time.monotonic() - start, 2), chars=len(result))
    if not result:
        raise RuntimeError("Fallback returned an empty answer")
    return result


def _answer(data):
    request_id = str(data.get("id", ""))
    message = str(data["message"])
    context_name = str(data.get("context_name", "Spider"))
    advisory_context = str(data.get("advisory_context") or "")[:3500]
    if len(message) > 15000:
        raise ValueError("Question too large")
    if len(context_name) > 100:
        raise ValueError("Context name too large")
    start = time.monotonic()
    try:
        wait = min(18.0, max(2.0, float(os.environ.get("WEBBIE_PRIMARY_WAIT_SECONDS", "14"))))
        answer = _primary_reply(request_id, message, context_name, advisory_context, seconds=wait)
        _log("PRIMARY_SUCCESS", seconds=round(time.monotonic() - start, 2))
        mode = "primary"
    except Exception as exc:
        _log("PRIMARY_FAILED", reason=type(exc).__name__,
             seconds=round(time.monotonic() - start, 2))
        _stop_primary()
        try:
            answer = _fallback_reply(message, context_name)
            mode = "local_fallback"
        except Exception as fallback_exc:
            _log("FALLBACK_FAILED", reason=type(fallback_exc).__name__)
            answer = ("My local AI reply is temporarily unavailable. "
                      "My desktop and built-in system commands are still available.")
            mode = "degraded"
    if mode != "degraded":
        _HISTORY.extend([("user", message[:900]), ("assistant", answer[:900])])
        if len(_HISTORY) > 8:
            del _HISTORY[:-8]
    _log("REQUEST_COMPLETE", mode=mode,
         seconds=round(time.monotonic() - start, 2))
    return {"id": request_id, "ok": True, "reply": answer}


def main():
    for line in sys.stdin:
        request_id = ""
        try:
            data = json.loads(line)
            request_id = str(data.get("id", ""))
            result = _answer(data)
        except Exception as exc:
            _log("REQUEST_ERROR", reason=type(exc).__name__)
            result = {"id": request_id, "ok": False, "error": type(exc).__name__}
        sys.stdout.write(json.dumps(result, ensure_ascii=False) + "\n")
        sys.stdout.flush()


atexit.register(_stop_primary)
if __name__ == "__main__":
    main()
