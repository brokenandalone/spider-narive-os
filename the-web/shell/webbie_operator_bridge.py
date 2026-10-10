"""A stop-safe, permission-gated local voice bridge to Webbie computer control.

No command can create or extend a task grant. The bridge exists only while
the owner-approved GUI task is active. The only voice-directed action here is
OPEN for the exact XDG application the owner selected; other GUI tasks require
further interactive safety work.
"""
from __future__ import annotations
import os
from pathlib import Path
import re
import socket
import stat

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtNetwork import QLocalServer

NAME = 'webbie-operator.sock'
MAX_REQUEST = 260
MAX_REPLY = 400
APP_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.+-]{0,199}\.desktop$')


def private_socket_directory(runtime=None):
    folder = Path(runtime) if runtime else Path(
        os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}')) / 'spider-os'
    if folder.is_symlink():
        raise PermissionError('Refusing a symlinked control runtime')
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    information = folder.stat()
    if information.st_uid != os.getuid() or not stat.S_ISDIR(information.st_mode):
        raise PermissionError('Desktop control runtime is not owned by this user')
    os.chmod(folder, 0o700)
    return folder


class OperatorBridge(QObject):
    openRequested = pyqtSignal(str)

    def __init__(self, *, grant, runtime=None, parent=None):
        super().__init__(parent)
        self.grant = grant
        self.path = private_socket_directory(runtime) / NAME
        self.server = QLocalServer(self)
        self.server.setSocketOptions(QLocalServer.UserAccessOption)
        self.server.newConnection.connect(self.accept)
        self.pending = None

    def activate(self):
        if self.server.isListening():
            return
        if self.path.is_symlink():
            raise PermissionError('Unsafe operator control socket')
        if self.path.exists():
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
                probe.settimeout(.2)
                try:
                    probe.connect(str(self.path))
                    raise RuntimeError('Another Webbie control panel is active')
                except (ConnectionRefusedError, FileNotFoundError):
                    pass
            QLocalServer.removeServer(str(self.path))
        if not self.server.listen(str(self.path)):
            raise RuntimeError('Unable to start the local operator bridge')
        os.chmod(self.path, 0o600)

    def accept(self):
        while self.server.hasPendingConnections():
            peer = self.server.nextPendingConnection()
            peer.readyRead.connect(lambda p=peer: self.read(p))
            if peer.bytesAvailable():
                self.read(peer)

    def read(self, peer):
        if self.pending is not None:
            self.finish(peer, 'Another desktop request is in progress')
            return
        if peer.bytesAvailable() > MAX_REQUEST:
            self.finish(peer, 'Rejected: oversized request')
            return
        packet = bytes(peer.readAll()).decode('utf-8', 'replace').strip()
        data = self.grant.status()
        if not data['active']:
            self.finish(peer, 'Desktop task authorization is not active')
            return
        if not packet.startswith('OPEN:'):
            self.finish(peer, 'Unsupported desktop control action')
            return
        app_id = packet[5:]
        if not APP_ID.fullmatch(app_id) or app_id != data['selected_app_id']:
            self.finish(peer, 'The selected application is not authorized')
            return
        self.pending = peer
        self.openRequested.emit(app_id)

    def finish(self, peer, text):
        if peer is None:
            return
        if peer is self.pending:
            self.pending = None
        peer.write(str(text).encode('utf-8')[:MAX_REPLY])
        peer.flush()
        peer.disconnectFromServer()
        peer.deleteLater()

    def deactivate(self):
        if self.pending is not None:
            self.finish(self.pending, 'Desktop task was stopped')
        if self.server.isListening():
            self.server.close()
        if self.path.exists() and not self.path.is_symlink():
            QLocalServer.removeServer(str(self.path))


def request_open(desktop_id, *, runtime=None, timeout=3):
    """Agent requests a specific already-approved app; never auto-authorizes."""
    if not isinstance(desktop_id, str) or not APP_ID.fullmatch(desktop_id):
        raise ValueError('Invalid installed application ID')
    path = private_socket_directory(runtime) / NAME
    if not path.is_file() or path.is_symlink():
        return 'To open that program, first authorize it in Webbie Computer Control.'
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as peer:
            peer.settimeout(timeout)
            peer.connect(str(path))
            peer.sendall(('OPEN:' + desktop_id).encode('utf-8'))
            response = peer.recv(MAX_REPLY + 1)
        if len(response) > MAX_REPLY:
            return 'Unexpected desktop control response.'
        return response.decode('utf-8', 'replace') or 'The operator did not respond.'
    except (OSError, TimeoutError):
        return 'Webbie Computer Control is unavailable.'
