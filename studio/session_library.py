"""Read-only, bounded saved-song discovery for the original Spider Studio.

An item in this list is a *candidate*, not a verified song. Opening a
candidate always invokes the existing SHA-256 session-audit worker.
No scanning arbitrary home directories and no symlink following.
"""
from __future__ import annotations
import json
from pathlib import Path
import stat
try:
    from .multitrack import DEFAULT_OUTPUT,MAX_TRACKS
except ImportError:
    from multitrack import DEFAULT_OUTPUT,MAX_TRACKS

MAX_SCAN=250
MAX_SHOW=75
MAX_MANIFEST=1024*1024

def recent_sessions(root=None):
    folder=Path(root if root is not None else DEFAULT_OUTPUT).expanduser()
    if folder.is_symlink() or not folder.is_dir():
        return []
    result=[]
    # Direct children only: cannot walk the rest of a musician's home.
    scanned=0
    for child in folder.iterdir():
        if scanned>=MAX_SCAN:
            break
        scanned+=1
        try:
            if child.is_symlink() or not child.is_dir():
                continue
            path=child/"session.json"
            if (path.is_symlink() or not path.is_file() or
                    not 0<path.stat().st_size<=MAX_MANIFEST):
                continue
            with path.open("r",encoding="utf-8") as file:
                info=json.load(file)
            if type(info) is not dict or info.get("schema")!=1:
                continue
            title=info.get("project_title")
            bpm=info.get("tempo_bpm")
            tracks=info.get("tracks")
            if (type(title) is not str or not 1<=len(title.strip())<=120 or
                    not isinstance(tracks,list) or not 1<=len(tracks)<=MAX_TRACKS or
                    (bpm is not None and (type(bpm) is not int or not 30<=bpm<=300))):
                continue
            disk=child.stat()
            if not stat.S_ISDIR(disk.st_mode):
                continue
            result.append({"path":str(child),"title":title.strip(),
                           "track_count":len(tracks),"bpm":bpm,
                           "modified_ns":disk.st_mtime_ns})
        except (OSError,UnicodeError,ValueError,TypeError):
            continue
    return sorted(result,key=lambda song:song["modified_ns"],reverse=True)[:MAX_SHOW]
