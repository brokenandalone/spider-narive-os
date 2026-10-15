"""Read-only JARVIS website project auditor.

Checks local HTML pages and asset references; never installs dependencies,
runs npm scripts, reads credentials, rewrites a site or deploys to hosting.
A project must be deliberately picked by the owner in the native GUI.
"""
from __future__ import annotations
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit,unquote
import os
import stat
from jarvis_local_evidence import approved_root

MAX_PAGES=160
MAX_CONTENT_BYTES=512_000
MAX_MISSING=50
INDEX_NAMES=("index.html","index.htm")
REFS={"img":"src","script":"src","link":"href","source":"src",
      "video":"poster","audio":"src"}


class _Assets(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.assets=[]

    def handle_starttag(self,tag,attrs):
        key=REFS.get(tag.lower())
        if key is None:
            return
        values=dict(attrs)
        kind=values.get("rel","").lower() if tag=="link" else ""
        if tag=="link" and kind not in ("stylesheet","icon","preload","modulepreload",
                                       "apple-touch-icon"):
            return
        value=values.get(key,"")
        if isinstance(value,str) and len(value)<800:
            self.assets.append(value)


def _read_page(file):
    try:
        flags=os.O_RDONLY|getattr(os,"O_NOFOLLOW",0)
        fd=os.open(file,flags)
        with os.fdopen(fd,"rb") as stream:
            data=os.fstat(stream.fileno())
            if (not stat.S_ISREG(data.st_mode) or data.st_uid!=os.getuid()
                    or data.st_size>MAX_CONTENT_BYTES or data.st_nlink>1):
                return ""
            raw=stream.read(MAX_CONTENT_BYTES+1)
        return raw.decode("utf-8",errors="replace") if len(raw)<=MAX_CONTENT_BYTES else ""
    except (OSError,UnicodeError):
        return ""


def _local_asset(root,page,reference):
    try:
        url=urlsplit(reference)
        if (url.scheme or url.netloc or not url.path or
                reference.startswith(("//","data:","javascript:","#"))):
            return None
        path=unquote(url.path)
        if "\0" in path or "\\" in path or any(x.startswith(".") for x in
                                                 Path(path.lstrip("/")).parts):
            return None
        if path.startswith("/"):
            candidate=root/path.lstrip("/")
        else:
            candidate=page.parent/path
        resolved=candidate.resolve()
        if resolved!=root and root not in resolved.parents:
            return None
        # Symlinks are never counted as authorized assets.
        current=root
        for part in resolved.relative_to(root).parts:
            current=current/part
            if current.is_symlink():
                return "blocked"
        return resolved
    except (OSError,ValueError):
        return None


def inspect_site_project(folder, *, home=None):
    root=approved_root(folder,home=home)
    pages=[]
    stack=[root]
    while stack and len(pages)<MAX_PAGES:
        directory=stack.pop()
        try:
            entries=sorted(os.scandir(directory),key=lambda x:x.name.casefold())
        except OSError:
            continue
        for entry in entries:
            if (entry.name.startswith(".") or
                    entry.name in ("node_modules","dist","build","vendor",
                                   "private","credentials","secrets")):
                continue
            try:
                if entry.is_symlink():
                    continue
                if entry.is_dir(follow_symlinks=False):
                    if len(Path(entry.path).relative_to(root).parts)<6:
                        stack.append(Path(entry.path))
                elif entry.is_file(follow_symlinks=False) and \
                        Path(entry.path).suffix.lower() in (".html",".htm"):
                    pages.append(Path(entry.path))
                    if len(pages)>=MAX_PAGES:
                        break
            except (OSError,ValueError):
                continue
    missing=[]
    external=0
    references=0
    for page in pages:
        markup=_read_page(page)
        if not markup:
            continue
        parser=_Assets()
        parser.feed(markup)
        for reference in parser.assets:
            references+=1
            target=_local_asset(root,page,reference)
            if target is None:
                external+=1
                continue
            if target=="blocked":
                continue
            if not target.is_file() and len(missing)<MAX_MISSING:
                missing.append({
                    "page":str(page.relative_to(root)),
                    "reference":reference[:180],
                })
    root_index=any((root/name).is_file() for name in INDEX_NAMES)
    return {
        "site":root.name,
        "html_pages":len(pages),
        "asset_references":references,
        "external_or_dynamic_references":external,
        "missing_local_assets":missing,
        "has_root_index":root_index,
        "truncated":len(pages)>=MAX_PAGES or len(missing)>=MAX_MISSING,
        "deployment":"not attempted",
        "read_only":True,
    }


def render_site_report(report):
    lines=[
        "JARVIS · LOCAL WEBSITE AUDIT · READ ONLY",
        "Selected project: "+str(report["site"]),
        "HTML pages inspected: "+str(report["html_pages"]),
        "Referenced assets: "+str(report["asset_references"]),
        "External/dynamic references: "+str(report["external_or_dynamic_references"]),
        "Root index.html present: "+("yes" if report["has_root_index"] else "no"),
        "Missing local assets: "+str(len(report["missing_local_assets"])),
    ]
    lines.extend(
        f'{x["page"]} → {x["reference"]}'
        for x in report["missing_local_assets"]
    )
    if report["truncated"]:
        lines.append("Some results exceeded the bounded inspection limit.")
    lines.append("No site files changed, no build ran, and no remote deployment occurred.")
    return "\n".join(lines)
