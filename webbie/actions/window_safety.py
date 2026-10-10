"""Window-confined controls for Webbie desktop operations.

An owner must explicitly select a window. Every key/click refocuses and checks
that window before operating, avoiding accidental actions in unrelated apps.
This is ordinary X11 automation, not an OS-level sandbox or protection from
other same-user processes. A window can move/resize; operations recheck bounds.
"""
import re
from desktop_control import DesktopOperator, WINDOW_ID, KEYS

GEOMETRY = re.compile(r'^(X|Y|WIDTH|HEIGHT)=(-?\d+)$')


def parse_geometry(text):
    values = {}
    for line in text.splitlines():
        match = GEOMETRY.fullmatch(line.strip())
        if match:
            values[match[1]] = int(match[2])
    if not {'WIDTH', 'HEIGHT'}.issubset(values):
        raise RuntimeError('Target window dimensions unavailable')
    if not 1 <= values['WIDTH'] <= 20000 or not 1 <= values['HEIGHT'] <= 20000:
        raise RuntimeError('Target window dimensions invalid')
    return values['WIDTH'], values['HEIGHT']


class ConfinedDesktopOperator(DesktopOperator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.target_window = None

    def bind_window(self, window_id):
        if not isinstance(window_id, str) or not WINDOW_ID.fullmatch(window_id):
            raise ValueError('Invalid target window identifier')
        self.require('window.target', f'Select window_id={window_id}')
        self.existing_window(window_id)
        self.target_window = window_id
        return {'selected_window': window_id}

    def _focus_bound(self):
        if not self.target_window:
            raise PermissionError('Choose the exact program window to control')
        target = self.existing_window(self.target_window)
        self.run(['wmctrl', '-ia', target])
        foreground = self.run(['xdotool', 'getactivewindow']).stdout.strip()
        if not foreground.isdigit() or int(foreground) != int(target, 16):
            raise RuntimeError('Selected window is not active; action not sent')
        return target

    def focus(self, window_id):
        if self.target_window is None or window_id.lower() != self.target_window.lower():
            raise PermissionError('Only the user-selected window may be focused')
        self.require('window.focus', f'Focus window_id={window_id}')
        target = self._focus_bound()
        return {'focused': target}

    def click(self, x, y, button=1):
        if (type(x) is not int or type(y) is not int or
                x < 0 or y < 0 or type(button) is not int or button not in (1, 2, 3)):
            raise ValueError('Invalid relative pointer coordinates')
        if not self.target_window:
            raise PermissionError('Select a window before moving the pointer')
        self.require('pointer.click', f'Click in window_id={self.target_window}')
        target = self._focus_bound()
        width, height = parse_geometry(
            self.run(['xdotool', 'getwindowgeometry', '--shell', target]).stdout)
        if x >= width or y >= height:
            raise ValueError('Click would leave the authorized window bounds')
        self.run(['xdotool', 'mousemove', '--sync', '--window', target,
                  str(x), str(y)])
        # Recheck foreground after pointer positioning.
        foreground = self.run(['xdotool', 'getactivewindow']).stdout.strip()
        if not foreground.isdigit() or int(foreground) != int(target, 16):
            raise RuntimeError('Target lost focus before click; no click sent')
        self.run(['xdotool', 'click', str(button)])
        return {'clicked_relative_to_window': [x, y, button]}

    def press(self, key):
        if key not in KEYS:
            raise ValueError('Only reviewed keyboard shortcuts are accepted')
        if not self.target_window:
            raise PermissionError('Select a window before sending keystrokes')
        action = ('keyboard.change.confirm' if key in
                  {'Delete', 'ctrl+x', 'ctrl+s'} else 'keyboard.key')
        self.require(action, f'Press {key} in window_id={self.target_window}')
        self._focus_bound()
        self.run(['xdotool', 'key', '--clearmodifiers', key])
        return {'pressed': key}

    def type_text(self, text):
        if not isinstance(text, str) or not 0 < len(text) <= 2048:
            raise ValueError('Text must be 1-2048 characters')
        if any(ord(ch) < 32 or ord(ch) == 127 for ch in text):
            raise ValueError('Only single-line non-control text accepted')
        if not self.target_window:
            raise PermissionError('Select a window before typing')
        self.require('keyboard.type', f'Type in window_id={self.target_window}')
        self._focus_bound()
        self.run(['xdotool', 'type', '--clearmodifiers', '--delay', '12', '--', text])
        return {'typed_characters': len(text)}

    def close_window(self, window_id):
        if not self.target_window or window_id.lower() != self.target_window.lower():
            raise PermissionError('Only the authorized target window may be closed')
        self.require('window.close.confirm', f'Close window_id={window_id}; save work first')
        self._focus_bound()
        self.run(['wmctrl', '-ic', window_id])
        self.target_window = None
        return {'close_requested': window_id}

    def stop(self):
        self.target_window = None
        return super().stop()

    def begin_new_task(self):
        result = super().begin_new_task()
        self.target_window = None
        return result
