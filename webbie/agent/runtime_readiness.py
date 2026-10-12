"""Evidence-based, read-only runtime readiness report for Webbie.

Never enables services, opens devices, downloads models, reads prompts,
searches documents, or infers speaker identity. A 'ready' component is
only ready for the narrow observed signal, not proof of end-to-end operation.
"""
from __future__ import annotations
from dataclasses import dataclass
import json
import os
from pathlib import Path
import stat
import time

DEFAULT_AGENT = Path.home()/".local/state/spider-os/webbie.json"
DEFAULT_CONTEXT = Path.home()/".local/state/spider-os/webbie-jarvis-context.json"
DEFAULT_PROACTIVE = Path.home()/".local/state/spider-os/webbie-proactive.json"
MAX_FILE = 32768

@dataclass(frozen=True)
class Observation:
    key: str
    status: str
    detail: str

def _private_json(path):
    try:
        path=Path(path)
        if path.is_symlink():
            return {}
        info=path.stat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid()
                or info.st_size>MAX_FILE or info.st_mode&0o077):
            return {}
        data=json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data,dict) else {}
    except (OSError,ValueError,UnicodeError,TypeError):
        return {}

def inspect_readiness(*, agent_path=DEFAULT_AGENT,
                      context_path=DEFAULT_CONTEXT,
                      proactive_path=DEFAULT_PROACTIVE,
                      now=None):
    """No side effects: snapshots only from owner-only status files."""
    timestamp=float(time.time() if now is None else now)
    items=[]
    agent=_private_json(agent_path)
    updated=agent.get("updated")
    # Source stores local naive ISO datetime. Compare naive wall clock only,
    # and avoid making a time-zone-dependent claim if it is invalid.
    fresh=False
    if isinstance(updated,str) and len(updated)<80:
        try:
            from datetime import datetime
            point=datetime.fromisoformat(updated)
            if point.tzinfo is None:
                age=(datetime.now()-point).total_seconds() if now is None else None
                fresh=age is not None and 0<=age<60
        except (ValueError,TypeError,OverflowError):
            pass
    items.append(Observation(
        "agent", "reported" if fresh and agent.get("online") is True else "unknown",
        "Recent resident agent heartbeat reported" if fresh and agent.get("online") is True
        else "No recent verified source-agent heartbeat; service may still be running"))
    microphone=agent.get("voice_listener")
    if microphone is True and fresh:
        items.append(Observation("microphone","reported",
                  "Voice listener reports active. Actual hearing and speaker identity unverified"))
    elif microphone is False:
        items.append(Observation("microphone","warning",
                  "Resident status reports voice listener stopped or failed"))
    else:
        items.append(Observation("microphone","unknown",
                  "Voice listener not recently confirmed; microphone device not accessed"))

    from jarvis_context import read_context
    context=read_context(context_path,clock=lambda:timestamp)
    items.append(Observation("workspace","reported" if context else "unknown",
        "Current short-lived GUI workspace context reported" if context
        else "No live GUI context; no screen/window inspection attempted"))
    proactive=_private_json(proactive_path)
    checks=proactive.get("checks")
    result_count=len(checks) if isinstance(checks,dict) else 0
    items.append(Observation(
        "proactive","reported" if result_count else "unknown",
        f"Stored results from {min(result_count,20)} check categories" if result_count
        else "No readable proactive check results"))
    from privacy_controls import private_session_active
    private=private_session_active()
    items.append(Observation("privacy","reported",
                  "Private chat-memory mode ON" if private else
                  "Normal local chat-memory mode"))
    from voice_trust import trust_status
    items.append(Observation("speaker_identity","unavailable",trust_status()))
    model=agent.get("local_model")
    allowed=("normal","ready_to_try","temporarily_paused")
    status=model.get("status") if isinstance(model,dict) else None
    if fresh and status in allowed:
        label=("temporarily_paused" if status=="temporarily_paused"
               else "recent_failure" if status=="ready_to_try"
               else "normal")
        items.append(Observation(
            "local_ai","warning" if status!="normal" else "reported",
            "Local AI request governor: "+label+
            " (does not verify model quality or active inference)"))
    else:
        items.append(Observation(
            "local_ai","unknown",
            "No fresh local AI request status reported"))
    intake=agent.get("voice_intake")
    keys=("heard_transcript","rejected_unverified",
          "verified_input","emergency_stop")
    if fresh and isinstance(intake,dict) and all(
            type(intake.get(key)) is int and 0<=intake[key]<=1_000_000
            for key in keys):
        items.append(Observation(
            "voice_intake","reported",
            "Coarse speech counters available; open Voice Lab for details"))
    else:
        items.append(Observation(
            "voice_intake","unknown",
            "No fresh voice intake counters reported"))
    return tuple(items)

def render_report(items):
    acceptable={"reported","warning","unknown","unavailable"}
    lines=["WEBBIE · LIVE READINESS REPORT",
           "Read-only status, not proof of working hardware or computer-control permission."]
    for item in items:
        if not isinstance(item,Observation) or item.status not in acceptable:
            continue
        lines.append(f"{item.key.replace('_',' ').title()}: "
                     f"{item.status.upper()} · {item.detail}")
    lines.append("No hardware was activated, no files were repaired, and no service was restarted.")
    return "\n".join(lines)
