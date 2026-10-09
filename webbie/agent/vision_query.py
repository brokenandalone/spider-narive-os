"""Local visual-question client for Webbie's *existing* wake-word voice agent.

Pure standard library, so a missing Qt module never interrupts the webcam mic
or Whisper listener. Camera access remains owned by the opt-in desktop UI.
"""
import os
from pathlib import Path
import re
import socket

VISION_SOCKET = 'webbie-vision.sock'
MAX_REPLY = 3200


def visual_question(command):
    phrase = re.sub(r'[^a-z0-9\s\']', ' ', str(command).lower())
    phrase = re.sub(r'\s+', ' ', phrase).strip()
    starts = (
        'what do you see', 'what can you see', 'what are you seeing',
        'tell me what you see', 'look around', 'look at the room',
        'describe the room', 'describe what you see', 'can you see me',
        'who do you see', 'what is in front of you', 'whats in front of you'
    )
    return any(phrase.startswith(part) for part in starts)


def ask_vision(question, runtime=None, timeout=65):
    if not visual_question(question):
        return None
    base = Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}'))
    directory = Path(runtime) if runtime is not None else base / 'spider-os'
    path = directory / VISION_SOCKET
    # Opening the user-owned socket is all a voice request can do. No
    # microphone setting changes, camera selection, or auto-enrollment.
    if directory.is_symlink() or path.is_symlink() or not path.exists():
        return 'My camera is off. Turn it on in The Web, then ask me again.'
    try:
        if directory.stat().st_uid != os.getuid():
            return 'My visual connection is unavailable.'
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(timeout)
            client.connect(str(path))
            client.sendall(b'LOOK\n')
            chunks, size = [], 0
            while True:
                part = client.recv(4096)
                if not part:
                    break
                size += len(part)
                if size > MAX_REPLY:
                    return 'My camera returned too much text. Please try again.'
                chunks.append(part)
            answer = b''.join(chunks).decode('utf-8', errors='replace').strip()
            return answer or 'I could not get a camera description. Please try again.'
    except (OSError, TimeoutError):
        return 'My camera could not finish looking. Please try again.'
