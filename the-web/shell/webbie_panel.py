"""Webbie portrait and asynchronous chat; preserve the installed voice agent."""
from html import escape
import math
import os
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
        self.runtime = runtime_directory(); self.worker = None; self.pending = False; self.phase = 0; self.mouth_frame = 0
        self.workspace_label = 'The Web'; self.workspace_mode = 'Normal'; self.workspace_summary = ''
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
        self.context = QLabel('Workspace: The Web  |  Normal')
        self.context.setWordWrap(True)
        self.context.setAccessibleName('Active Webbie workspace and mode')
        layout.addWidget(self.context)
        self.disclosure = QLabel('Only the workspace name and selected title are shared with local Webbie when you send a message. Files and chapter text are not sent automatically.')
        self.disclosure.setWordWrap(True)
        layout.addWidget(self.disclosure)
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

    def append_message(self, who, text):
        self.chat.append('<b>' + escape(who) + ':</b> ' + escape(text).replace('\n', '<br>'))

    def set_workspace_context(self, label, mode='Normal', summary=''):
        self.workspace_label = str(label)[:90]
        self.workspace_mode = str(mode)[:70]
        self.workspace_summary = str(summary)[:600]
        description = f'Workspace: {self.workspace_label}  |  {self.workspace_mode}'
        if self.workspace_summary:
            description += '\nSelected: ' + self.workspace_summary
        self.context.setText(description)

    def prepare_request(self, text):
        fields = [f'Workspace: {self.workspace_label}', f'Mode: {self.workspace_mode}']
        if self.workspace_summary:
            fields.append('Selected title: ' + self.workspace_summary)
        return '[Spider OS workspace context; advisory only]\n' + '\n'.join(fields) + '\n[User request]\n' + text

    def send(self):
        text = self.entry.text().strip()
        if not text or self.pending:
            return
        request = self.prepare_request(text)
        if len(request.encode('utf-8')) > 32768:
            self.append_message('Status', 'Message is too long. Send a shorter message.'); return
        self.append_message('You', text); self.entry.clear(); self.pending = True
        self.send_button.setEnabled(False); self.entry.setEnabled(False); self.refresh_state()
        self.worker = ReplyWorker(request, self.runtime / 'webbie.sock', self)
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
