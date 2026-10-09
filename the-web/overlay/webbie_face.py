#!/usr/bin/env python3
"""The Web / Plasma X11 overlay: a translucent, click-through Webbie face.

Never replaces Webbie's agent, intercepts input, or changes KWin/Plasma settings.
"""
import ctypes
import ctypes.util
import fcntl
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from PyQt5.QtCore import Qt, QRectF, QTimer
from PyQt5.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPixmap
from PyQt5.QtWidgets import QApplication, QWidget

ROOT = Path('/usr/local/lib/spider-os')
if not (ROOT / 'branding/webbie/webbie-face-v1.png').is_file():
    ROOT = Path(__file__).resolve().parents[2]
CONFIG = Path.home() / '.config/spider-os/webbie-face.json'
SIZE = 196
BOTTOM_MARGIN = 72
SPEECH_FRAMES = (0, .3, .75, .95, .3, 0, .6, .15)


def state_from_data(payload, now=None):
    now = int(datetime.now().timestamp() if now is None else now)
    if not isinstance(payload, dict) or payload.get('asleep') is not True:
        return False
    until = payload.get('until')
    return until is None or (type(until) is int and now < until)


def asleep(path=CONFIG, now=None):
    try:
        return state_from_data(json.loads(Path(path).read_text(encoding='utf-8')), now)
    except (OSError, ValueError, TypeError):
        return False


def morning(now=None):
    now = now or datetime.now().astimezone()
    target = now.replace(hour=8, minute=0, second=0, microsecond=0)
    if target <= now: target += timedelta(days=1)
    return int(target.timestamp())


