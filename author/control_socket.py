"""Owner-local Author command socket.

AuthorWindow owns the receiver. Other Spider OS components may enqueue a
read-only review or narration intent only while that window is open.
The socket is NOT a speaker verifier; spoken callers must pass their own
verified speaker gate before invoking send_author_command.
"""
import json
import os
import socket
import stat
import struct
import threading
from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal

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
    """Send explicit local intent; fail closed for unverified voice."""
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


class AuthorCommandServer(QThread):
    intentReady = pyqtSignal(object)
    stateChanged = pyqtSignal(str)

    def __init__(self, parent=None, socket_path=None):
        super().__init__(parent)
        self.path = author_socket_path() if socket_path is None else Path(socket_path)
        self._stop = threading.Event()
        self._server = None
        self._owns_socket = False

    def stop(self):
        self._stop.set()
        if self.isRunning():
            self.wait(1400)

    def run(self):
        try:
            self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            owner = self.path.parent.stat()
            if owner.st_uid != os.getuid() or self.path.parent.is_symlink():
                raise PermissionError("Unsafe Author runtime directory owner.")
            if self.path.exists() or self.path.is_socket():
                existing = self.path.lstat()
                if not stat.S_ISSOCK(existing.st_mode) or existing.st_uid != os.getuid():
                    raise PermissionError("Author socket path belongs to something else.")
                # Remove only a stale socket in our own user's runtime directory.
                with socket.socket(socket.AF_UNIX) as probe:
                    probe.settimeout(0.15)
                    try:
                        probe.connect(str(self.path))
                    except ConnectionRefusedError:
                        self.path.unlink()
                    else:
                        raise RuntimeError("Author command receiver is already running.")
            with socket.socket(socket.AF_UNIX) as listener:
                listener.bind(str(self.path))
                self._owns_socket = True
                os.chmod(self.path, 0o600)
                self._server = listener
                listener.listen(4)
                listener.settimeout(0.2)
                self.stateChanged.emit("Author commands available to authorized local session.")
                while not self._stop.is_set():
                    try:
                        conn, _ = listener.accept()
                    except socket.timeout:
                        continue
                    with conn:
                        conn.settimeout(0.5)
                        try:
                            credentials = conn.getsockopt(
                                socket.SOL_SOCKET, socket.SO_PEERCRED,
                                struct.calcsize("3i"))
                            _, peer_uid, _ = struct.unpack("3i", credentials)
                            if peer_uid != os.getuid():
                                conn.sendall(b"Author command rejected: different user.")
                                continue
                            payload = bytearray()
                            while len(payload) <= 2048:
                                part = conn.recv(2049 - len(payload))
                                if not part:
                                    break
                                payload.extend(part)
                            if len(payload) > 2048:
                                raise ValueError("Command exceeds maximum size.")
                            parsed = json.loads(payload.decode("utf-8"))
                            if parsed.get("version") != 1:
                                raise ValueError("Unsupported command protocol.")
                            intent = parsed.get("intent")
                            if not isinstance(intent, dict) or set(intent) - {
                                "action", "scope", "depth"}:
                                raise ValueError("Unsupported command.")
                            # Validate command shape, not arbitrary instructions.
                            action = intent.get("action")
                            if action not in {"review", "read", "pause_reading",
                                             "resume_reading", "stop_reading",
                                             "cancel_review"}:
                                raise ValueError("Unsupported action.")
                            if action in ("review", "read") and intent.get("scope") not in (
                                    "chapter", "book"):
                                raise ValueError("Missing review or narration scope.")
                            if action == "review" and intent.get("depth") not in (
                                    "quick", "deep"):
                                raise ValueError("Missing review depth.")
                            self.intentReady.emit(intent)
                            conn.sendall(b"Author request queued.")
                        except (OSError, ValueError, TypeError, KeyError) as error:
                            try:
                                conn.sendall(("Author command rejected: " + str(error)).encode()[:500])
                            except OSError:
                                pass
        except (OSError, RuntimeError, PermissionError) as error:
            self.stateChanged.emit("Author command receiver unavailable: " + str(error))
        finally:
            self._server = None
            try:
                if self._owns_socket and self.path.is_socket() and self.path.lstat().st_uid == os.getuid():
                    self.path.unlink()
            except OSError:
                pass
