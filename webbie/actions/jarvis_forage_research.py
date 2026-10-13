"""Bounded public-web research using the EXISTING Spider Forage engine.

No new cloud account or model. Public search hits are displayed as untrusted
evidence and can never become shell, browser-control or Kali instructions.
"""
from __future__ import annotations
import importlib.util
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit
import ipaddress

_SOURCE_ROOT=Path(__file__).resolve().parents[2]
LOCATIONS=(
    Path("/usr/local/lib/spider-os/forage/engine.py"),
    _SOURCE_ROOT/"forage/engine.py",
)
MAX_RESULTS=8
MAX_QUERY=150


def _forage_search(query, max_results):
    module_path=next((p for p in LOCATIONS if p.is_file() and
                      not p.is_symlink()),None)
    if module_path is None:
        raise RuntimeError("Forage engine isn't installed in Spider OS")
    spec=importlib.util.spec_from_file_location(
        "_spider_jarvis_forage_engine",module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Forage engine is unavailable")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.web_search(query,max_results=max_results)


def _plain(value,limit):
    if not isinstance(value,str):
        return ""
    return "".join(x for x in value if x.isprintable())[:limit].strip()


def _public_result(url):
    if not isinstance(url,str) or len(url)>600:
        return False
    try:
        x=urlsplit(url)
        host=(x.hostname or "").lower()
        if (x.scheme!="https" or not x.netloc or
                x.username or x.password or x.port not in (None,443)
                or not re.fullmatch(r"[a-z0-9.-]+",host)
                or "." not in host
                or host.endswith((".local",".localhost",".internal",".test",
                                   ".invalid",".example"))):
            return False
        try:
            ipaddress.ip_address(host)
            return False
        except ValueError:
            pass
        return True
    except ValueError:
        return False


def research_public_web(query,*,search=None,max_results=6):
    if (not isinstance(query,str) or not 2<=len(query.strip())<=MAX_QUERY
            or any(ord(ch)<32 for ch in query)):
        raise ValueError("Provide a short single-line public research topic")
    if not isinstance(max_results,int) or not 1<=max_results<=MAX_RESULTS:
        raise ValueError("Invalid research result limit")
    operator=search or _forage_search
    raw=operator(query.strip(),max_results=max_results)
    if not isinstance(raw,list):
        raise RuntimeError("Forage did not return a results list")
    sources=[]
    for item in raw[:MAX_RESULTS]:
        if not isinstance(item,dict) or not _public_result(item.get("url")):
            continue
        sources.append({
            "title":_plain(item.get("title",""),150),
            "url":item["url"][:600],
            "summary":_plain(item.get("snippet",""),320),
        })
    return {
        "query":query.strip(),"sources":sources,
        "no_remote_account_access":True,
        "no_remote_actions":True,
    }


def render_public_research(data):
    lines=[
        "JARVIS + FORAGE · PUBLIC WEB RESEARCH",
        "Topic: "+data["query"],
        "Sources returned: "+str(len(data["sources"])),
    ]
    for item in data["sources"]:
        lines.extend([
            "• "+(item["title"] or "Untitled source"),
            item["url"],
            item["summary"][:320],
        ])
    lines.append(
        "Search results are third-party untrusted material. "
        "No apps, websites, accounts or OS settings were modified.")
    return "\n".join(lines)
