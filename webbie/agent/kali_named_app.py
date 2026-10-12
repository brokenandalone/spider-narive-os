"""Exact, explicit owner-requested Kali desktop app opening.

Uses Kali Bay's inventory and fixed manager commands, never text as shell.
This is a tool LAUNCH, NOT permission to scan, exploit, brute-force, change
a target, or execute model-proposed parameters. Kali tools may have their
own risk and consent needs before performing network or privileged tasks.
"""
from __future__ import annotations
import json
import re
import subprocess
from pathlib import Path

APP_ID=re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,100}\.desktop$")
OWNER_COMMAND=re.compile(
    r"(?:(?:open|launch|start|use)\s+kali\s+"
    r"(?:app|application)\s+)(.{1,95})",
    flags=re.IGNORECASE,
)
MAX_APPS=1500
MAX_OUTPUT=500_000


def parse_named_app_request(phrase):
    """Only a whole, literal one-line instruction with explicit Kali scope."""
    if not isinstance(phrase,str) or len(phrase)>180 or "\n" in phrase:
        return None
    cleaned=re.sub(r"^(?:hey\s+)?webbie\s*[,:]?\s+", "",phrase.strip(),
                   flags=re.I).strip(" .!?")
    match=OWNER_COMMAND.fullmatch(cleaned)
    if not match:
        return None
    wanted=match.group(1).strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ._+()-]{0,94}",wanted):
        return None
    return wanted


def installed_apps(manager, *, run=subprocess.run):
    """Read-only, bounded inventory; never executes arbitrary app Exec text."""
    manager=Path(manager)
    try:
        result=run([str(manager),"apps-json"],capture_output=True,
                   text=True,timeout=24,check=False)
        if result.returncode or len(result.stdout)>MAX_OUTPUT:
            return []
        raw=json.loads(result.stdout)
        entries=raw.get("applications") if isinstance(raw,dict) else None
        if not isinstance(entries,list) or len(entries)>MAX_APPS:
            return []
        available=[]
        for item in entries:
            if not isinstance(item,dict):
                continue
            ident=item.get("id")
            name=item.get("name")
            if (isinstance(ident,str) and APP_ID.fullmatch(ident) and
                    isinstance(name,str) and 1<=len(name.strip())<=95 and
                    not any(ord(ch)<32 for ch in name)):
                available.append((ident,name.strip()))
        return available
    except (OSError,subprocess.TimeoutExpired,ValueError,
            UnicodeError,TypeError,KeyError):
        return []


def launch_named_kali_app(phrase,manager,*,run=subprocess.run,
                          spawn=subprocess.Popen):
    """Require exact unambiguous installed entry; launch one GUI app only."""
    wanted=parse_named_app_request(phrase)
    if wanted is None:
        return None
    apps=installed_apps(manager,run=run)
    matches=[(ident,name) for ident,name in apps if
             ident.casefold()==wanted.casefold() or
             ident.casefold().removesuffix(".desktop")==wanted.casefold() or
             name.casefold()==wanted.casefold()]
    if len(matches)!=1:
        if not apps:
            return "Kali Bay's installed application list is unavailable. No tool was started."
        return ("Choose one exact installed Kali application name. "
                "No tool was started.")
    ident,name=matches[0]
    manager=Path(manager)
    try:
        check=run([str(manager),"app-check",ident],capture_output=True,
                  text=True,timeout=12,check=False)
        if check.returncode:
            return f"{name} could not be verified in Kali Bay. Nothing was started."
        spawn([str(manager),"app-open",ident],
              stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
              stderr=subprocess.DEVNULL,start_new_session=True,
              close_fds=True)
        return (f"Requested Kali Bay application {name}. "
                "Application readiness and activity are not verified; "
                "no scan or other operation was requested.")
    except (OSError,subprocess.TimeoutExpired,ValueError):
        return f"Kali Bay could not open {name}. Nothing was started."
