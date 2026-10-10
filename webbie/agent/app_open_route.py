"""Read-only command recognition and local request to the approved operator GUI.

The agent has no access to grant creation. Voice app launch is ONLY a request
to the trusted Webbie panel for the owner-chosen application, and is denied
when the panel or explicit grant is unavailable. No PyQt dependency here.
"""
import os
from pathlib import Path
import re
import socket
import stat
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'the-web/shell'))


def installed_app_request(command, applications=None, sender=None):
    phrase = re.sub(r'\s+', ' ', str(command or '')).strip()
    match = re.fullmatch(
        r'(?:please\s+)?(?:open|launch|start)\s+(.+?)', phrase, flags=re.I)
    if not match:
        return None
    requested_name = match.group(1).strip(' ,.!?').casefold()
    if not requested_name:
        return None
    if applications is None:
        from app_catalog import discover_apps
        applications = discover_apps()
    exact = [app for app in applications
             if (app.name.casefold() == requested_name or
                 app.desktop_id.casefold().removesuffix('.desktop') == requested_name)]
    if not exact:
        # Return None so established Spider OS workspace commands still work.
        return None
    if len(exact) != 1:
        return 'Multiple programs have that name. Choose one in Computer Control.'
    return (sender or request_approved_app)(exact[0].desktop_id)


def request_approved_app(desktop_id):
    import re
    if not isinstance(desktop_id, str) or not re.fullmatch(
            r'[A-Za-z0-9][A-Za-z0-9_.+-]{0,199}\.desktop', desktop_id):
        return 'The program ID is not supported.'
    runtime = Path(os.environ.get(
        'XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}')) / 'spider-os'
    path = runtime / 'webbie-operator.sock'
    if (runtime.is_symlink() or path.is_symlink() or
            not path.exists() or not stat.S_ISSOCK(path.stat().st_mode)):
        return 'Open Webbie Computer Control and authorize this program first.'
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(3)
            client.connect(str(path))
            client.sendall(('OPEN:' + desktop_id).encode('utf-8'))
            result = client.recv(401)
        return (result[:400].decode('utf-8', 'replace')
                if result and len(result) <= 400 else
                'The computer control request was not completed.')
    except OSError:
        return 'The computer control panel is not currently available.'
