"""Owner-approved, privacy-minimal diagnostic snapshot for Spider OS.

This creates an in-memory JSON string only when requested. It never reads
clipboard, windows, files, URLs, manuscripts, speech, credentials, or logs.
"""
import json
import math

MAX_TABS = 32
MAX_SECONDS = 3600.0


def build_safe_report(workspaces, opened, active, health=(), load_seconds=None,
                      restore=None, applications=0, open_windows=0, safe_mode=False):
    allowed = set(workspaces)
    names = [name for name in list(opened)[:MAX_TABS]
             if isinstance(name, str) and name in allowed]
    if 'default' not in names:
        names.insert(0, 'default')
    delays = {}
    for ident, value in (load_seconds or {}).items():
        if ident not in allowed or not isinstance(value, (float, int)) or isinstance(value, bool):
            continue
        if math.isfinite(value) and 0 <= value <= MAX_SECONDS:
            delays[ident] = round(value, 3)
    statuses = {}
    for item in health:
        ident = getattr(item, 'ident', None)
        status = getattr(item, 'status', None)
        if ident in allowed and status in ('open', 'available', 'needs-attention', 'missing'):
            statuses[ident] = status
    progress = None
    if isinstance(restore, dict):
        progress = {
            'processed': min(max(int(restore.get('processed', 0)), 0), MAX_TABS),
            'remaining': min(max(int(restore.get('remaining', 0)), 0), MAX_TABS),
            'paused': restore.get('paused') is True,
            'skipped': [name for name in restore.get('skipped', ())
                        if isinstance(name, str) and name in allowed][:MAX_TABS]
        }
    return {
        'schema': 'spider-web-safe-diagnostics-v1',
        'active_workspace': active if active in allowed else 'default',
        'open_workspaces': names,
        'workspace_health': statuses,
        'load_seconds': delays,
        'restoration': progress,
        'safe_mode': bool(safe_mode),
        'installed_app_count': min(max(int(applications), 0), 100000),
        'visible_window_count': min(max(int(open_windows), 0), 10000)
    }


def report_text(report):
    return json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + '\n'
