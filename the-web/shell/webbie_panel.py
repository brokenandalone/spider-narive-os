"""Webbie portrait and asynchronous chat; preserve the installed voice agent."""
from html import escape
import configparser
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path
import socket
import stat

from PyQt5.QtCore import Qt, QRectF, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QPainterPath, QPixmap
from PyQt5.QtWidgets import (QGraphicsDropShadowEffect, QHBoxLayout, QLabel,
                            QLineEdit, QPushButton, QTextEdit, QVBoxLayout, QWidget)


def runtime_directory():
    return Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}')) / 'spider-os'


def observed_state(runtime, pending=False):
    """File signals are observations, not microphone or speaker authentication."""
    try:
        if (runtime / 'webbie-speaking').is_file():
            return 'speaking', 'Speaking'
        if pending:
            return 'thinking', 'Waiting for Webbie’s reply'
        if stat.S_ISSOCK((runtime / 'webbie.sock').stat().st_mode):
            return 'available', 'Webbie service detected'
    except OSError:
        pass
    return 'offline', 'Webbie connection unavailable'


def request_reply(text, socket_path):
    """Existing agent protocol: UTF-8 request and reply terminated by peer close."""
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(130)
        client.connect(str(socket_path))
        client.sendall(text.encode('utf-8'))
        parts = []; size = 0
        while True:
            data = client.recv(65536)
            if not data:
                break
            size += len(data)
            if size > 262144:
                raise ValueError('Webbie reply exceeded the display limit')
            parts.append(data)
        reply = b''.join(parts).decode('utf-8', errors='replace')
        if not reply.strip():
            raise ValueError('Webbie returned an empty reply')
        return reply


class ReplyWorker(QThread):
    reply = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, text, socket_path, parent):
        super().__init__(parent); self.text = text; self.socket_path = socket_path

    def run(self):
        try:
            self.reply.emit(request_reply(self.text, self.socket_path))
        except (OSError, ValueError) as error:
            self.failed.emit('Unable to reach Webbie: ' + str(error))


class SpeakingPortrait(QLabel):
    """Blend only the mouth region; the head and background remain stationary."""
    def __init__(self, root):
        super().__init__(); self.setFixedSize(192, 192); self.setAlignment(Qt.AlignCenter)
        directory = Path(root) / 'branding/webbie'
        self.closed = QPixmap(str(directory / 'webbie-face-v1.png'))
        self.opened = QPixmap(str(directory / 'webbie-face-speaking-v1.png'))
        self.mouth_opacity = 0
        if self.closed.isNull():
            self.setText('WEBBIE')

    def paintEvent(self, event):
        if self.closed.isNull():
            super().paintEvent(event); return
        painter = QPainter(self); painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.drawPixmap(self.rect(), self.closed)
        if self.mouth_opacity and not self.opened.isNull():
            clip = QPainterPath(); clip.addEllipse(QRectF(self.width() * .445, self.height() * .467, self.width() * .151, self.height() * .096))
            painter.setClipPath(clip); painter.setOpacity(self.mouth_opacity)
            painter.drawPixmap(self.rect(), self.opened)


def cloud_state_label():
    """Local-only check; no network, sign-in dialog or waiting for Microsoft."""
    setting = Path.home() / '.config/spider-os/onedrive.json'
    remote = Path.home() / '.config/rclone/rclone.conf'
    try:
        if json.loads(setting.read_text()).get('enabled') is not True:
            return 'OneDrive: not connected. Webbie stays local.'
        if not shutil.which('rclone'):
            return 'OneDrive: paused (rclone unavailable).'
        parser = configparser.RawConfigParser(interpolation=None)
        if remote.is_symlink(): return 'OneDrive: configuration requires review.'
        parser.read(remote)
        if parser.get('webbie_onedrive', 'type', fallback='') == 'onedrive':
            return 'OneDrive: configured. Background sync will verify cloud access.'
    except (OSError, ValueError, TypeError, configparser.Error):
        pass
    return 'OneDrive: not connected. Webbie stays local.'


