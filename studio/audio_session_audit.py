"""Read-only, bounded WAV inventory for Spider Audio Studio."""
from __future__ import annotations
from pathlib import Path
import json
import os
import wave

MAX_FILES = 2000
MAX_DEPTH = 5

def audit_recordings(folder, *, max_files=MAX_FILES):
    root = Path(folder).expanduser()
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Choose an existing, non-symlink recording folder")
    if type(max_files) is not int or not 1 <= max_files <= MAX_FILES:
        raise ValueError("Invalid file limit")
    rows = []
    skipped_links = 0
    truncated = False
    def onerror(_error):
        raise OSError("Cannot read the selected recording folder")
    for current, dirs, files in os.walk(root, topdown=True, followlinks=False, onerror=onerror):
        relative = Path(current).relative_to(root)
        depth = len(relative.parts)
        blocked = [d for d in dirs if (Path(current)/d).is_symlink()]
        skipped_links += len(blocked)
        dirs[:] = sorted(d for d in dirs if d not in blocked) if depth < MAX_DEPTH else []
        for filename in sorted(files):
            path = Path(current)/filename
            if path.suffix.lower() != ".wav":
                continue
            if path.is_symlink():
                skipped_links += 1
                continue
            if len(rows) == max_files:
                truncated = True
                break
            item = {"path": str(path.relative_to(root)), "status": "unreadable"}
            try:
                with wave.open(str(path), "rb") as reader:
                    rate = reader.getframerate()
                    channels = reader.getnchannels()
                    width = reader.getsampwidth()
                    frames = reader.getnframes()
                    pcm = reader.getcomptype() == "NONE"
                size = path.stat().st_size
                if not path.is_file():
                    raise ValueError("Not a regular file")
                item.update(rate=rate, channels=channels, bit_depth=width*8,
                            frames=frames, duration_seconds=round(frames/rate, 3) if rate else None,
                            bytes=size)
                item["status"] = ("ready" if pcm and rate in (44100, 48000)
                    and channels in (1, 2) and width in (2, 3)
                    and frames > 0 and size >= frames*channels*width+44
                    else "incompatible")
            except (OSError, EOFError, ValueError, wave.Error) as exc:
                item["reason"] = type(exc).__name__
            rows.append(item)
        if truncated:
            break
    counts = {state:sum(r["status"]==state for r in rows)
              for state in ("ready","incompatible","unreadable")}
    return {"root":str(root.resolve()), "files":rows, "counts":counts,
            "skipped_symlinks":skipped_links, "truncated":truncated,
            "max_depth":MAX_DEPTH, "read_only":True}

def report_json(report):
    return json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True)
