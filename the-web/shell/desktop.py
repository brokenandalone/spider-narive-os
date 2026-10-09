"""X11 desktop/dock integration and bounded window-manager commands."""
import ctypes
import ctypes.util
from dataclasses import dataclass
import os
import re
import shutil
import subprocess

@dataclass(frozen=True)
class Task:
    ident: str
    title: str


def list_tasks(excluded=()):
    command = shutil.which('wmctrl')
    if not command:
        return []
    try:
        result = subprocess.run([command, '-l'], capture_output=True, text=True, timeout=1)
    except (OSError, subprocess.TimeoutExpired):
        return []
    tasks = []
    for line in result.stdout.splitlines():
        parts = line.split(None, 3)
        if len(parts) == 4 and parts[0] not in excluded and parts[1] != '-1':
            tasks.append(Task(parts[0], parts[3]))
    return tasks


def wm_command(*arguments):
    executable = shutil.which('wmctrl')
    if executable:
        subprocess.Popen([executable, *arguments], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def close_window(ident):
    """Request WM_DELETE_WINDOW; retain the application's unsaved-work prompt."""
    if not isinstance(ident, str) or not re.fullmatch(r'0x[0-9a-fA-F]+', ident) or int(ident, 16) == 0:
        raise ValueError('Invalid X11 window ID')
    wm_command('-i', '-c', ident)


def x11_properties(window, kind, screen=None):
    """EWMH desktop/dock types; dock reserves only its bottom-screen interval."""
    if not os.environ.get('DISPLAY') or os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
        return False
    library = ctypes.util.find_library('X11')
    if not library:
        return False
    x = ctypes.CDLL(library)
    x.XOpenDisplay.argtypes = [ctypes.c_char_p]; x.XOpenDisplay.restype = ctypes.c_void_p
    x.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]; x.XInternAtom.restype = ctypes.c_ulong
    x.XChangeProperty.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_int]
    x.XFlush.argtypes = [ctypes.c_void_p]; x.XCloseDisplay.argtypes = [ctypes.c_void_p]
    display = x.XOpenDisplay(None)
    if not display:
        return False
    try:
        def atom(name):
            return x.XInternAtom(display, name.encode('ascii'), 0)
        def prop(name, values, datatype='CARDINAL'):
            data = (ctypes.c_ulong * len(values))(*values)
            x.XChangeProperty(display, int(window.winId()), atom(name), atom(datatype), 32, 0, data, len(values))
        prop('_NET_WM_WINDOW_TYPE', [atom('_NET_WM_WINDOW_TYPE_' + kind)], 'ATOM')
        prop('_NET_WM_DESKTOP', [0xffffffff])
        prop('_NET_WM_STATE', [atom('_NET_WM_STATE_SKIP_TASKBAR'), atom('_NET_WM_STATE_SKIP_PAGER')], 'ATOM')
        if kind == 'DOCK' and screen:
            # Root coordinates are required for multi-monitor setups.
            bottom = max(s.geometry().bottom() + 1 for s in window.screen().virtualSiblings())
            geometry = screen.geometry()
            height = max(0, bottom - window.geometry().top())
            prop('_NET_WM_STRUT_PARTIAL', [0, 0, 0, height, 0, 0, 0, 0, 0, 0, max(0, geometry.left()), max(0, geometry.right())])
            prop('_NET_WM_STRUT', [0, 0, 0, height])
        x.XFlush(display)
    finally:
        x.XCloseDisplay(display)
    return True
