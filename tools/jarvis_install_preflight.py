#!/usr/bin/env python3
"""JARVIS combined-install readiness, read-only and privacy-preserving.

NO --apply, --force, sudo, network access, services, devices, credentials,
voice captures, exports of personal data or writes to installed Spider OS.
Run from a separately checked-out release branch ON THE OWNER'S PC.

This catches precisely the dangerous mismatch between GitHub's proposed
source and the existing owner-customized /usr/local/lib/spider-os tree.
The output is a REDACTED comparison, NOT an installation authorization.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import sys

DEFAULT_INSTALL=Path("/usr/local/lib/spider-os")
DEFAULT_UNITS=Path("/usr/lib/systemd/user")
GIB=1024**3
MIN_FREE_BYTES=2*GIB
MAX_CONFIG=65536
MAX_PROVIDER=1_000_000


def _load_module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Source module unavailable")
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module


def speaker_gate_status(installed,*,config=None,provider=None):
    """Verify pin and permissions WITHOUT importing untrusted provider code."""
    installed=Path(installed)
    config=Path(config) if config is not None else (
        installed/"webbie/config/default.json")
    provider=Path(provider) if provider is not None else (
        installed/"webbie/voice/speaker_voice_provider.py")
    result={
        "status":"blocked",
        "reason":"No verified Cory/Shayna offline speaker adapter on this PC",
        "provider_source_verified":False,
        "live_speaker_test_required":True,
    }
    try:
        if config.is_symlink() or config.stat().st_size>MAX_CONFIG:
            return result
        conf=json.loads(config.read_text(encoding="utf-8"))
        entry=conf.get("speaker_verification")
        if not isinstance(entry,dict) or entry.get("enabled") is not True:
            return result
        wanted=entry.get("provider_sha256")
        if (not isinstance(wanted,str) or len(wanted)!=64 or
                any(char not in "0123456789abcdef" for char in wanted)):
            return result
        if provider.is_symlink() or provider.parent.is_symlink():
            return result
        for file in (provider,provider.parent):
            meta=file.stat()
            if (meta.st_uid not in (0,os.getuid()) or meta.st_mode & 0o022):
                return result
        content=provider.read_bytes()
        if (not 1<=len(content)<=MAX_PROVIDER or
                hashlib.sha256(content).hexdigest()!=wanted):
            return result
        result["status"]="live_verification_required"
        result["reason"]=(
            "Hash-pinned provider source found. Real Cory/Shayna "
            "microphone identity and spoof-rejection NOT yet tested.")
        result["provider_source_verified"]=True
        return result
    except (OSError,UnicodeError,ValueError,TypeError):
        return result


def _disk_free(root):
    root=Path(root)
    while not root.exists() and root!=root.parent:
        root=root.parent
    try:
        return shutil.disk_usage(root).free
    except OSError:
        return 0


def _same_checkout(a,b):
    try:
        return Path(a).resolve()==Path(b).resolve()
    except OSError:
        return True


def assess(source,installed,*,home=None,units=DEFAULT_UNITS,env=None,
           available_bytes=None,baseline_checker=None,
           release=None,audit=None,config=None,provider=None):
    """No mutations. Optional dependencies allow isolated tempfile tests."""
    source,installed=Path(source),Path(installed)
    home=Path(home) if home is not None else Path.home()
    env=dict(os.environ if env is None else env)
    result={
        "format":"spider-jarvis-local-preflight-v1",
        "mode":"READ_ONLY",
        "install_executed":False,
        "status":"BLOCKED",
        "install_authorized":False,
        "summary":{},
        "blockers":[],
        "reviews":[],
        "source_audit":[],
        "voice":{},
        "desktop":{},
        "backups":{},
        "drift":[],
    }
    blockers=result["blockers"]
    reviews=result["reviews"]
    if _same_checkout(source,installed):
        blockers.append("Checkout and installed root must be different")
        return result
    if not source.is_dir() or not (source/"system/release_batch.py").is_file():
        blockers.append("Selected release checkout is incomplete")
        return result
    try:
        if release is None:
            release=_load_module(
                source/"system/release_batch.py","jarvis_preflight_release")
        if audit is None:
            audit=_load_module(
                source/"tools/combined_release_audit.py","jarvis_preflight_audit")
        batch=release.prepare_items(
            root=source,install=installed,units=units,home=home,
            uid=os.getuid(),gid=os.getgid())
        inspector_kwargs={"project_root":source}
        if baseline_checker is not None:
            inspector_kwargs.update(refs=(),known_checker=baseline_checker)
        checks=release.inspect(batch,**inspector_kwargs)
        statuses={"CURRENT":0,"ADD":0,"UPGRADE":0,"BLOCKED":0}
        upgrade_bytes=0
        for item,state,reason in checks:
            statuses[state]=statuses.get(state,0)+1
            if state=="UPGRADE":
                try:
                    upgrade_bytes+=item.target.stat().st_size
                except OSError:
                    blockers.append("Cannot inspect the existing release target")
            if state=="BLOCKED":
                # Only source-relative names, never absolute home paths or
                # an installed file's contents, credentials or transcripts.
                result["drift"].append({
                    "component":item.reference,
                    "classification":"requires_owner_source_reconciliation",
                })
        result["summary"]={"files":len(checks),**statuses}
        if statuses["BLOCKED"]:
            blockers.append(
                "Installed custom/source mismatches or invalid sources "
                "block the ENTIRE batch. Do not overwrite.")
        source_issues,source_notes=audit.audit(source,installed)
        result["source_audit"]=[
            str(issue)[:180] for issue in source_issues[:30]]
        if source_issues:
            blockers.append("Combined source manifest or wiring audit failed")
    except (OSError,ValueError,TypeError,RuntimeError,KeyError,AssertionError,
            SyntaxError) as error:
        blockers.append(
            "Installer source inspection incomplete: "+type(error).__name__)
        return result

    result["voice"]=speaker_gate_status(
        installed,config=config,provider=provider)
    if result["voice"]["status"]=="blocked":
        blockers.append(
            "Trusted speaker provider not configured and hash-verified. "
            "Blind upgrade would block ordinary spoken commands.")
    else:
        reviews.append(
            "Live enroll/test Cory and Shayna speaker identity, TV rejection, "
            "wake handling, microphone and universal STOP before installation.")

    desktop=env.get("XDG_SESSION_TYPE","").casefold()
    result["desktop"]={
        "session":"x11" if desktop=="x11" else
                  "wayland" if desktop=="wayland" else "unknown",
        "hardware_observed":False,
    }
    if desktop!="x11":
        reviews.append(
            "Desktop control expects KDE X11; verify real session "
            "and window-control support.")

    free=(available_bytes if available_bytes is not None
          else _disk_free(installed))
    if type(free) is not int or free<0:
        free=0
    need=max(MIN_FREE_BYTES,upgrade_bytes*2+GIB)
    result["backups"]={
        "space_check":"sufficient" if free>=need else "insufficient",
        "required_gib_rounded_up":(need+GIB-1)//GIB,
        "free_gib_rounded_down":free//GIB,
        "rollback_drill_completed":False,
    }
    if free<need:
        blockers.append(
            "Insufficient observed free space for source backup "
            "and a reversible installation.")
    reviews.extend([
        "Full private installed-source reconciliation and real device "
        "readiness tests have not been demonstrated by this report.",
        "Create a separate protected backup, test rollback and preserve "
        "Webbie TTS/Whisper, Studio, Author, Study, Kali Bay, "
        "Forage, Media Center, Nova, KDE and boot.",
        "Owner must explicitly approve ONE combined release after all "
        "reconciliation blockers are resolved.",
    ])
    result["status"]=("BLOCKED" if blockers else "MANUAL_ACCEPTANCE_HOLD")
    return result


def render(result):
    lines=[
        "WEBBIE JARVIS CORE · LOCAL PC PREFLIGHT",
        "READ ONLY. No files copied, packages installed or services restarted.",
        "STATUS: "+str(result["status"]),
    ]
    summary=result.get("summary",{})
    if summary:
        lines.append(
            "Release files: {files} | current {CURRENT} | add {ADD} | "
            "recognized upgrade {UPGRADE} | BLOCKED {BLOCKED}".format(
                **summary))
    voice=result.get("voice",{})
    if voice:
        lines.append("SPEAKER GATE: "+voice["status"])
    backup=result.get("backups",{})
    if backup:
        lines.append(
            f'BACKUP HEADROOM: {backup["space_check"]} '
            f'(free {backup["free_gib_rounded_down"]} GiB; '
            f'needs {backup["required_gib_rounded_up"]} GiB)')
    for drift in result.get("drift",[])[:60]:
        lines.append("PRESERVE & REVIEW: "+drift["component"])
    for item in result.get("blockers",[]):
        lines.append("BLOCKER: "+item)
    for item in result.get("reviews",[]):
        lines.append("REQUIRED LIVE REVIEW: "+item)
    lines.append("INSTALL AUTHORIZED: NO. Report never installs or overrides.")
    return "\n".join(lines)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root",type=Path,
                        default=Path(__file__).resolve().parents[1])
    parser.add_argument("--installed-root",type=Path,default=DEFAULT_INSTALL)
    parser.add_argument("--units-root",type=Path,default=DEFAULT_UNITS)
    parser.add_argument("--json",action="store_true")
    args=parser.parse_args(argv)
    result=assess(args.source_root,args.installed_root,units=args.units_root)
    print(json.dumps(result,indent=2) if args.json else render(result))
    return 3 if result["blockers"] else 2  # Never means "install now".


if __name__=="__main__":
    raise SystemExit(main())