class WebbiePanel(QWidget):
    def __init__(self, root):
        super().__init__()
        self.setObjectName('webbiePanel')
        self.setStyleSheet('''
            QWidget#webbiePanel { background:#120d18; color:#f5eff8; border-radius:10px; }
            QLabel { color:#f5eff8; background:transparent; }
            QTextEdit, QLineEdit { background:#17111f; color:#f5eff8; border:1px solid #5b21b6; border-radius:8px; padding:8px; }
            QPushButton { background:#6d28d9; color:white; border:1px solid #8b5cf6; border-radius:8px; padding:8px 16px; }
            QPushButton:disabled { background:#342343; color:#b5a5c0; }
        ''')
        self.root = Path(root)
        self.runtime = runtime_directory(); self.worker = None; self.pending = False; self.phase = 0; self.mouth_frame = 0
        layout = QVBoxLayout(self)
        header = QHBoxLayout(); layout.addLayout(header)
        self.face = SpeakingPortrait(root)
        self.face.setAccessibleName('Webbie: ethereal violet woman portrait')
        self.glow = QGraphicsDropShadowEffect(self.face); self.glow.setOffset(0, 0)
        self.glow.setColor(QColor('#a78bfa')); self.face.setGraphicsEffect(self.glow)
        header.addWidget(self.face)
        details = QVBoxLayout(); header.addLayout(details, 1)
        title = QLabel('WEBBIE'); title.setStyleSheet('font-size:28px; font-weight:bold; color:#c4b5fd'); details.addWidget(title)
        details.addWidget(QLabel('Resident AI · Spider OS'))
        self.state_label = QLabel(); self.state_label.setWordWrap(True); details.addWidget(self.state_label)
        note = QLabel('Wake: Hey Webbie · Hey Web')
        note.setToolTip('Lip movement follows the speaking signal. Word-level synchronization and listening detection are not yet available.')
        note.setWordWrap(True); details.addWidget(note)
        # These are explicit user actions. Neither OneDrive nor the overlay is
        # a dependency of the resident voice agent or its normal replies.
        extras = QHBoxLayout(); layout.addLayout(extras)
        sleep_btn = QPushButton('Sleep face tonight')
        sleep_btn.setToolTip('Hide the screen portrait until 8 AM. Webbie continues running.')
        sleep_btn.clicked.connect(lambda: self.face_mode('sleep-tonight'))
        extras.addWidget(sleep_btn)
        wake_btn = QPushButton('Wake face')
        wake_btn.clicked.connect(lambda: self.face_mode('wake'))
        extras.addWidget(wake_btn)
        self.cloud_label = QLabel(cloud_state_label())
        self.cloud_label.setWordWrap(True); layout.addWidget(self.cloud_label)
        cloud_actions = QHBoxLayout(); layout.addLayout(cloud_actions)
        connect_btn = QPushButton('Connect OneDrive')
        connect_btn.clicked.connect(self.connect_onedrive); cloud_actions.addWidget(connect_btn)
        folder_btn = QPushButton('OneDrive folder')
        folder_btn.clicked.connect(self.open_onedrive_folder); cloud_actions.addWidget(folder_btn)
        pause_btn = QPushButton('Pause OneDrive')
        pause_btn.clicked.connect(self.pause_onedrive); cloud_actions.addWidget(pause_btn)
        self.cloud_timer = QTimer(self); self.cloud_timer.timeout.connect(
            lambda: self.cloud_label.setText(cloud_state_label()))
        self.cloud_timer.start(10000)
        self.chat = QTextEdit(); self.chat.setReadOnly(True); layout.addWidget(self.chat, 1)
        self.chat.setPlainText('Ask Webbie below.')
        row = QHBoxLayout(); layout.addLayout(row)
        self.entry = QLineEdit(); self.entry.setPlaceholderText('Ask Webbie or tell her what to open…')
        self.entry.returnPressed.connect(self.send); row.addWidget(self.entry, 1)
        self.send_button = QPushButton('Send'); self.send_button.setMinimumHeight(44)
        self.send_button.clicked.connect(self.send); row.addWidget(self.send_button)
        self.timer = QTimer(self); self.timer.timeout.connect(self.refresh_state); self.timer.start(120)
        self.refresh_state()

    def refresh_state(self):
        state, label = observed_state(self.runtime, self.pending)
        self.state_label.setText(label); self.face.setAccessibleDescription(label)
        self.phase += 0.2
        self.glow.setBlurRadius(22 + 10 * math.sin(self.phase) if state in {'thinking', 'speaking'} else 10)
        if state == 'speaking':
            cadence = (0, .45, 1, .65, 0, .35, .8, .2)
            self.face.mouth_opacity = cadence[self.mouth_frame % len(cadence)]; self.mouth_frame += 1
        else:
            self.face.mouth_opacity = 0; self.mouth_frame = 0
        self.face.update()

    def face_mode(self, mode):
        script = self.root / 'the-web/overlay/webbie_face.py'
        if not script.is_file():
            self.append_message('Status', 'The Webbie overlay has not been installed yet.')
            return
        try:
            subprocess.Popen([sys.executable, str(script), mode],
                             stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL,
                             start_new_session=True)
            self.append_message('Status',
                'Webbie face will wake at 8 AM.' if mode == 'sleep-tonight' else 'Webbie face waking.')
        except OSError as error:
            self.append_message('Status', 'Could not change face display: ' + str(error))

    def connect_onedrive(self):
        script = self.root / 'system/onedrive.py'
        if not script.is_file():
            self.append_message('Status', 'The OneDrive integration is not installed yet.')
            return
        console = shutil.which('konsole')
        if not console:
            self.append_message('Status', 'Konsole is needed for Microsoft sign-in.')
            return
        try:
            subprocess.Popen([console, '--hold', '-e', sys.executable, str(script), 'connect'],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
            self.append_message('Status', 'OneDrive sign-in is open in Konsole. Webbie stays available.')
        except OSError as error:
            self.append_message('Status', 'Unable to open OneDrive sign-in: ' + str(error))

    def open_onedrive_folder(self):
        folder = Path.home() / 'Documents/Spider OS/Webbie/OneDrive'
        if not folder.is_dir():
            self.append_message('Status', 'Connect OneDrive first. Your Webbie cloud folder is not yet set up.')
            return
        try:
            subprocess.Popen(['xdg-open', str(folder)], stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError as error:
            self.append_message('Status', 'Unable to open folder: ' + str(error))

    def pause_onedrive(self):
        script = self.root / 'system/onedrive.py'
        if not script.is_file():
            return
        try:
            subprocess.Popen([sys.executable, str(script), 'pause'], stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.cloud_label.setText('OneDrive: pausing. Webbie continues locally.')
        except OSError:
            self.append_message('Status', 'Could not pause OneDrive. Check the connection settings.')

    def append_message(self, who, text):
        self.chat.append('<b>' + escape(who) + ':</b> ' + escape(text).replace('\n', '<br>'))

    def send(self):
        text = self.entry.text().strip()
        if not text or self.pending:
            return
        if len(text.encode('utf-8')) > 32768:
            self.append_message('Status', 'Message is too long. Send a shorter message.'); return
        self.append_message('You', text); self.entry.clear(); self.pending = True
        self.send_button.setEnabled(False); self.entry.setEnabled(False); self.refresh_state()
        self.worker = ReplyWorker(text, self.runtime / 'webbie.sock', self)
        self.worker.reply.connect(lambda reply: self.append_message('Webbie', reply))
        self.worker.failed.connect(lambda message: self.append_message('Status', message))
        self.worker.finished.connect(self.request_finished); self.worker.start()

    def request_finished(self):
        self.pending = False; self.send_button.setEnabled(True); self.entry.setEnabled(True)
        self.entry.setFocus(); self.refresh_state()

    def closeEvent(self, event):
        # The workspace/tab owner uses the same worker guard before deletion.
        if self.worker and self.worker.isRunning():
            event.ignore()
        else:
            event.accept()
