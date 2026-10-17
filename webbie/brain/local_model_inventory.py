"""Read-only local Ollama/voice model readiness for Webbie's control center.

No implicit downloads, cloud fallbacks, model swaps, or scans outside
127.0.0.1. Role preferences are read from the installed owner's config.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

TAGS="http://127.0.0.1:11434/api/tags"
RUNNING="http://127.0.0.1:11434/api/ps"
LIMIT=180000


def _request(url, *, opener, timeout):
    with opener(url,timeout=timeout) as reply:
        if hasattr(reply,"geturl") and reply.geturl()!=url:
            raise ValueError("Unexpected local model endpoint redirect")
        data=json.loads(reply.read(LIMIT).decode("utf-8"))
    if not isinstance(data,dict):
        raise ValueError("Invalid local Ollama response")
    return data


def inspect_local_models(*, opener=None,timeout=2,
                         brain_preference=None,vision_preference=None):
    """Return statuses only, never issue a model-generation request."""
    if not 0<timeout<=10:
        raise ValueError("Model read-only timeout must be 0-10 seconds")
    opener=opener or urllib.request.urlopen
    try:
        installed=_request(TAGS,opener=opener,timeout=timeout)
    except (OSError,TimeoutError,UnicodeError,ValueError,urllib.error.URLError):
        return {"online":False,"installed":[],"running":[],
                "brain":{"requested":brain_preference,"ready":False},
                "vision":{"requested":vision_preference,"ready":False},
                "message":"Ollama is not responding on local loopback."}
    names=[]
    for row in installed.get("models",[]) if isinstance(installed.get("models"),list) else []:
        if isinstance(row,dict):
            name=row.get("name")
            if isinstance(name,str) and 1<=len(name)<=100 and all(
                    ch.isalnum() or ch in "._:-/" for ch in name):
                names.append(name)
    names=sorted(set(names))[:150]
    running=[]
    try:
        packets=_request(RUNNING,opener=opener,timeout=timeout)
        for row in packets.get("models",[]) if isinstance(packets.get("models"),list) else []:
            if isinstance(row,dict) and isinstance(row.get("name"),str) and row["name"] in names:
                running.append(row["name"])
    except (OSError,TimeoutError,UnicodeError,ValueError,urllib.error.URLError):
        pass
    return {
        "online":True,"installed":names,"running":sorted(set(running)),
        "brain":{"requested":brain_preference,"ready":brain_preference in names
                 if brain_preference else None},
        "vision":{"requested":vision_preference,"ready":vision_preference in names
                  if vision_preference else None},
        "message":"Local model inventory available. No models were downloaded or changed.",
    }


def report_lines(result):
    if not result.get("online"):
        return result.get("message","Local Ollama offline.")
    text=["Webbie local model inventory",
          f"Installed model tags: {len(result.get('installed',[]))}",
          "Loaded currently: "+(", ".join(result["running"]) if result.get("running") else "none reported")]
    for role in ("brain","vision"):
        info=result.get(role,{})
        chosen=info.get("requested") or "not specified"
        state=info.get("ready")
        outcome=("installed" if state is True else
                 "MISSING" if state is False else "no explicit preference")
        text.append(f"{role.title()} preference: {chosen} ({outcome})")
    if result.get("installed"):
        text.append("All local models: "+", ".join(result["installed"][:20]))
        if len(result["installed"])>20:
            text.append("Additional installed models omitted from this view.")
    text.append("This only checks model availability; it does not verify response quality.")
    return "\n".join(text)
