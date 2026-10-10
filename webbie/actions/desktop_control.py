"""Opt-in, local X11 desktop operations for Spider OS Webbie.

This is a backend, not a voice-command listener. It NEVER authorizes itself.
A trusted, visible owner UI must supply a permission callback and bind that
approval to an actual task and speaker/session before this can be used by Webbie.
No model text, transcription, webpage or on-screen content grants permission.
There is no shell execution, remote API, privileged action or automatic startup.
"""
from __future__ import annotations

import importlib
import os
from pathlib import Path
import re
import subprocess
import sys
import threading

ROOT = Path(__file__).resolve().parents[2]
SHELL_MODULE = ROOT / 'the-web' / 'shell'
WINDOW_ID = re.compile(r'^0x[0-9a-fA-F]{1,16}$')
KEYS = frozenset({
    'Escape', 'Tab', 'BackSpace', 'Delete', 'Up', 'Down', 'Left', 'Right',
    'Home', 'End', 'Page_Up', 'Page_Down', 'space', 'ctrl+a', 'ctrl+c',
    'ctrl+v', 'ctrl+x', 'ctrl+z', 'ctrl+shift+z', 'ctrl+s', 'alt+Tab',
})


def app_catalog():
    """Use The Web's existing XDG catalog; do not parse/execute Exec ourselves."""
    if str(SHELL_MODULE) not in sys.path:
        sys.path.insert(0, str(SHELL_MODULE))
    return importlib.import_module('app_catalog')


def select_app(query, entries):
    """Resolve a spoken program name without accidentally launching a lookalike."""
    if not isinstance(query, str) or not query.strip() or len(query) > 120:
        raise ValueError('Name an installed application to open')
    search = query.strip().casefold()
    exact = [app for app in entries if
             app.name.casefold() == search or
             app.desktop_id.casefold() == search or
             app.desktop_id.casefold().removesuffix('.desktop') == search]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        raise ValueError('Several installed apps use that name. Select an app ID.')
    partial = [app for app in entries if search in app.name.casefold()]
    if len(partial) == 1:
        return partial[0]
    if partial:
        raise ValueError('More than one application matches; select an exact name.')
    raise ValueError('Application not found in the installed desktop menu')


def parse_windows(output):
    """Parse wmctrl's window listing, retaining names for user-visible previews."""
    windows = []
    for line in output.splitlines():
        fields = line.split(maxsplit=4)
        if len(fields) != 5 or not WINDOW_ID.fullmatch(fields[0]):
            continue
        try:
            pid = int(fields[2])
        except ValueError:
            continue
        windows.append({
            'id': fields[0], 'pid': pid, 'host': fields[3],
            'title': fields[4][:300],
        })
    return windows


class DesktopOperator:
    """Restricted X11 control primitives, denied unless a trusted UI approves.

    permission(action, preview) is a trusted local GUI callback, NOT a function
    supplied by the language model. Mutating steps must show their target and
    purpose to the owner. Confirm risky actions separately in the UI.
    """

    def __init__(self, permission=None, *, runner=None, launcher=None,
                 discover=None, display=None):
        self.permission = permission
        self.runner = runner or subprocess.run
        self.launcher = launcher or subprocess.Popen
        self.discover = discover
        self.display = display if display is not None else os.environ.get('DISPLAY', '')
        self.cancelled = threading.Event()

    def require(self, action, preview):
        if not self.display or not self.display.startswith(':'):
            raise RuntimeError('Desktop automation requires an active local X11 session')
        # No permissive default, including for read-only screen/window metadata.
        if self.permission is None or self.permission(action, preview) is not True:
            raise PermissionError('Desktop control has not been authorized in the local UI')
        if self.cancelled.is_set() and action != 'task.begin':
            raise InterruptedError('Webbie desktop task stopped by user')

    def run(self, command):
        if self.cancelled.is_set():
            raise InterruptedError('Webbie desktop task stopped by user')
        # Argument vectors only. Never use shell=True or execute model strings.
        return self.runner(
            command, check=True, text=True, capture_output=True, timeout=8,
        )

    def applications(self):
        self.require('observe.apps', 'List installed applications')
        catalog = app_catalog()
        apps = catalog.discover_apps() if self.discover is None else self.discover()
        return [{'name': a.name, 'desktop_id': a.desktop_id, 'workspace': a.workspace}
                for a in apps]

    def open_app(self, query):
        self.require('app.open', f'Open the installed application named {query!r}')
        catalog = app_catalog()
        apps = catalog.discover_apps() if self.discover is None else self.discover()
        app = select_app(query, apps)
        command = catalog.launch_command(app)
        self.launcher(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                      stderr=subprocess.DEVNULL, start_new_session=True)
        # Process launch is not evidence of successful UI load.
        return {'desktop_id': app.desktop_id, 'name': app.name, 'launch_requested': True}

    def windows(self):
        self.require('observe.windows', 'Inspect open window titles')
        return parse_windows(self.run(['wmctrl', '-lp']).stdout)

    def existing_window(self, window_id):
        if not isinstance(window_id, str) or not WINDOW_ID.fullmatch(window_id):
            raise ValueError('Invalid desktop window ID')
        # Even a syntactically valid ID must exist in the current window list.
        if window_id.lower() not in {item['id'].lower() for item in self.windows()}:
            raise ValueError('That window is no longer open')
        return window_id

    def focus(self, window_id):
        self.require('window.focus', f'Focus window {window_id}')
        self.run(['wmctrl', '-ia', self.existing_window(window_id)])
        return {'focus_requested': window_id}

    def click(self, x, y, button=1):
        if (type(x) is not int or type(y) is not int or
                not 0 <= x <= 16384 or not 0 <= y <= 16384 or
                type(button) is not int or button not in (1, 2, 3)):
            raise ValueError('Invalid pointer coordinates or button')
        self.require('pointer.click', f'Click button {button} at ({x}, {y})')
        self.run(['xdotool', 'mousemove', '--sync', str(x), str(y)])
        self.run(['xdotool', 'click', str(button)])
        return {'clicked': [x, y, button]}

    def press(self, key):
        if key not in KEYS:
            raise ValueError('Unsupported keystroke; only reviewed shortcuts are allowed')
        self.require('keyboard.key', f'Press {key}')
        self.run(['xdotool', 'key', '--clearmodifiers', key])
        return {'pressed': key}

    def type_text(self, text):
        # One-line input only: automatic Return and multiline shell paste are
        # deliberately excluded. Do not log user text or expose it to a model.
        if not isinstance(text, str) or not 0 < len(text) <= 2048:
            raise ValueError('Text must have 1 to 2048 characters')
        if any(ord(ch) < 32 or ord(ch) == 127 for ch in text):
            raise ValueError('Control characters and newlines are not accepted')
        self.require('keyboard.type', f'Type {len(text)} characters in the active window')
        self.run(['xdotool', 'type', '--clearmodifiers', '--delay', '12', '--', text])
        return {'typed_characters': len(text)}

    def close_window(self, window_id):
        self.require('window.close.confirm', f'Close window {window_id}; unsaved work may be lost')
        self.run(['wmctrl', '-ic', self.existing_window(window_id)])
        return {'close_requested': window_id}

    def stop(self):
        """Always allow an immediate local cancel, even without permissions."""
        self.cancelled.set()
        return {'stopped': True}

    def begin_new_task(self):
        self.require('task.begin', 'Begin a new owner-approved desktop task')
        self.cancelled.clear()
        return {'ready': True}
