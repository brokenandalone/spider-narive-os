#!/usr/bin/env python3
"""Build a deterministic, source-only Spider Audio Studio developer preview.

This is NOT a signed commercial installer or a dependency-frozen runtime.
Does not alter the host OS. Only tracks explicit source directories.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import re
import tarfile
import io

SOURCE_DIRS = ("studio", "system", "the-web/shell", "the-web/overlay",
               "branding/spider-apps")
EXTENSIONS = {".py", ".svg", ".json", ".qss", ".css", ".desktop", ".md"}
EXACT_FILES = {"studio/bin/studio", "distro/config/applications/studio.desktop", "LICENSE"}
PRIVATE = re.compile(r"(^|/)(\.env[^/]*|__pycache__|\.git|private|secrets?|credentials?|tokens?|\.ssh)(/|$)", re.I)
MAX_FILE = 2 * 1024 * 1024
MAX_TOTAL = 30 * 1024 * 1024

def source_files(root: Path):
    root = root.resolve(strict=True)
    selected = {}
    for directory in SOURCE_DIRS:
        base = root / directory
        if not base.is_dir() or base.is_symlink():
            raise ValueError(f"Required source directory missing or linked: {directory}")
        for candidate in base.rglob("*"):
            if candidate.is_symlink():
                raise ValueError(f"Linked source is forbidden: {candidate}")
            if not candidate.is_file():
                continue
            relative = candidate.relative_to(root).as_posix()
            if PRIVATE.search("/" + relative) or candidate.suffix.lower() not in EXTENSIONS:
                continue
            if candidate.stat().st_size > MAX_FILE:
                raise ValueError(f"Unexpectedly large source file: {relative}")
            selected[relative] = candidate
    for relative in EXACT_FILES:
        candidate = root / relative
        if candidate.is_symlink() or not candidate.is_file():
            raise ValueError(f"Required application file missing or linked: {relative}")
        selected[relative] = candidate
    return [(name, selected[name]) for name in sorted(selected)]

def preview_build(root: Path, destination: Path):
    files = source_files(root)
    output = destination.expanduser().absolute()
    if output.suffixes[-2:] != [".tar", ".gz"]:
        raise ValueError("Preview destination must end in .tar.gz")
    if output.exists() or output.is_symlink():
        raise FileExistsError("Preview archive must have a new filename")
    if not output.parent.is_dir():
        raise ValueError("Preview destination directory does not exist")
    total = sum(p.stat().st_size for _,p in files)
    if total > MAX_TOTAL:
        raise ValueError("Source bundle exceeds 30 MiB safety limit")
    # The launch script lives at the package root to avoid depending on
    # Spider OS's desktop command routing or installed /usr/local path.
    launcher = b'#!/usr/bin/env bash\nset -euo pipefail\nROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"\ncd "$ROOT"\nexec python3 "$ROOT/studio/main.py" "$@"\n'
    notice = (b"SPIDER AUDIO STUDIO - DEVELOPER PREVIEW ONLY\n"
              b"Linux source distribution. Requires system Python, PyQt5, and\n"
              b"other optional Python/audio dependencies. No bundled media or\n"
              b"SoundFonts. Not tested or certified for public commercial sale.\n"
              b"Do not install over an existing Spider OS tree.\n")
    import os
    import tempfile
    fd, tmp = tempfile.mkstemp(prefix=".spider-preview-", suffix=".tar.gz", dir=output.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            with tarfile.open(fileobj=stream, mode="w:gz") as archive:
                def add_bytes(name, data, executable=False):
                    entry=tarfile.TarInfo("spider-audio-studio-preview/" + name)
                    entry.size=len(data)
                    entry.mode=0o755 if executable else 0o644
                    entry.mtime=0
                    archive.addfile(entry,io.BytesIO(data))
                add_bytes("RUN_PREVIEW.sh",launcher,True)
                add_bytes("PREVIEW_NOTICE.txt",notice)
                for name,path in files:
                    add_bytes(name,path.read_bytes(),name=="studio/bin/studio")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(tmp, output, follow_symlinks=False)
    finally:
        os.unlink(tmp)
    return {"archive":str(output), "source_files":len(files), "bytes":output.stat().st_size}

if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    print(preview_build(args.source,args.output))
