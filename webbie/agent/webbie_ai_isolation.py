#!/usr/bin/env python3
"""Isolate Webbie's local brain in a bounded, restartable worker process.

Reconciled from the owner-tested Webbie AI V2 source. Runs as the existing
Webbie service user. No additional service, root capability, or network target.
"""
import atexit
import json
import os
import select
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

# Share one owner-selected local model preference with the existing brain.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "brain"))
from resident_model_choice import read_choice

HERE = Path(__file__).resolve().parent
WORKER = HERE / "webbie_ai_worker.py"
_LOCK = threading.Lock()
_PROCESS = None
_BUFFER = b""
_LOG_HANDLE = None


def _log_file():
    global _LOG_HANDLE
    if _LOG_HANDLE is None:
        state = Path.home() / ".local" / "state" / "spider-os"
        state.mkdir(parents=True, exist_ok=True, mode=0o700)
        path = state / "webbie-ai-worker.log"
        if path.is_symlink():
            raise PermissionError("AI log must not be a symlink")
        if path.exists() and path.stat().st_size > 2 * 1024 * 1024:
            path.replace(state / "webbie-ai-worker.previous.log")
        fd = os.open(str(path), os.O_CREAT | os.O_APPEND | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o600)
        _LOG_HANDLE = os.fdopen(fd, "ab", buffering=0)
    return _LOG_HANDLE


def _stop():
    global _PROCESS, _BUFFER
    proc = _PROCESS
    _PROCESS = None
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
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
    for stream in (proc.stdin, proc.stdout):
        try:
            if stream:
                stream.close()
        except OSError:
            pass


def _ensure_worker():
    global _PROCESS, _BUFFER
    if _PROCESS is not None and _PROCESS.poll() is None:
        return _PROCESS
    _stop()
    if not WORKER.is_file():
        raise FileNotFoundError("Webbie AI worker file missing")
    _PROCESS = subprocess.Popen(
        [sys.executable, "-u", str(WORKER)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=_log_file(),
        bufsize=0,
        close_fds=True,
    )
    _BUFFER = b""
    return _PROCESS


def respond(message, context_name="Spider", advisory_context=None):
    """Compatible with brain.respond(message, context_name, advisory_context)."""
    global _BUFFER
    try:
        # A full-size owner-selected local model can take longer to respond
        # on the installed CPU. The original 8B default remains quick.
        default_wait = 90 if read_choice() else 28
        max_wait = float(os.environ.get(
            "WEBBIE_AI_WORKER_TIMEOUT", str(default_wait)))
    except (ValueError, OverflowError):
        max_wait = 90 if read_choice() else 28
    max_wait = min(120, max(4, max_wait))
    if not _LOCK.acquire(timeout=2):
        return "I am finishing another AI request. My desktop controls are still available."
    try:
        proc = _ensure_worker()
        ident = uuid.uuid4().hex
        payload = {
            "id": ident,
            "message": str(message or ""),
            "context_name": str(context_name or "Spider"),
            "advisory_context": str(advisory_context or "")[:3500],
        }
        try:
            proc.stdin.write((json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8"))
            proc.stdin.flush()
        except (OSError, BrokenPipeError) as exc:
            _stop()
            return f"My AI worker disconnected ({type(exc).__name__}). My system controls remain available."
        deadline = time.monotonic() + max_wait
        while True:
            if b"\n" in _BUFFER:
                line, _BUFFER = _BUFFER.split(b"\n", 1)
                try:
                    result = json.loads(line)
                except (ValueError, UnicodeError):
                    _stop()
                    return "My AI worker returned invalid data. It has been restarted."
                if result.get("id") != ident:
                    _stop()
                    return "My AI worker lost request synchronization. It has been restarted."
                if not result.get("ok"):
                    _stop()
                    return "My AI worker encountered an error. My system controls remain available."
                return str(result.get("reply") or "").strip() or "I received your question, but the model returned an empty answer."
            seconds = deadline - time.monotonic()
            if seconds <= 0:
                _stop()
                return "My AI worker exceeded its response deadline. I can still respond to system commands."
            if proc.poll() is not None:
                _stop()
                return "My AI worker stopped unexpectedly. It will restart on the next question."
            ready, _, _ = select.select([proc.stdout], [], [], min(seconds, 1.0))
            if not ready:
                continue
            chunk = os.read(proc.stdout.fileno(), 65536)
            if not chunk:
                _stop()
                return "My AI worker connection closed. It will restart on the next question."
            _BUFFER += chunk
            if len(_BUFFER) > 1024 * 1024:
                _stop()
                return "My AI worker sent an oversized response. It has been restarted."
    except Exception as exc:
        _stop()
        return f"My AI worker is unavailable ({type(exc).__name__}). My system controls remain available."
    finally:
        _LOCK.release()


atexit.register(_stop)
