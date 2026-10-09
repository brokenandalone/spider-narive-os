"""Consent-bound local visual question bridge for the resident voice agent.

The Web owns this socket only while the owner has explicitly enabled camera
access. A spoken LOOK asks the live GUI to take one new frame, not to enable
camera access. The only reply is a bounded description, never image bytes.
"""
import os
from pathlib import Path
import socket
import stat

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtNetwork import QLocalServer

SOCKET_NAME = 'webbie-vision.sock'
MAX_REQUEST = 24
MAX_RESPONSE = 3200


def visual_question(command):
    """Conservatively recognize direct, intentional requests for room vision."""
    import re
    phrase = re.sub(r'[^a-z0-9\s\']', ' ', str(command).lower())
    phrase = re.sub(r'\s+', ' ', phrase).strip()
    phrases = (
        'what do you see', 'what can you see', 'what are you seeing',
        'tell me what you see', 'look around', 'look at the room',
        'describe the room', 'describe what you see', 'can you see me',
        'who do you see', 'what is in front of you', 'whats in front of you'
    )
    return any(phrase.startswith(p) for p in phrases)


def _safe_runtime(runtime=None):
    candidate = Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}'))
    home = candidate if candidate.is_dir() else Path.home() / '.cache' / 'spider-os' / 'private-run'
    folder = Path(runtime) if runtime is not None else home / 'spider-os'
    if folder.is_symlink():
        raise ValueError('Unsafe runtime directory.')
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    info = folder.stat()
    if info.st_uid != os.getuid() or not stat.S_ISDIR(info.st_mode):
        raise ValueError('Vision runtime directory is not owned by this user.')
    # Protect the socket even when an older Spider OS runtime used wide perms.
    os.chmod(folder, 0o700)
    return folder


class VisionBridge(QObject):
    lookRequested = pyqtSignal()

    def __init__(self, runtime=None, parent=None):
        super().__init__(parent)
        self.path = _safe_runtime(runtime) / SOCKET_NAME
        self.server = QLocalServer(self)
        self.server.setSocketOptions(QLocalServer.UserAccessOption)
        self.server.newConnection.connect(self.accept_connection)
        self.pending = None
        self.enabled = False

    def activate(self):
        if self.enabled:
            return True
        if self.path.is_symlink():
            raise ValueError('Unsafe visual assistant socket.')
        # A stale socket from a prior crashed desktop may be cleaned up only
        # inside the current user's private runtime directory. Never preempt
        # a live listening server.
        if self.path.exists():
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
                probe.settimeout(.25)
                try:
                    probe.connect(str(self.path))
                    raise RuntimeError('Another Webbie vision listener is running.')
                except (ConnectionRefusedError, FileNotFoundError):
                    pass
            QLocalServer.removeServer(str(self.path))
        if not self.server.listen(str(self.path)):
            raise RuntimeError('Unable to open local visual question listener.')
        os.chmod(self.path, 0o600)
        self.enabled = True
        return True

    def accept_connection(self):
        while self.server.hasPendingConnections():
            incoming = self.server.nextPendingConnection()
            incoming.readyRead.connect(lambda s=incoming: self.read_request(s))
            if incoming.bytesAvailable():
                self.read_request(incoming)

    def read_request(self, incoming):
        if incoming is self.pending:
            return
        if incoming.bytesAvailable() > MAX_REQUEST:
            self._finish_socket(incoming, 'Camera request rejected.')
            return
        command = bytes(incoming.readAll()).strip()
        if command != b'LOOK' or not self.enabled:
            self._finish_socket(incoming, 'Camera not enabled in The Web.')
        elif self.pending is not None:
            self._finish_socket(incoming, 'Webbie is already looking. Try again in a moment.')
        else:
            self.pending = incoming
            incoming.disconnected.connect(self._clear_if_disconnected)
            self.lookRequested.emit()

    def _clear_if_disconnected(self):
        if self.sender() is self.pending:
            self.pending = None

    def _finish_socket(self, peer, reply):
        # Bound the reply by characters first, then trim to valid UTF-8.
        data = str(reply).encode('utf-8')[:MAX_RESPONSE].decode('utf-8', errors='ignore').encode('utf-8')
        if peer is not None:
            peer.write(data)
            peer.flush()
            peer.disconnectFromServer()
            peer.deleteLater()
        if peer is self.pending:
            self.pending = None

    def reply(self, message):
        if self.pending is not None:
            self._finish_socket(self.pending, message)

    def deactivate(self):
        if self.pending is not None:
            self.reply('Camera turned off before Webbie could look.')
        self.enabled = False
        if self.server.isListening():
            self.server.close()
        if self.path.exists() and not self.path.is_symlink():
            QLocalServer.removeServer(str(self.path))


def ask_vision(question, runtime=None, timeout=65):
    """Synchronous resident agent route; socket exists ONLY with camera ON."""
    if not visual_question(question):
        return None
    path = _safe_runtime(runtime) / SOCKET_NAME
    if not path.exists() or path.is_symlink():
        return 'My camera is off. Turn it on in The Web, then ask me again.'
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(timeout)
        try:
            client.connect(str(path))
            client.sendall(b'LOOK\n')
            chunks = []
            total = 0
            while True:
                part = client.recv(4096)
                if not part:
                    break
                total += len(part)
                if total > MAX_RESPONSE:
                    return 'My camera response was too long. Please try again.'
                chunks.append(part)
            message = b''.join(chunks).decode('utf-8', errors='replace').strip()
            return message or 'I could not get a picture. Please try again.'
        except (OSError, TimeoutError):
            return 'My camera could not finish looking. Please try again.'
