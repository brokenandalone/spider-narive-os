"""User-owned persistent, explicit Webbie authorization preference.

The on-disk record authorizes a *policy profile*, never a root process,
credential, session token, LLM message, or a connection to cloud accounts.
Default is DENY. Authorized and paused are distinct durable states so STOP
cannot silently re-enable after GUI restart or login.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import stat
import tempfile

DEFAULT_PATH=Path.home()/".config/spider-os/webbie-owner-authorization.json"
VERSION=1
MAX_BYTES=2048
DISABLED={"version":VERSION,"authorized":False,"paused":True,
          "kali_on_demand":False}
ACTIONS=frozenset(("authorize","pause","resume","revoke"))


def read_policy(path=DEFAULT_PATH):
    target=Path(path)
    try:
        if target.is_symlink():
            return dict(DISABLED)
        info=target.stat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid()
                or info.st_size>MAX_BYTES or info.st_size<2
                or info.st_mode&0o077):
            return dict(DISABLED)
        raw=json.loads(target.read_text(encoding="utf-8"))
        if (not isinstance(raw,dict) or raw.get("version")!=VERSION
                or type(raw.get("authorized")) is not bool
                or type(raw.get("paused")) is not bool
                or type(raw.get("kali_on_demand")) is not bool
                or raw.get("profile")!="routine_apps_only"
                or not raw["authorized"] and not raw["paused"]):
            return dict(DISABLED)
        if raw["kali_on_demand"] and not raw["authorized"]:
            return dict(DISABLED)
        return {"version":VERSION,"authorized":raw["authorized"],
                "paused":raw["paused"],
                "kali_on_demand":raw["kali_on_demand"]}
    except (OSError,TypeError,ValueError,UnicodeError):
        return dict(DISABLED)


def update_policy(action, *, owner_clicked=False, path=DEFAULT_PATH):
    """The only durable state transitions.

    'authorize', 'resume' and 'revoke' require a direct owner GUI click.
    'pause' may also follow the STOP voice/keyboard safety channel.
    A language model never receives this callback or a path parameter.
    """
    if action not in ACTIONS:
        raise ValueError("Unsupported permanent authorization operation")
    if action!="pause" and owner_clicked is not True:
        raise PermissionError("Explicit local owner click required")

    target=Path(path)
    parent=target.parent
    if parent.is_symlink():
        raise PermissionError("Unsafe authorization directory")
    parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    info=parent.stat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid()
            or info.st_mode&0o077):
        raise PermissionError("Authorization directory must be owner-private")
    if target.is_symlink():
        raise PermissionError("Refusing authorization symlink")
    try:
        current_info=target.stat()
        if (not stat.S_ISREG(current_info.st_mode)
                or current_info.st_uid!=os.getuid()
                or current_info.st_mode&0o077
                or current_info.st_size>MAX_BYTES):
            raise PermissionError("Unsafe existing owner authorization file")
    except FileNotFoundError:
        pass

    previous=read_policy(target)
    if action=="authorize":
        new={"version":VERSION,"authorized":True,"paused":False,
             "kali_on_demand":True}
    elif action=="resume":
        if not previous["authorized"]:
            raise PermissionError("First grant permanent authorization")
        new={"version":VERSION,"authorized":True,"paused":False,
             "kali_on_demand":previous["kali_on_demand"]}
    elif action=="pause":
        new={"version":VERSION,"authorized":previous["authorized"],
             "paused":True,
             "kali_on_demand":previous["kali_on_demand"]}
    else:
        new=dict(DISABLED)

    payload=json.dumps({**new,"profile":"routine_apps_only"},
                       separators=(",",":"),sort_keys=True).encode()
    if len(payload)>MAX_BYTES:
        raise ValueError("Owner authorization record is oversized")
    fd,temporary=tempfile.mkstemp(prefix=".webbie-owner-auth-",dir=parent)
    try:
        os.fchmod(fd,0o600)
        with os.fdopen(fd,"wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary,target)
        try:
            directory_fd=os.open(str(parent),os.O_DIRECTORY|os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            # The policy content was written; sync isn't always supported.
            pass
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return new
