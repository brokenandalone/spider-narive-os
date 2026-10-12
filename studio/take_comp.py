"""Offline Take Comp Lab: comp sections of genuine, owner-selected PCM performances.

Edits create ONE role-specific audio track from real takes. Cropping a full-song
mix does NOT isolate a guitar or singer. Source material must already be an
independent recorded performance. No generative model, cloud, or DAW mutation.
"""
from pathlib import Path
import hashlib
import json
import os
import shutil
import stat
import tempfile
import threading
import wave

try:
    from .multitrack import ROLES, SessionError, _probe
except ImportError:
    from multitrack import ROLES, SessionError, _probe

DEFAULT_ROOT = Path.home() / "Documents/Spider Studio/Music/Take Comps"
MAX_EDITS = 96
MAX_DURATION_MS = 600_000
MAX_INPUT_BYTES = 3 * 1024 ** 3
PRESETS = (0, 5, 10, 25, 50)
NON_PERFORMANCE = {"reference_mix", "click_guide", "instrumental_bed"}


def _ms_to_frame(ms, rate):
    return (ms * rate + 500) // 1000


def _read_layout(edits, role, fade_ms):
    if role not in ROLES or role in NON_PERFORMANCE:
        raise SessionError("Choose one real recorded vocal or instrument role, not a mix/click reference.")
    if type(fade_ms) is not int or fade_ms not in PRESETS:
        raise SessionError("Use 0, 5, 10, 25 or 50 ms fades.")
    if not isinstance(edits, (list, tuple)) or not 1 <= len(edits) <= MAX_EDITS:
        raise SessionError("Use between 1 and 96 selected take regions.")
    items, all_inputs, first_format = [], {}, None
    for edit in edits:
        if not isinstance(edit, dict) or set(edit) != {"source", "in_ms", "out_ms", "at_ms"}:
            raise SessionError("A take needs source, in_ms, out_ms and at_ms.")
        start, end, at = edit["in_ms"], edit["out_ms"], edit["at_ms"]
        if (any(type(x) is not int for x in (start, end, at))
                or not 0 <= start < end <= MAX_DURATION_MS or not 0 <= at < MAX_DURATION_MS):
            raise SessionError("Each clip must have positive, bounded millisecond offsets.")
        source, previous, meta = _probe(edit["source"])
        if source not in all_inputs:
            all_inputs[source] = (previous, meta)
        if sum(x.st_size for x, _ in all_inputs.values()) > MAX_INPUT_BYTES:
            raise SessionError("Too much audio supplied to one comp (maximum 3 GiB).")
        fmt = (meta["sample_rate"], meta["channels"], meta["sample_width_bytes"])
        if first_format is None:
            first_format = fmt
        if first_format != fmt:
            raise SessionError("Comping requires consistent sample rate, channel count and PCM bit depth.")
        rate = fmt[0]
        first = _ms_to_frame(start, rate)
        last = _ms_to_frame(end, rate)
        arrival = _ms_to_frame(at, rate)
        if last <= first or last > meta["frames"]:
            raise SessionError("A region falls outside its recorded take.")
        if arrival + last - first > _ms_to_frame(MAX_DURATION_MS, rate):
            raise SessionError("The resulting comp would be longer than ten minutes.")
        items.append({
            "source": source, "in_ms": start, "out_ms": end, "at_ms": at,
            "first": first, "last": last, "position": arrival,
            "frames": last-first,
        })
    items.sort(key=lambda x: (x["position"], x["source"].as_posix(), x["first"]))
    cursor = 0
    for item in items:
        if item["position"] < cursor:
            raise SessionError("Overlapping take edits are not mixed automatically. Choose non-overlapping positions.")
        cursor = item["position"] + item["frames"]
    return items, all_inputs, first_format, cursor


def _checksum(path, old, stop):
    digest = hashlib.sha256()
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, "rb") as f:
        stat_before = os.fstat(f.fileno())
        if (not stat.S_ISREG(stat_before.st_mode) or stat_before.st_dev != old.st_dev
                or stat_before.st_ino != old.st_ino or stat_before.st_size != old.st_size
                or stat_before.st_mtime_ns != old.st_mtime_ns):
            raise SessionError("A source take changed before comping.")
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            if stop.is_set():
                raise SessionError("Take comp cancelled.")
            digest.update(chunk)
        stat_after = os.fstat(f.fileno())
        if stat_after.st_mtime_ns != old.st_mtime_ns or stat_after.st_size != old.st_size:
            raise SessionError("A take changed during checksum review.")
    return digest.hexdigest()


def _fade_frames(raw, *, width, channels, start, total, fade_frames):
    """Apply a linear fade to this PCM chunk at edit boundaries, not the overall song."""
    if not fade_frames:
        return raw
    frame_bytes = width * channels
    if len(raw) % frame_bytes:
        raise SessionError("A WAV frame ended unexpectedly.")
    buffer = bytearray(raw)
    sample_count = len(raw) // frame_bytes
    bits = width * 8
    smallest, largest = -(1 << (bits - 1)), (1 << (bits - 1)) - 1
    for local in range(sample_count):
        frame = start + local
        level = min(1.0, (frame + 1) / fade_frames,
                    (total - frame) / fade_frames)
        if level == 1:
            continue
        for channel in range(channels):
            offset = local * frame_bytes + channel * width
            original = int.from_bytes(
                buffer[offset:offset+width], "little", signed=width != 1)
            if width == 1:
                original -= 128
            adjusted = min(largest, max(smallest, round(original * level)))
            if width == 1:
                adjusted += 128
            buffer[offset:offset+width] = int(adjusted).to_bytes(
                width, "little", signed=width != 1)
    return bytes(buffer)


