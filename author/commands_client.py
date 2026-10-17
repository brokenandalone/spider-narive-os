"""Qt-free local Author Bay command sender.

Safe to import from Webbie's resident voice process. Caller identity and
speaker authorization are separate from recognizing a command.
"""
import json
import os
import socket
from pathlib import Path

try:
    from .commands import parse_author_command
except ImportError:
    from commands import parse_author_command


def author_socket_path(runtime=None):
    if runtime is None:
        runtime = Path(os.environ.get(
            "XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")) / "spider-os"
    return Path(runtime) / "author-control.sock"


def send_author_command(command, *, source="typed", speaker_verified=False,
                        socket_path=None, timeout=0.6):
    if source not in ("typed", "voice") or (
        source == "voice" and not speaker_verified
    ):
        return "Author voice command blocked: trusted speaker not verified."
    intent = parse_author_command(command)
    if intent is None:
        return None
    path = author_socket_path() if socket_path is None else Path(socket_path)
    request = json.dumps({"version": 1, "intent": intent}).encode("utf-8")
    try:
        with socket.socket(socket.AF_UNIX) as client:
            client.settimeout(timeout)
            client.connect(str(path))
            client.sendall(request)
            client.shutdown(socket.SHUT_WR)
            reply = client.recv(512)
        return reply.decode("utf-8", errors="replace") or "Author did not acknowledge the request."
    except (OSError, TimeoutError) as error:
        return "Author Bay is not ready to accept commands: " + str(error)
