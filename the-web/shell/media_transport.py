"""Linux MPRIS transport. Explicit selected player; no shell or process killing."""
import re
import subprocess

PREFIX = 'org.mpris.MediaPlayer2.'
PLAYER = re.compile(r'org\.mpris\.MediaPlayer2\.[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*\Z')


def call(destination, path, method, *arguments):
    try:
        result = subprocess.run(['dbus-send', '--session', '--type=method_call', '--print-reply',
                                 '--reply-timeout=1500', '--dest=' + destination, path, method, *arguments],
                                capture_output=True, text=True, timeout=2)
    except (OSError, subprocess.TimeoutExpired):
        raise RuntimeError('Media control connection is unavailable') from None
    if result.returncode:
        raise RuntimeError('The player did not accept this command. It may have closed or may not support the control.')
    return result.stdout[:65536]


def discover_players():
    text = call('org.freedesktop.DBus', '/org/freedesktop/DBus', 'org.freedesktop.DBus.ListNames')
    return sorted({name for name in re.findall(r'string "([^"]+)"', text) if PLAYER.fullmatch(name)})


def player_state(name):
    if not PLAYER.fullmatch(name): raise ValueError('Invalid media player')
    text = call(name, '/org/mpris/MediaPlayer2', 'org.freedesktop.DBus.Properties.Get',
                'string:org.mpris.MediaPlayer2.Player', 'string:PlaybackStatus')
    match = re.search(r'string "(Playing|Paused|Stopped)"', text)
    return match.group(1) if match else 'Status unavailable'


def control(name, action):
    if not isinstance(name, str) or not PLAYER.fullmatch(name): raise ValueError('Select a media player')
    if action in {'PlayPause', 'Previous', 'Next', 'Stop'}:
        method, args = action, []
    elif action in {'Back10', 'Forward10'}:
        method, args = 'Seek', ['int64:' + str(-10000000 if action == 'Back10' else 10000000)]
    else:
        raise ValueError('Unsupported media control')
    call(name, '/org/mpris/MediaPlayer2', 'org.mpris.MediaPlayer2.Player.' + method, *args)
