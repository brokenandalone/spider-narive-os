"""Read-only local service-status adapters for Webbie owner-wide access.

These are narrow, source-reviewed integrations. A single owner click may
authorize repeated local status queries without repeated prompts.
No credential/token reads, cloud sign-ins, emails, radio playback commands,
uploads, cloud browsing, model prompts or remote network requests.
Adding future third-party services requires a new reviewed adapter.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import stat
from urllib.request import build_opener,ProxyHandler,Request
from urllib.error import URLError

SERVICES=("webbie","nova","onedrive")
LOCAL_NOVA_HEALTH="http://127.0.0.1:9876/health"
MAX_READ_BYTES=2048

def _private_json(path):
    try:
        source=Path(path)
        if source.is_symlink():
            return {}
        info=source.stat()
        if (not stat.S_ISREG(info.st_mode)
                or info.st_uid!=os.getuid()
                or info.st_size>16384 or info.st_mode & 0o077):
            return {}
        result=json.loads(source.read_text(encoding="utf-8"))
        return result if isinstance(result,dict) else {}
    except (OSError,UnicodeError,ValueError,TypeError):
        return {}


def read_local_service_status(name, *, access,
                              agent_path=None, onedrive_path=None,
                              opener=None):
    """An enabled owner-wide gate is required even for read-only checks."""
    if name not in SERVICES or access is None or (
            not access.authorize_service(name,"status.read")):
        raise PermissionError("Service status is not authorized by the owner")

    if name=="webbie":
        path=agent_path or Path.home()/".local/state/spider-os/webbie.json"
        data=_private_json(path)
        return {"service":"webbie","configured":True,
                "reported_online":data.get("online") is True,
                "detail":"Owner-private resident status only; not live hardware proof."}

    if name=="onedrive":
        path=onedrive_path or Path.home()/".config/spider-os/onedrive.json"
        settings=_private_json(path)
        return {"service":"onedrive",
                "configured":settings.get("enabled") is True,
                "reported_online":False,
                "detail":"Local sync preference only; OAuth and cloud access not tested."}

    # Localhost-only no-proxy GET; fixed URL no caller-supplied destination.
    transport=opener if opener is not None else build_opener(ProxyHandler({}))
    try:
        result=transport.open(
            Request(LOCAL_NOVA_HEALTH,method="GET"),timeout=2)
        with result as response:
            packet=response.read(MAX_READ_BYTES+1)
        if len(packet)>MAX_READ_BYTES:
            raise ValueError("Oversized local status")
        data=json.loads(packet.decode("utf-8"))
        healthy=(isinstance(data,dict)
                 and data.get("ok") is True
                 and data.get("service")=="Spider AI DJ")
    except (URLError,OSError,TimeoutError,ValueError,UnicodeError,TypeError,KeyError):
        healthy=False
    return {"service":"nova","configured":healthy,
            "reported_online":healthy,
            "detail":"Local Nova health endpoint only; no broadcast command."}


def status_summary(statuses):
    result=["WEBBIE SAFE SERVICE ACCESS · LOCAL STATUS ONLY"]
    for entry in statuses:
        if not isinstance(entry,dict) or entry.get("service") not in SERVICES:
            continue
        item=entry["service"]
        result.append(
            item.title()+": "+
            ("locally reported available" if entry.get("reported_online") is True
             else "not live-confirmed")+
            " · "+str(entry.get("detail",""))[:140])
    result.append("No login, cloud files, broadcasts or connected account actions were attempted.")
    return "\n".join(result)