def set_sleep(mode, path=CONFIG, now=None):
    if mode not in ('sleep', 'sleep-tonight', 'wake'):
        raise ValueError('Unknown Webbie face mode')
    data = {'asleep': mode != 'wake',
            'until': morning(now) if mode == 'sleep-tonight' else None}
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, tmp = tempfile.mkstemp(prefix='.webbie-face-', dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(data, stream)
            stream.write('\n')
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
    return data


def active_window_id(data):
    match = re.search(r'window id # (0x[0-9a-fA-F]+)', data)
    return match.group(1) if match and int(match.group(1), 16) else None


def fullscreen_from_properties(data):
    return bool(re.search(r'\b_NET_WM_STATE_FULLSCREEN\b', data))


def fullscreen_active():
    """True for a fullscreen app; None if detection failed (fail closed)."""
    try:
        active = subprocess.run(['xprop', '-root', '_NET_ACTIVE_WINDOW'],
                                capture_output=True, text=True, timeout=.8)
        if active.returncode: return None
        ident = active_window_id(active.stdout)
        if ident is None: return False
        info = subprocess.run(['xprop', '-id', ident, '_NET_WM_STATE'],
                              capture_output=True, text=True, timeout=.8)
        return fullscreen_from_properties(info.stdout) if info.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def click_through_x11(window):
    """Set empty XFixes input shape: both opaque and clear pixels pass clicks."""
    if os.environ.get('QT_QPA_PLATFORM') == 'offscreen': return False
    xname = ctypes.util.find_library('X11')
    fname = ctypes.util.find_library('Xfixes')
    if not xname or not fname or not os.environ.get('DISPLAY'): return False
    display = None
    region = None
    try:
        xlib, fixes = ctypes.CDLL(xname), ctypes.CDLL(fname)
        xlib.XOpenDisplay.argtypes = [ctypes.c_char_p]
        xlib.XOpenDisplay.restype = ctypes.c_void_p
        xlib.XCloseDisplay.argtypes = [ctypes.c_void_p]
        xlib.XFlush.argtypes = [ctypes.c_void_p]
        fixes.XFixesCreateRegion.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
        fixes.XFixesCreateRegion.restype = ctypes.c_ulong
        fixes.XFixesSetWindowShapeRegion.argtypes = [ctypes.c_void_p, ctypes.c_ulong,
                                                     ctypes.c_int, ctypes.c_int,
                                                     ctypes.c_int, ctypes.c_ulong]
        fixes.XFixesDestroyRegion.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        display = xlib.XOpenDisplay(None)
        if not display: return False
        region = fixes.XFixesCreateRegion(display, None, 0)
        if not region: return False
        # ShapeInput is 2. An empty input region cannot receive mouse events.
        fixes.XFixesSetWindowShapeRegion(display, int(window.winId()), 2, 0, 0, region)
        xlib.XFlush(display)
        return True
    except (OSError, ValueError):
        return False
    finally:
        if region and display:
            fixes.XFixesDestroyRegion(display, region)
        if display: xlib.XCloseDisplay(display)


class WebbieOverlay(QWidget):
    def __init__(self, root=ROOT, sleep_path=CONFIG, full_screen_check=fullscreen_active):
        flags = Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus
        flags |= Qt.WindowTransparentForInput
        super().__init__(None, flags)
        self.setObjectName('webbieFaceOverlay')
        self.setWindowTitle('Webbie · Click-through portrait')
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setFixedSize(SIZE, SIZE)
        self.closed = QPixmap(str(Path(root) / 'branding/webbie/webbie-face-v1.png'))
        self.speaking = QPixmap(str(Path(root) / 'branding/webbie/webbie-face-speaking-v1.png'))
        self.sleep_path = Path(sleep_path)
        self.full_screen_check = full_screen_check
        self.runtime = Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}')) / 'spider-os'
        self.phase = 0
        self.sleeping = False
        self.allowed = False
        self.move_corner()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1400)  # Fullscreen polling is separate from mouth frames.
        self.mouth_timer = QTimer(self)
        self.mouth_timer.timeout.connect(self.tick_mouth)
        self.mouth_timer.start(135)

    def tick_mouth(self):
        if self.allowed:
            self.phase += 1
            self.update()

    def move_corner(self):
        screen = QApplication.primaryScreen()
        if not screen: return
        box = screen.availableGeometry()
        self.move(box.left() + 12, box.bottom() - SIZE - BOTTOM_MARGIN + 1)

    def refresh(self):
        self.move_corner()
        # Sleep keeps her face visible; fullscreen hides it. Voice only
        # accepts an explicit wake phrase, and background work continues.
        self.sleeping = asleep(self.sleep_path)
        visible = self.full_screen_check() is False
        if not visible:
            self.allowed = False
            self.hide()
            return
        if not self.allowed:
            self.show()
            # Fail closed: never leave a window capturing clicks over desktop.
            if not click_through_x11(self):
                self.hide()
                self.allowed = False
                return
            self.allowed = True
        self.update()

    def paintEvent(self, event):
        if self.closed.isNull(): return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        # The circular portrait fades into the existing desktop; alpha stays
        # below 1 even over the head, so buttons remain visible underneath.
        painter.setOpacity(.53)
        circle = QPainterPath()
        circle.addEllipse(QRectF(7, 7, SIZE - 14, SIZE - 14))
        painter.setClipPath(circle)
        painter.drawPixmap(self.rect(), self.closed)
        if not self.sleeping and (self.runtime / 'webbie-speaking').is_file() and not self.speaking.isNull():
            # Blend mouth only; do not flash a second full portrait.
            mouth = QPainterPath()
            mouth.addEllipse(QRectF(SIZE * .445, SIZE * .467, SIZE * .151, SIZE * .096))
            painter.setClipPath(mouth)
            painter.setOpacity(.53 * SPEECH_FRAMES[self.phase % len(SPEECH_FRAMES)])
            painter.drawPixmap(self.rect(), self.speaking)
        if self.sleeping:
            # Keep her face in view, with clearly closed eyes and subdued glow.
            painter.setClipping(False)
            painter.setOpacity(.93)
            painter.fillRect(self.rect(), QColor(22, 12, 48, 76))
            pen = QPen(QColor(91, 55, 132, 228), 4)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            for left in (.31, .56):
                eyelid = QPainterPath()
                eyelid.moveTo(SIZE * left, SIZE * .425)
                eyelid.cubicTo(SIZE * (left + .035), SIZE * .468,
                               SIZE * (left + .105), SIZE * .468,
                               SIZE * (left + .15), SIZE * .425)
                painter.drawPath(eyelid)
            painter.setPen(QColor(230, 210, 255, 235))
            painter.setFont(QFont('Sans Serif', 18, QFont.Bold))
            painter.drawText(self.rect().adjusted(112, 0, -4, -132),
                             Qt.AlignCenter, 'Zzz')


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv:
        if len(argv) != 1 or argv[0] not in ('sleep', 'sleep-tonight', 'wake', 'status'):
            raise SystemExit('Usage: webbie-face [sleep|sleep-tonight|wake|status]')
        if argv[0] == 'status':
            print('asleep' if asleep() else 'awake')
        else:
            set_sleep(argv[0])
            print('Webbie face: ' + ('awake' if argv[0] == 'wake' else 'asleep'))
        return 0
    if os.environ.get('XDG_SESSION_TYPE', '').lower() != 'x11':
        print('Webbie overlay: currently supported only in X11 sessions; nothing changed.', file=sys.stderr)
        return 0
    # XDG and KDE can both process autostarts; never create two floating faces.
    runtime = Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}')) / 'spider-os'
    runtime.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock = runtime / 'webbie-face-overlay.lock'
    handle = lock.open('a+', encoding='utf-8')
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print('Webbie overlay already running.')
        return 0
    app = QApplication(sys.argv)
    window = WebbieOverlay()
    if window.closed.isNull():
        print('Webbie overlay artwork missing; leaving the screen untouched.', file=sys.stderr)
        return 0
    window.refresh()
    return app.exec_()


if __name__ == '__main__':
    raise SystemExit(main())
