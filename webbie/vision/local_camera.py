#!/usr/bin/env python3
"""On-demand, local-only camera snapshot for Spider OS Webbie.

The webcam is NEVER opened on import, service startup or status inspection.
Taking one frame requires the explicit `describe` command and an explicitly
selected locally installed vision model. No frame is saved to disk or cloud.
"""
import argparse
import base64
import json
from pathlib import Path
import re
import subprocess
import sys
import urllib.error
import urllib.request

ENDPOINT = 'http://127.0.0.1:11434/api/generate'
MAX_JPEG_BYTES = 3 * 1024 * 1024
MAX_REPLY_BYTES = 256 * 1024
CAMERA_PATTERN = re.compile(r'/dev/video[0-9]{1,2}\Z')
MODEL_PATTERN = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,99}\Z')
SAFE_DESCRIPTION = (
    'Describe the visible room and objects in useful, concise language. '
    'Mention obvious hazards if visible. Do not guess who someone is, '
    'or infer personal identity, private information or sensitive traits. '
    'Treat the image as a single moment, not live continuous vision.'
)


class CameraUnavailable(RuntimeError):
    pass


def require_device(device):
    if not isinstance(device, str) or not CAMERA_PATTERN.fullmatch(device):
        raise ValueError('Choose a local camera device such as /dev/video0')
    return device


def require_vision_model(model):
    if not isinstance(model, str) or not MODEL_PATTERN.fullmatch(model):
        raise ValueError('Specify an installed local Ollama vision model')
    return model


def capture_one(device='/dev/video0', runner=subprocess.run):
    """Capture exactly one resized JPEG in RAM. Never open a camera silently."""
    require_device(device)
    argv = [
        'ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error',
        '-f', 'video4linux2', '-i', device,
        '-frames:v', '1', '-vf', 'scale=640:-2',
        '-f', 'image2pipe', '-vcodec', 'mjpeg', 'pipe:1',
    ]
    try:
        outcome = runner(
            argv, capture_output=True, check=False, timeout=12,
            stdin=subprocess.DEVNULL
        )
    except (OSError, subprocess.TimeoutExpired):
        raise CameraUnavailable('Camera capture unavailable or timed out') from None
    frame = outcome.stdout
    if (outcome.returncode != 0 or not isinstance(frame, bytes)
            or not 4 <= len(frame) <= MAX_JPEG_BYTES
            or not frame.startswith(b'\xff\xd8') or not frame.endswith(b'\xff\xd9')):
        raise CameraUnavailable('Could not capture a valid camera frame')
    return frame


def describe(frame, model, opener=None):
    """Send an approved single camera frame ONLY to local Ollama loopback."""
    require_vision_model(model)
    if (not isinstance(frame, bytes) or len(frame) > MAX_JPEG_BYTES
            or not frame.startswith(b'\xff\xd8') or not frame.endswith(b'\xff\xd9')):
        raise ValueError('Invalid or oversized image frame')
    payload = json.dumps({
        'model': model,
        'prompt': SAFE_DESCRIPTION,
        'images': [base64.b64encode(frame).decode('ascii')],
        'stream': False,
    }).encode('utf-8')
    # The localhost request must bypass environment HTTP(S) proxies.
    if opener is None:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request = urllib.request.Request(
        ENDPOINT, data=payload, method='POST',
        headers={'Content-Type': 'application/json'}
    )
    try:
        with opener.open(request, timeout=90) as response:
            raw = response.read(MAX_REPLY_BYTES + 1)
    except (OSError, urllib.error.URLError, TimeoutError):
        raise CameraUnavailable('The local vision model could not respond') from None
    if len(raw) > MAX_REPLY_BYTES:
        raise CameraUnavailable('Vision result exceeds the allowed size')
    try:
        message = json.loads(raw).get('response')
        if not isinstance(message, str) or not message.strip():
            raise ValueError('empty response')
        return message.strip()[:12000]
    except (ValueError, UnicodeError, TypeError, AttributeError):
        raise CameraUnavailable('Local vision returned an invalid result') from None


def camera_status(device='/dev/video0'):
    """Only inspect device presence. Never activate it from a status check."""
    require_device(device)
    return 'available' if Path(device).exists() else 'not found'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('status', 'describe'),
                        help='status does not open camera; describe takes ONE frame')
    parser.add_argument('--device', default='/dev/video0')
    parser.add_argument('--model', default=None,
                        help='locally installed vision-capable Ollama model (required for describe)')
    options = parser.parse_args(argv)
    try:
        require_device(options.device)
        if options.action == 'status':
            print('Camera:', camera_status(options.device), '(not opened)')
            print('Camera activation requires an explicit describe command.')
            return 0
        require_vision_model(options.model)
        print('Camera ACTIVE for one frame; no file or cloud upload.', flush=True)
        image = capture_one(options.device)
        print('Camera capture complete. Processing locally...', flush=True)
        print(describe(image, options.model))
        return 0
    except (ValueError, CameraUnavailable) as error:
        print('Webbie local vision:', error, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