def render_take_comp(edits, *, role, fade_ms=10, output_root=None, stop=None):
    """Render one independent-role WAV using exact PCM frame selections.

    Edits are placed at absolute *musical project* timestamps in milliseconds,
    with digital silence preceding any delayed performance. Time zero stays
    consistent for a subsequent DAW/Spider multitrack export.
    """
    stop = stop if stop is not None else threading.Event()
    items, inputs, fmt, total_frames = _read_layout(edits, role, fade_ms)
    if stop.is_set():
        raise SessionError("Take comp cancelled.")
    fingerprints = {}
    for source, (state, _) in inputs.items():
        fingerprints[str(source)] = _checksum(source, state, stop)
    root = Path(output_root).expanduser() if output_root else DEFAULT_ROOT
    if root.is_symlink() or (root.exists() and not root.is_dir()):
        raise SessionError("Take comps must be saved inside a real folder, not a symlink.")
    if stop.is_set():
        raise SessionError("Take comp cancelled.")
    rate, channels, width = fmt
    duration_bytes = total_frames * channels * width
    if duration_bytes > 2 * 1024 ** 3 - 8192:
        raise SessionError("Take comp exceeds the standard PCM WAV size limit.")
    try:
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(root, 0o700)
        if shutil.disk_usage(root).free < duration_bytes + 2 * 1024 * 1024:
            raise SessionError("Not enough disk space for the new take comp.")
        folder = Path(tempfile.mkdtemp(prefix="take-", dir=root))
        os.chmod(folder, 0o700)
    except OSError as error:
        raise SessionError("Cannot create a private take comp folder.") from error
    target = folder / f"{role}.wav"
    try:
        os.chmod(folder, 0o700)
        receipt = []
        with target.open("xb") as handle:
            os.chmod(target, 0o600)
            with wave.open(handle, "wb") as result:
                result.setnchannels(channels)
                result.setsampwidth(width)
                result.setframerate(rate)
                cursor = 0
                silence = bytes([128]) * channels if width == 1 else bytes(channels * width)
                fade = _ms_to_frame(fade_ms, rate)
                for edit in items:
                    if stop.is_set():
                        raise SessionError("Take comp cancelled.")
                    remaining = edit["position"] - cursor
                    while remaining:
                        if stop.is_set():
                            raise SessionError("Take comp cancelled.")
                        count = min(32768, remaining)
                        result.writeframesraw(silence * count)
                        remaining -= count
                    source = edit["source"]
                    original_stat = inputs[source][0]
                    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                    descriptor = os.open(source, flags)
                    with os.fdopen(descriptor, "rb") as stream:
                        fresh = os.fstat(stream.fileno())
                        if (not stat.S_ISREG(fresh.st_mode)
                                or fresh.st_dev != original_stat.st_dev
                                or fresh.st_ino != original_stat.st_ino
                                or fresh.st_size != original_stat.st_size
                                or fresh.st_mtime_ns != original_stat.st_mtime_ns):
                            raise SessionError("An original recording changed during comp creation.")
                        with wave.open(stream, "rb") as wav:
                            if (wav.getframerate(), wav.getnchannels(), wav.getsampwidth()) != fmt:
                                raise SessionError("An original take's PCM format changed.")
                            wav.setpos(edit["first"])
                            local = 0
                            remaining = edit["frames"]
                            fade_count = min(fade, edit["frames"] // 2)
                            while remaining:
                                if stop.is_set():
                                    raise SessionError("Take comp cancelled.")
                                count = min(8192, remaining)
                                data = wav.readframes(count)
                                if len(data) != count * channels * width:
                                    raise SessionError("Source take ended unexpectedly.")
                                data = _fade_frames(
                                    data, width=width, channels=channels,
                                    start=local, total=edit["frames"], fade_frames=fade_count)
                                result.writeframesraw(data)
                                local += count
                                remaining -= count
                        after = os.fstat(stream.fileno())
                        if (after.st_size != original_stat.st_size
                                or after.st_mtime_ns != original_stat.st_mtime_ns):
                            raise SessionError("Source take changed during playback extraction.")
                    cursor = edit["position"] + edit["frames"]
                    receipt.append({
                        "source": str(source), "source_sha256": fingerprints[str(source)],
                        "in_ms": edit["in_ms"], "out_ms": edit["out_ms"],
                        "at_ms": edit["at_ms"], "source_first_frame": edit["first"],
                        "source_last_frame": edit["last"],
                        "project_start_frame": edit["position"],
                        "frames_written": edit["frames"],
                    })
        with wave.open(str(target), "rb") as checked:
            if (checked.getnframes() != total_frames or
                    (checked.getframerate(), checked.getnchannels(),
                     checked.getsampwidth()) != fmt):
                raise SessionError("Rendered WAV frame count or format is invalid.")
        digest = hashlib.sha256()
        with target.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        manifest = {
            "schema": 1, "role": role, "format": {"sample_rate": rate, "channels": channels,
                                                  "sample_width_bytes": width},
            "output": target.name, "output_sha256": digest.hexdigest(),
            "duration_seconds": round(total_frames / rate, 4), "fade_ms": fade_ms,
            "edits": receipt, "original_takes_untouched": True,
            "preexisting_isolation_owner_attested": False,
            "full_song_cropping_does_not_isolate_instruments": True,
            "audio_generated_by_model": False, "timeline_zero_aligned": True,
        }
        record = folder / "comp.json"
        with record.open("x", encoding="utf-8") as stream:
            os.chmod(record, 0o600)
            json.dump(manifest, stream, indent=2)
        return target
    except BaseException:
        shutil.rmtree(folder, ignore_errors=True)
        raise
