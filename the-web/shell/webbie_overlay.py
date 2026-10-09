"""Persistent, click-through Webbie portrait for Spider OS desktop sessions.

Only the face floats above the desktop. Interaction stays in the explicitly
opened Webbie side panel. Never captures input or looks at protected content.
"""
import json
import os
from pathlib import Path
import re
import subprocess

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout
from webbie_panel import SpeakingPortrait, observed_state, runtime_directory


def fullscreen_active():
    """Inspect EWMH active-window state only; missing tools fail open."""
    if not os.environ.get('DISPLAY'):
        return False
    try:
        active = subprocess.run(
            ['xprop', '-root', '_NET_ACTIVE_WINDOW'],
            capture_output=True, text=True, timeout=1, check=False
        )
        if active.returncode:
            return False
        match = re.search(r'window id # (0x[0-9a-fA-F]+)', active.stdout)
        if not match or int(match.group(1), 16) == 0:
            return False
        state = subprocess.run(
            ['xprop', '-id', match.group(1), '_NET_WM_STATE'],
            capture_output=True, text=True, timeout=1, check=False
        )
        return state.returncode == 0 and '_NET_WM_STATE_FULLSCREEN' in state.stdout
    except (OSError, subprocess.TimeoutExpired):
        return False


class WebbieOverlay(QWidget):
    """Read-only speaking portrait with no mouse or keyboard input region."""

    def __init__(self, root):
        super().__init__(
            None,
            Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
            | Qt.WindowTransparentForInput
        )
        self.setObjectName('webbiePersistentPortrait')
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setFocusPolicy(Qt.NoFocus)
        self.setWindowTitle('Webbie (click-through portrait)')
        self.setWindowOpacity(0.65)
        self.setFixedSize(170, 170)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.portrait = SpeakingPortrait(root)
        self.portrait.setFixedSize(170, 170)
        layout.addWidget(self.portrait)
        self.runtime = runtime_directory()
        self.face_sleeping = False
        self.config = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'spider-os/webbie-face.json'
        self.load_state()
        self.mouth_frame = 0
        self.timer = QTimer(self)
        self.timer.setInterval(350)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()
        self.refresh()

    def load_state(self):
        try:
            if self.config.stat().st_size > 2048:
                return
            data = json.loads(self.config.read_text(encoding='utf-8'))
            self.face_sleeping = data.get('sleeping') is True
        except (OSError, ValueError, TypeError):
            return

    def sleep(self, asleep):
        self.face_sleeping = bool(asleep)
        try:
            self.config.parent.mkdir(parents=True, exist_ok=True)
            destination = self.config.with_suffix('.tmp')
            destination.write_text(json.dumps({'sleeping': self.face_sleeping}) + '\n', encoding='utf-8')
            destination.replace(self.config)
        except OSError:
            pass
        self.refresh()

    def place(self):
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geometry = screen.availableGeometry()
        self.move(geometry.left() + 10, geometry.bottom() - self.height() - 58)

    def refresh(self):
        if self.face_sleeping or fullscreen_active():
            self.hide()
            return
        self.place()
        state, _ = observed_state(self.runtime)
        if state == 'speaking':
            self.portrait.mouth_opacity = (0, .4, .9, .5, 0, .8, .2)[self.mouth_frame % 7]
            self.mouth_frame += 1
        else:
            self.portrait.mouth_opacity = 0
            self.mouth_frame = 0
        self.portrait.update()
        if not self.isVisible():
            self.show()
        self.raise_()

    def stop(self):
        self.timer.stop()
        self.close()
