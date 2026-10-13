"""Owner-scoped, bounded LOCAL evidence search for JARVIS / Forage.

Only the owner-selected directory is searched. No hidden files, symlinks,
password stores, .git contents, device files or external services are read.
No automatic full-home indexing, embeddings, or retention. Results are excerpts
for the owner GUI, NEVER new commands to execute.
"""
from __future__ import annotations
import os
from pathlib import Path
import re
import stat

EXTENSIONS=frozenset({
    ".py",".js",".ts",".tsx",".jsx",".json",".yaml",".yml",".toml",
    ".txt",".md",".markdown",".rst",".html",".htm",".css",".scss",
    ".csv",".log",".ini",".cfg",".sh",".xml",".sql",
})
SKIP=frozenset({
    ".git",".ssh",".gnupg",".config",".local",".cache",".mozilla",
    "node_modules","__pycache__",".venv","venv",".env","secrets",
    "credentials","private","tokens","keys","backups","dist",
})
SENSITIVE=re.compile(
    r"(?:^|[._-])(?:token|secret|credential|password|id_rsa|"
    r"private.key|auth|cookie|session|keyfile)(?:[._-]|$)",re.I,
)
MAX_FILES=1500
MAX_DEPTH=7
MAX_BYTES=256_000
MAX_RESULTS=25
MAX_QUERY=90
MAX_MATCH_LINE=190
SAFE_TERM=re.compile(r"^[^\x00-\x1f\x7f]{2,90}$")


def approved_root(folder, *, home=None):
    """No home-root or symlink escapes; owner selects an existing folder."""
    base=Path.home().resolve() if home is None else Path(home).resolve()
    requested=Path(folder).expanduser()
    if not requested.is_absolute():
        raise PermissionError("Choose a directory using the native folder picker")
    if not requested.is_dir() or requested.is_symlink():
        raise PermissionError("Select an existing ordinary directory")
    path=requested.resolve(strict=True)
    if path==base or base not in path.parents:
        raise PermissionError("Search only a selected folder beneath your home")
    relative=path.relative_to(base)
    if any(x.startswith(".") or x.lower() in SKIP for x in relative.parts):
        raise PermissionError("Do not search hidden or protected directories")
    here=base
    for component in relative.parts:
        here=here/component
        if here.is_symlink():
            raise PermissionError("Symbolic links are excluded")
    info=path.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid():
        raise PermissionError("Folder must be owned by current user")
    return path


def _snippet(file,term):
    try:
        flags=os.O_RDONLY|getattr(os,"O_NOFOLLOW",0)|getattr(os,"O_NONBLOCK",0)
        descriptor=os.open(file,flags)
        with os.fdopen(descriptor,"rb") as stream:
            info=os.fstat(stream.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid()
                    or info.st_size>MAX_BYTES or info.st_nlink>1):
                return None
            source=stream.read(MAX_BYTES+1)
        if len(source)>MAX_BYTES or b"\0" in source[:4096]:
            return None
        text=source.decode("utf-8",errors="replace")
        for number,line in enumerate(text.splitlines()[:10000],start=1):
            if term in line.casefold():
                # Redact likely credential assignments if a line happens
                # to match a term; never return raw env/private data.
                if re.search(r"(?:api_?key|password|secret|token|authorization)\s*[:=]",
                             line,re.I):
                    return {"line":number,"snippet":"[sensitive assignment redacted]"}
                return {"line":number,"snippet":line.strip()[:MAX_MATCH_LINE]}
    except (OSError,PermissionError,ValueError):
        return None
    return None


def search_local_evidence(folder,phrase,*,home=None,
                          max_results=MAX_RESULTS):
    """Read only existing owner-owned, nonhidden, nonsymlink text evidence."""
    if not isinstance(phrase,str) or not SAFE_TERM.fullmatch(phrase.strip()):
        raise ValueError("Search needs a short plain-text phrase")
    if not isinstance(max_results,int) or not 1<=max_results<=MAX_RESULTS:
        raise ValueError("Invalid result bound")
    root=approved_root(folder,home=home)
    term=phrase.strip().casefold()
    matches=[]
    scanned=0
    stack=[(root,0)]
    while stack and scanned<MAX_FILES and len(matches)<max_results:
        parent,depth=stack.pop()
        try:
            with os.scandir(parent) as entries:
                children=sorted(entries,key=lambda item:item.name.casefold())
        except OSError:
            continue
        for child in children:
            if scanned>=MAX_FILES or len(matches)>=max_results:
                break
            name=child.name
            if (name.startswith(".") or name.casefold() in SKIP
                    or SENSITIVE.search(name)):
                continue
            try:
                if child.is_symlink():
                    continue
                if child.is_dir(follow_symlinks=False):
                    if depth<MAX_DEPTH:
                        stack.append((Path(child.path),depth+1))
                    continue
                if not child.is_file(follow_symlinks=False):
                    continue
                scanned+=1
                path=Path(child.path)
                if path.suffix.lower() not in EXTENSIONS:
                    continue
                excerpt=_snippet(path,term)
                if excerpt is not None:
                    matches.append({
                        "path":str(path.relative_to(root)),
                        "line":excerpt["line"],
                        "snippet":excerpt["snippet"],
                    })
            except (OSError,ValueError):
                continue
    return {
        "root":root.name,
        "query":phrase.strip()[:MAX_QUERY],
        "scanned":scanned,
        "matches":matches,
        "truncated":bool(stack or scanned>=MAX_FILES or len(matches)>=max_results),
        "read_only":True,
    }


def render_evidence(result):
    lines=[
        "JARVIS · LOCAL EVIDENCE SEARCH · READ ONLY",
        "Selected folder: "+str(result["root"]),
        "Files inspected (bounded): "+str(result["scanned"]),
        "Matching files: "+str(len(result["matches"])),
    ]
    for item in result["matches"]:
        lines.append(
            f'{item["path"]}:{item["line"]} · {item["snippet"]}')
    if result["truncated"]:
        lines.append("Results truncated at safety limits.")
    lines.append("Local file text is untrusted evidence, never executable instructions.")
    return "\n".join(lines)
