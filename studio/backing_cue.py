"""Private virtual-band backing cues for Spider Studio overdub recording.

Renders the actual score or song arranger offline and hands a new, strict
16-bit stereo PCM WAV to the existing full-duplex recording console. No
microphone, output device, DAW application, service or radio queue is opened.
Cues are private, never written over earlier songs, and have a five-minute
maximum matching the real overdub engine.
"""
from __future__ import annotations

from copy import deepcopy
import os
from pathlib import Path
import secrets
import stat
import tempfile
import wave

try:
    from .audio_capture_engine import CaptureError
    from .soundfont_render import validate_soundfont
    from .studio_score_mix import render_score_mix, MixChannel
    from .song_arranger_engine import Song, song_duration, write_song_wav
except ImportError:
    from audio_capture_engine import CaptureError
    from soundfont_render import validate_soundfont
    from studio_score_mix import render_score_mix, MixChannel
    from song_arranger_engine import Song, song_duration, write_song_wav

DEFAULT_CUES = Path.home() / "Documents/Spider Studio/Music/Backing Cues"
MAX_CUE_SECONDS = 300
MAX_CUE_BYTES = MAX_CUE_SECONDS * 48000 * 2 * 2 + 4096

def _directory(output_root):
    root = Path(output_root).expanduser() if output_root is not None else DEFAULT_CUES
    if root.is_symlink() or (root.exists() and not root.is_dir()):
        raise CaptureError("Backing cue library must be a real private directory")
    if not root.exists():
        root.mkdir(parents=True, mode=0o700)
    if root.is_symlink() or not root.is_dir():
        raise CaptureError("Backing cue library is not a regular folder")
    if os.stat(root).st_mode & stat.S_IWOTH:
        raise CaptureError("Backing cue library cannot be writable by everyone")
    return root

def validate_recordable_cue(filename, *, expected_rate=None):
    """Same PCM constraints as the real duplex player, without device access."""
    path = Path(filename)
    if path.is_symlink() or not path.is_file() or path.suffix.lower() != ".wav":
        raise CaptureError("Backing cue must be a local regular WAV")
    if path.stat().st_size > MAX_CUE_BYTES:
        raise CaptureError("Backing cue is larger than the supported limit")
    try:
        with wave.open(str(path), "rb") as reader:
            rate = reader.getframerate()
            frames = reader.getnframes()
            if (reader.getcomptype() != "NONE" or reader.getnchannels() not in (1,2)
                    or reader.getsampwidth() != 2 or rate not in (44100,48000)
                    or not 1 <= frames <= rate * MAX_CUE_SECONDS):
                raise CaptureError("Overdub backing must be 16-bit mono/stereo WAV at 44.1/48 kHz, at most five minutes")
            if expected_rate is not None and rate != expected_rate:
                raise CaptureError("Rendered backing does not match the requested sample rate")
            required = frames * reader.getnchannels() * 2
            if path.stat().st_size < required + 44:
                raise CaptureError("Backing file contains truncated PCM")
            return {"rate":rate,"frames":frames,"seconds":frames/rate}
    except (wave.Error,EOFError,OSError,ZeroDivisionError) as error:
        raise CaptureError("Cannot inspect backing WAV PCM") from error

def _publish(root, source, *, title, rate):
    data = validate_recordable_cue(source, expected_rate=rate)
    # Per-cue random identifier protects even repeated same-title arrangements.
    # Publishing is create-new-only, so an older cue cannot be overwritten.
    import re
    stem = re.sub(r"[^A-Za-z0-9_-]+", "-", title).strip("-")[:45] or "Spider-Band"
    dest = root / ("Spider-Band-" + stem + "-" + secrets.token_hex(7) + ".wav")
    os.chmod(source, 0o600)
    os.link(source, dest, follow_symlinks=False)
    return dest, data

def render_score_backing(performance, default_bank, *, part_banks=None,
                         channels=None, rate=48000, output_root=None,
                         renderer=None):
    """Mix owner-selected SoundFont score parts to a recordable 16-bit cue.

    Renderer injection is for deterministic tests only. Owner SF2/SF3 banks
    must pass SoundFont header validation before a render begins.
    """
    p = deepcopy(performance).validated()
    if type(rate) is not int or rate not in (44100,48000):
        raise CaptureError("Backing rate must be 44.1 or 48 kHz")
    if p.duration_seconds > MAX_CUE_SECONDS:
        raise CaptureError("Score is longer than the five-minute overdub limit")
    selected = dict(part_banks or {})
    if any(type(i) is not int or not 0 <= i < len(p.parts) for i in selected):
        raise CaptureError("Backing uses an unknown instrument bank")
    bank = validate_soundfont(default_bank)
    banks = {i:validate_soundfont(path) for i,path in selected.items()}
    controls = list(channels) if channels is not None else [MixChannel() for _ in p.parts]
    if len(controls) != len(p.parts) or any(
        not isinstance(c,MixChannel) or not isinstance(c.validate(),MixChannel)
        for c in controls
    ):
        raise CaptureError("Backing part mixer is invalid")
    root = _directory(output_root)
    perform = renderer or render_score_mix
    with tempfile.TemporaryDirectory(prefix=".spider-band-render-",dir=str(root)) as temp:
        raw = Path(temp)/"score.wav"
        perform(p,bank,raw,part_banks=banks,channels=controls,
                rate=rate,bit_depth=16)
        return _publish(root,raw,title=p.title,rate=rate)

def render_song_backing(song, *, rate=44100, output_root=None, renderer=None):
    """Render existing Song Arranger patterns and mixer as a 16-bit cue."""
    p = Song.from_dict(song.as_dict())
    if not p.bars:
        raise CaptureError("Add song arrangement bars before recording along")
    if type(rate) is not int or rate not in (44100,48000):
        raise CaptureError("Backing rate must be 44.1 or 48 kHz")
    if song_duration(p) > MAX_CUE_SECONDS:
        raise CaptureError("Arrangement is longer than the five-minute overdub limit")
    root = _directory(output_root)
    perform = renderer or write_song_wav
    with tempfile.TemporaryDirectory(prefix=".spider-arranger-render-",dir=str(root)) as temp:
        raw = Path(temp)/"arrangement.wav"
        perform(p,raw,rate=rate)
        return _publish(root,raw,title=p.title,rate=rate)
