"""Webbie quiet sleep: keep her services alive, ignore ordinary microphone input.

This is NOT microphone mute. The existing recognizer still hears short chunks
to detect the explicit wake command. No camera permission, job scheduler or
private model state is changed. Shares one owner-local flag with her face.
"""
import json
import os
from pathlib import Path
import tempfile

STATE_PATH = Path.home() / '.config/spider-os/webbie-face.json'

SLEEP_COMMANDS = frozenset({
    'hey webbie go to sleep', 'hey webbie goodnight', 'hey webbie good night',
    'webbie go to sleep', 'webbie goodnight', 'webbie good night',
    'goodnight webbie', 'good night webbie',
    'hey webby go to sleep', 'hey webby goodnight', 'hey webby good night',
    'webby go to sleep', 'webby goodnight', 'webby good night',
    'goodnight webby', 'good night webby',
    'hey web go to sleep', 'hey web goodnight',
})
WAKE_COMMANDS = frozenset({
    'hey webbie wake up', 'webbie wake up',
    'hey web wake up', 'hey webbie wake', 'webbie wake',
    'hey webby wake up', 'webby wake up',
    'hey webby wake', 'webby wake',
})


def normalize(text):
    import re
    return re.sub(r'\s+', ' ', re.sub(r"[^a-z0-9\s']", ' ', str(text).lower())).strip()


def spoken_mode(text, sleeping=False):
    """Return sleep or wake only on an entire recognized command.

    Requiring a deliberate complete phrase prevents random background
    transcription, quoted text, movies, or ordinary commands from toggling
    the assistant just because they happen to mention 'sleep'.
    """
    phrase = normalize(text)
    if sleeping:
        return 'wake' if phrase in WAKE_COMMANDS else None
    return 'sleep' if phrase in SLEEP_COMMANDS else None


def asleep(path=STATE_PATH):
    try:
        state = json.loads(Path(path).read_text(encoding='utf-8'))
        if state.get('asleep') is not True: return False
        until = state.get('until')
        if until is None: return True
        if type(until) is not int: return False
        import time
        return time.time() < until
    except (OSError, ValueError, TypeError, AttributeError):
        return False


def set_mode(mode, path=STATE_PATH):
    """Atomically change sleep mode; never restart or stop background services."""
    if mode not in ('sleep', 'wake'):
        raise ValueError('Webbie sleep mode must be sleep or wake')
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.webbie-night-', dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump({'asleep': mode == 'sleep', 'until': None}, stream)
            stream.write('\n')
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
