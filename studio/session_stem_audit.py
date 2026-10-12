"""Conservative audio-content audit of labeled Spider Studio session stems.

Identical WAV bytes or sampled PCM windows across track roles are important
warning signals, but no audio algorithm here can prove genuine isolation.
Includes only verified local session files. NEVER runs separation models.
"""
import hashlib
import json
import threading
import wave

try:
    from .multitrack import SessionError
    from .session_project import inspect_session
except ImportError:
    from multitrack import SessionError
    from session_project import inspect_session

WINDOW_SECONDS = 1.5
MAX_WARNINGS = 150


def _pcm_window_signature(track, stop):
    """Include audio properties, first and last windows, excluding WAV headers."""
    digest = hashlib.sha256()
    try:
        with wave.open(str(track["path"]), "rb") as audio:
            channels, width = audio.getnchannels(), audio.getsampwidth()
            rate, frames = audio.getframerate(), audio.getnframes()
            digest.update(json.dumps([rate, channels, width]).encode())
            count = max(1, min(frames, round(rate * WINDOW_SECONDS)))
            windows = [(0, count)]
            if frames > count:
                pos = max(count, frames - count)
                if pos < frames:
                    windows.append((pos, frames-pos))
            for start, amount in windows:
                if stop.is_set():
                    raise SessionError("Independent-stem check cancelled.")
                audio.setpos(start)
                remaining = amount
                while remaining:
                    if stop.is_set():
                        raise SessionError("Independent-stem check cancelled.")
                    n = min(32768, remaining)
                    raw = audio.readframes(n)
                    if len(raw) != n * channels * width:
                        raise SessionError("Track changed while checking sampled PCM.")
                    digest.update(raw)
                    remaining -= n
            digest.update(str(frames).encode())
    except (OSError, EOFError, wave.Error) as error:
        raise SessionError("Cannot inspect a saved track's PCM content.") from error
    return digest.hexdigest()


def assess_stem_independence(folder, *, stop=None):
    """Return 'not proven' even if no duplicate was detected."""
    stop = stop if stop is not None else threading.Event()
    session = inspect_session(folder, stop=stop)
    tracks = session["tracks"]
    hashes, windows = {}, {}
    notices, collisions = [], []
    for track in tracks:
        if stop.is_set():
            raise SessionError("Independent-stem check cancelled.")
        role, filename = track["role"], track["filename"]
        if role == "reference_mix":
            notices.append(f"{filename}: full-song reference, not an independent instrument.")
        if role == "click_guide":
            notices.append(f"{filename}: timing guide, never musical drums or a release stem.")
        byte_key = track["sha256"]
        if byte_key in hashes:
            collisions.append({
                "type": "identical_wav_bytes",
                "tracks": [hashes[byte_key], filename],
            })
        else:
            hashes[byte_key] = filename
        signature = _pcm_window_signature(track, stop)
        if signature in windows and windows[signature] != filename:
            collision = {
                "type": "matching_sampled_pcm_content",
                "tracks": [windows[signature], filename],
            }
            if collision not in collisions:
                collisions.append(collision)
        else:
            windows[signature] = filename
    duration_values = [
        (t["filename"], t["duration_seconds"]) for t in tracks
        if t["role"] not in {"click_guide", "reference_mix"}
    ]
    if len(duration_values) >= 2:
        highest = max(value for _, value in duration_values)
        lowest = min(value for _, value in duration_values)
        if highest - lowest > 2:
            notices.append(
                "Some performance stems differ by more than two seconds. "
                "Review bar alignment and trailing silence before mixing.")
    if len({t["sample_rate"] for t in tracks}) > 1:
        notices.append(
            "Tracks use different sample rates; render resamples to 48 kHz.")
    if collisions:
        notices.append("Matching WAV content was found under separate track labels.")
    notices.append(
        "Audio-role labels are user claims. No automatic proof of isolated guitar, "
        "bass, drum or singing sources is provided.")
    return {
        "schema": 1, "project_title": session["title"],
        "track_count": len(tracks),
        "reference_tracks": sum(t["role"] == "reference_mix" for t in tracks),
        "recording_guides": sum(t["role"] == "click_guide" for t in tracks),
        "identical_or_sampled_pcm_collisions": collisions[:MAX_WARNINGS],
        "notices": notices[:MAX_WARNINGS],
        "all_stems_independently_verified": False,
        "needs_human_listening_review": True,
        "audited_originals_preserved": True,
        "audio_comparison_only_checks_sampled_pcm_windows": True,
    }
