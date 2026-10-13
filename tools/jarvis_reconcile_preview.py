#!/usr/bin/env python3
"""PRIVATE, NON-INSTALLING reconciliation of Spider OS owner-source drift.

Produces only metadata on stdout. With --output, a 0700 local-only folder
contains bounded textual diffs (0600) for owner review. It never imports or
runs installed Python, modifies the installed OS, fetches remotes, merges,
writes Git objects, uploads data or disables the strict batch preflight.

Exact git provenance means only that a blob was seen at the same relative
path in a local Git ref. Even that DOES NOT authorize overwriting anything.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import difflib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

MAX_DIFF_FILE_BYTES=1_000_000
MAX_DIFF_OUTPUT_BYTES=600_000
MAX_DIFF_FILES=80
MAX_GIT_OUTPUT=24_000_000
ACCEPTED=frozenset({"CURRENT","ADD","UPGRADE","BLOCKED"})


def _load_release(source):
    location=Path(source)/"system/release_batch.py"
    spec=importlib.util.spec_from_file_location(
        "spider_jarvis_reconciliation_release",location)
    if spec is None or spec.loader is None:
        raise RuntimeError("No selected Spider OS release module")
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module


def _blob_hash(blob):
    # SHA-1 here is Git's object identifier, NOT an integrity/auth signature.
    envelope=b"blob "+str(len(blob)).encode("ascii")+b"\0"+blob
    return hashlib.sha1(envelope).hexdigest()


def _git_blobs_at_paths(source,relatives,*,runner=subprocess.run):
    """One bounded local read-only git query for all proposed target paths."""
    if not relatives:
        return {}
    commands=[
        "git","-C",str(source),"rev-list","--objects","--all","--",
        *sorted(relatives),
    ]
    try:
        run=runner(commands,stdout=subprocess.PIPE,
                   stderr=subprocess.DEVNULL,timeout=35,check=False)
        if run.returncode!=0 or len(run.stdout)>MAX_GIT_OUTPUT:
            return {}
        output={}
        for line in run.stdout.decode("utf-8","replace").splitlines():
            object_id,space,relative=line.partition(" ")
            if (space and relative in relatives and
                    re.fullmatch(r"[0-9a-f]{40,64}",object_id)):
                output.setdefault(relative,set()).add(object_id)
        return output
    except (OSError,subprocess.TimeoutExpired,ValueError):
        return {}


def _file_blob(path):
    path=Path(path)
    try:
        if path.is_symlink():
            return None
        meta=path.stat()
        if (not stat.S_ISREG(meta.st_mode) or meta.st_size>MAX_DIFF_FILE_BYTES
                or meta.st_nlink>1):
            return None
        return path.read_bytes()
    except (OSError,PermissionError):
        return None


def _stage_directory(output,source,installed,*,home=None):
    output=Path(output).expanduser()
    if not output.is_absolute() or output.exists() or output.is_symlink():
        raise RuntimeError("Choose a new absolute, unused private output folder")
    home=Path(home).resolve() if home is not None else Path.home().resolve()
    if home not in output.parents or any(part.startswith(".") for part in
                                          output.relative_to(home).parts):
        raise RuntimeError("Review output must be a new visible owner-home folder")
    if (source.resolve()==output or installed.resolve()==output or
            source.resolve() in output.parents or
            installed.resolve() in output.parents):
        raise RuntimeError("Review output cannot reside inside source or installed tree")
    here=home
    for part in output.relative_to(home).parts[:-1]:
        here=here/part
        if here.is_symlink():
            raise RuntimeError("Review output parent may not be a symbolic link")
    parent=output.parent
    info=parent.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid():
        raise RuntimeError("Review output parent must be user-owned")
    output.mkdir(mode=0o700)
    (output/"diffs").mkdir(mode=0o700)
    return output


def _write_private(path,data):
    path=Path(path)
    if isinstance(data,str):
        data=data.encode("utf-8")
    handle=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|
                   getattr(os,"O_NOFOLLOW",0),0o600)
    try:
        with os.fdopen(handle,"wb") as file:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
    finally:
        # If fdopen/write failed, the handle is either closed or fully owned
        # by the context manager; only report data, not credentials.
        pass


def compare_release(source,installed,*,output=None,home=None,units=None,
                    release=None,checker=None,git_runner=subprocess.run):
    """Classify drift via exact local git provenance, stage diffs if asked.

    A returned REVIEW classification is never a writable merge decision.
    'recognized_git_blob' means content was seen under this path in a local
    Git ref but the strict release baseline STILL BLOCKS a blind apply.
    """
    source=Path(source).expanduser().resolve()
    installed=Path(installed).expanduser()
    home=Path(home) if home is not None else Path.home()
    if source==installed.resolve():
        raise RuntimeError("Review a checkout separate from installed Spider OS")
    module=release or _load_release(source)
    opts=dict(root=source,install=installed,home=home,
              uid=os.getuid(),gid=os.getgid())
    if units is not None:
        opts["units"]=units
    items=module.prepare_items(**opts)
    checks=dict(project_root=source)
    if checker is not None:
        checks.update(refs=(),known_checker=checker)
    observed=module.inspect(items,**checks)
    blocked=[item for item,status,_ in observed if status=="BLOCKED"]
    rels={item.reference for item in blocked if item.reference}
    git_blobs=_git_blobs_at_paths(source,rels,runner=git_runner)
    root=None
    if output is not None:
        root=_stage_directory(output,source,installed,home=home)
    results=[]
    for item,status,reason in observed:
        if status not in ACCEPTED:
            raise RuntimeError("Unknown source/installed preflight classification")
        if status!="BLOCKED":
            continue
        relative=item.reference
        obj={
            "component":relative,
            "installer_status":"BLOCKED",
            "reason":"owner-customized or unknown installed content",
            "classification":"manual_reconciliation_required",
            "source_lines":None,
            "installed_lines":None,
            "exact_git_history_match":False,
            "private_diff_written":False,
        }
        # Do not open the installed file if source or target safety checks
        # reject it. Never follow an installed symlink or inspect special files.
        if (not module.safe_path(item.source) or
                not module.safe_path(item.target)):
            obj["classification"]="unsafe_path_manual_review"
            results.append(obj)
            continue
        proposed=_file_blob(item.source)
        local=_file_blob(item.target)
        if proposed is None or local is None:
            obj["classification"]="unreadable_or_large_manual_review"
            results.append(obj)
            continue
        historical=_blob_hash(local) in git_blobs.get(relative,set())
        obj["exact_git_history_match"]=historical
        obj["classification"]=("recognized_git_blob_manual_review"
                               if historical else "custom_code_manual_merge")
        if b"\0" not in proposed and b"\0" not in local:
            proposed_lines=proposed.decode("utf-8","replace").splitlines(True)
            local_lines=local.decode("utf-8","replace").splitlines(True)
            obj["source_lines"]=len(proposed_lines)
            obj["installed_lines"]=len(local_lines)
            if root is not None:
                diff="".join(difflib.unified_diff(
                    local_lines,proposed_lines,
                    fromfile="INSTALLED/"+relative,
                    tofile="PROPOSED/"+relative,
                    n=3))
                if (diff and len(diff.encode("utf-8"))<=MAX_DIFF_OUTPUT_BYTES):
                    out=root/"diffs"/(relative+".diff")
                    out.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
                    _write_private(out,diff)
                    obj["private_diff_written"]=True
        results.append(obj)
    totals=Counter(row["classification"] for row in results)
    answer={
        "format":"spider-jarvis-private-reconciliation-v1",
        "source_only":True,
        "installed_files_modified":False,
        "installation_authorized":False,
        "files_reviewed":len(observed),
        "blocked_files":len(blocked),
        "classifications":dict(sorted(totals.items())),
        "items":results,
        "voice_provider":"not fixed by source reconciliation",
        "next_action":"Owner reviews and reconciles custom code; no blind apply.",
    }
    if root is not None:
        _write_private(root/"summary.json",json.dumps(
            answer,indent=2,sort_keys=True)+"\n")
        _write_private(root/"README.txt",(
            "PRIVATE WEBBIE JARVIS SOURCE REVIEW\n"
            "All .diff files contain OWN COMPUTER CODE. Do not upload "
            "these files or share this directory without reviewing it.\n"
            "Diffs show INSTALLED code versus PROPOSED GitHub code. "
            "They do NOT merge source or authorize installation.\n"
            "A recognized Git blob still needs review and installation "
            "baseline recognition; custom code requires real reconciliation.\n"
            "No installed files, boot settings, services, TTS or models "
            "were modified. Voice verifier blocker remains separate.\n"))
    return answer


def render(answer):
    lines=[
        "WEBBIE JARVIS · PRIVATE SOURCE RECONCILIATION",
        "No installed source modified; installation remains BLOCKED.",
        f'Inspected: {answer["files_reviewed"]} release files | '
        f'blocked: {answer["blocked_files"]}',
    ]
    for classification,count in answer["classifications"].items():
        lines.append(f"{classification}: {count}")
    lines.extend(
        f'{item["classification"]}: {item["component"]}'
        for item in answer["items"])
    lines.append("Voice verification still needs its own live provider test.")
    return "\n".join(lines)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root",type=Path,
                        default=Path(__file__).resolve().parents[1])
    parser.add_argument("--installed-root",type=Path,
                        default=Path("/usr/local/lib/spider-os"))
    parser.add_argument("--output",type=Path,default=None,
                        help="NEW private owner-only local review folder; optional")
    args=parser.parse_args(argv)
    try:
        result=compare_release(args.source_root,args.installed_root,
                               output=args.output)
    except (OSError,RuntimeError,ValueError,TypeError,AssertionError) as error:
        print("JARVIS review stopped: "+str(error)[:250],file=sys.stderr)
        return 3
    print(render(result))
    if args.output is not None:
        print("Private owner-only diff folder: "+str(args.output))
        print("Contains project source diffs; DO NOT upload the whole folder.")
    return 2 if result["blocked_files"] else 0


if __name__=="__main__":
    raise SystemExit(main())
