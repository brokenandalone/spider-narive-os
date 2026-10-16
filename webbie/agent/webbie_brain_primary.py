#!/usr/bin/env python3
"""Persistent full-brain child for owner-verified Webbie AI V2.

Logs Ollama request shape, never transcripts or model answers.
Preserves the actual brain.py conversation/memory behavior while healthy.
"""
import contextlib
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT / "brain", ROOT / "agent", ROOT / "voice", ROOT):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

_original_urlopen = urllib.request.urlopen


def _traced_urlopen(req, *args, **kwargs):
    url = getattr(req, "full_url", req if isinstance(req, str) else "")
    if isinstance(url, str) and url.startswith("http://127.0.0.1:11434/api/chat"):
        try:
            payload = json.loads(req.data)
            messages = payload.get("messages", [])
            print(
                "PRIMARY_OLLAMA_REQUEST model=%s messages=%d prompt_chars=%d request_bytes=%d think=%r max_tokens=%r" % (
                    str(payload.get("model", "?"))[:80],
                    len(messages),
                    sum(len(str(m.get("content", ""))) for m in messages if isinstance(m, dict)),
                    len(req.data),
                    payload.get("think"),
                    payload.get("options", {}).get("num_predict")
                    if isinstance(payload.get("options"), dict) else None,
                ),
                file=sys.stderr,
                flush=True,
            )
        except (TypeError, ValueError, AttributeError):
            print("PRIMARY_OLLAMA_REQUEST metadata_unavailable", file=sys.stderr, flush=True)
    return _original_urlopen(req, *args, **kwargs)


urllib.request.urlopen = _traced_urlopen


def main():
    with contextlib.redirect_stdout(sys.stderr):
        from brain import respond
    for line in sys.stdin:
        request_id = ""
        started = time.monotonic()
        try:
            data = json.loads(line)
            request_id = str(data.get("id", ""))
            with contextlib.redirect_stdout(sys.stderr):
                answer = respond(
                    str(data["message"]),
                    context_name=str(data.get("context_name", "Spider")),
                    advisory_context=str(data.get("advisory_context") or "")[:3500],
                )
            reply = {"id": request_id, "ok": True, "reply": str(answer or "")}
        except Exception as exc:
            print("PRIMARY_EXCEPTION type=%s" % type(exc).__name__, file=sys.stderr, flush=True)
            reply = {"id": request_id, "ok": False, "error": type(exc).__name__}
        print(
            "PRIMARY_COMPLETE seconds=%.2f ok=%s" % (time.monotonic() - started, reply["ok"]),
            file=sys.stderr,
            flush=True,
        )
        sys.stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
