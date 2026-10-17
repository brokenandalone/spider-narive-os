#!/usr/bin/env python3
"""Read-only owner-PC acceptance preflight; never declares manual checks passed."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request


MANUAL = [
    'Choose The Web (X11) at login; check Start, clock and taskbar.',
    'Switch workspace tabs and external app windows; check every monitor.',
    'Edit and restart Author/School; confirm saved work and wallpaper choices.',
    'Lock, try a wrong password, unlock, then log out normally.',
    'Play/Pause/seek a local song and movie in Media Center.',
    'Prepare an unsupported local movie; check cancellation and replay.',
    'Check visualizer, microphone/mix and broadcast stop/start.',
    'Check desktop-loading and boot splash transitions.',
]


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def audit_wallpapers(root):
    """Return counts; reject bad hashes, unsafe paths and malformed assignments."""
    root = Path(root).resolve()
    data = json.loads((root / 'branding/wallpapers/collection.json').read_text())
    entries = data['wallpapers']
    valid = {'default', 'webbie', 'forage', 'deep-forage', 'studio', 'author',
             'art-lab', 'dev-bay', 'study', 'media', 'communications', 'kali-bay',
             'system', 'recovery', 'games'}
    counts = {}
    ids = set()
    for entry in entries:
        image = (root / entry['file']).resolve()
        if not image.is_relative_to(root) or not image.is_file():
            raise ValueError('missing or unsafe artwork file')
        if entry['workspace'] not in valid or entry['id'] in ids:
            raise ValueError('invalid workspace assignment or duplicate ID')
        if digest(image) != entry['sha256']:
            raise ValueError('artwork checksum mismatch')
        ids.add(entry['id'])
        counts[entry['workspace']] = counts.get(entry['workspace'], 0) + 1
    for workspace, ident in data.get('new_workspace_defaults', {}).items():
        if not any(e['id'] == ident and e['workspace'] == workspace for e in entries):
            raise ValueError('default wallpaper assigned to the wrong workspace')
    return len(entries), counts


def command(args):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=4)
        return r.returncode == 0, r.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return False, ''


def get_json(url):
    # Local services must not be sent through a configured network proxy.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(url, timeout=3) as response:
        raw = response.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError('oversized local response')
    return json.loads(raw)


def verify(root, system_root, media_root, reference, live=True):
    root, system_root, media_root = map(Path, (root, system_root, media_root))
    checks = []
    def add(name, ok, detail, required=True):
        checks.append({'check': name, 'status': 'PASS' if ok else 'FAIL' if required else 'WARN', 'detail': detail})
    required = ['the-web/shell/main.py', 'the-web/shell/desktop.py',
                'the-web/shell/workspaces.py', 'the-web/shell/app_catalog.py',
                'the-web/shell/wallpapers.py', 'author/main.py', 'studio/main.py',
                'study/study.py', 'system/apps.py']
    add('Desktop and native workspace source', all((root / p).is_file() for p in required),
        'Required desktop, Author, Studio and School files present.' if all((root / p).is_file() for p in required) else 'Install the desktop and corresponding workspace upgrades.')
    for name, relative in [('Webbie workspace', 'webbie/ui/webbie-ui.py'),
                           ('Forage workspace', 'forage/forage.py'),
                           ('Deep Forage workspace', 'forage/deep-forage/deep_forage.py'),
                           ('Kali Bay workspace', 'kali-bay/ui/kali_bay.py'),
                           ('Guardian', 'system/bin/spider-guardian'),
                           ('Vault', 'system/bin/spider-vault')]:
        add(name, (root / relative).is_file(), 'Source or launcher present; interactive behavior needs owner-PC verification.')
    entry = system_root / 'usr/share/xsessions/the-web.desktop'
    try:
        ok = 'Exec=/usr/local/bin/the-web-session' in entry.read_text().splitlines()
    except OSError:
        ok = False
    add('Login session entry', ok, 'The Web session registered.' if ok else 'The Web login session is missing or outdated.')
    add('Session launcher', os.access(system_root / 'usr/local/bin/the-web-session', os.X_OK), 'Executable desktop launcher required.')
    add('Old app entry removed', not (system_root / 'usr/share/applications/the-web.desktop').exists(), 'The Web belongs in the login chooser.')
    try:
        count, counts = audit_wallpapers(root)
        add('Wallpaper collection', count == 59, f'{count} verified artwork files; workspace assignments and default mappings checked.')
    except (OSError, ValueError, KeyError, TypeError):
        add('Wallpaper collection', False, 'Collection is incomplete, malformed or has mismatched files; reinstall the desktop collection.')
    originals = ['art-lab', 'dev-bay', 'forage', 'kali-bay', 'media', 'recovery', 'studio', 'study', 'system']
    add('Original backgrounds', all((root / 'branding/workspaces' / (w + '.png')).is_file() for w in originals), 'Original workspace backgrounds retained.')
    archive = media_root / 'resources/app.asar'
    try:
        expected = json.loads(Path(reference).read_text())
        ok = digest(archive) == expected['archiveSha256']
        add('Media Center playback build', ok, 'Installed archive matches the supplied tested build.' if ok else 'Installed archive differs from this tested build; a newer build is also possible.', required=False)
    except (OSError, ValueError, KeyError, TypeError):
        add('Media Center playback build', False, 'Archive or reference metadata unavailable; installation is unconfirmed.', required=False)
    if live:
        for exe in ['startplasma-x11', 'wmctrl', 'dbus-send', 'systemctl', 'ffmpeg']:
            add('Command: ' + exe, shutil.which(exe) is not None, 'Available.' if shutil.which(exe) else 'Missing dependency.')
        ok, _ = command([sys.executable, '-c', 'from PyQt5.QtWidgets import QApplication'])
        add('System PyQt5', ok, 'Available to this Python interpreter.' if ok else 'System PyQt5 is unavailable.')
        add('Current X11 desktop session', os.environ.get('XDG_SESSION_TYPE') == 'x11' and os.environ.get('SPIDER_THE_WEB_SESSION') == '1', 'Run from a terminal opened in The Web (X11) to verify the active session.', required=False)
        for name, destination, object_path in [('KWin', 'org.kde.KWin', '/KWin'), ('Secure locker', 'org.freedesktop.ScreenSaver', '/ScreenSaver')]:
            ok, _ = command(['dbus-send', '--session', '--print-reply', '--reply-timeout=2000', '--dest=' + destination, object_path, 'org.freedesktop.DBus.Peer.Ping'])
            add(name, ok, 'Session endpoint responds; interactive behavior still requires a manual check.', required=False)
        for name, unit, user in [('Webbie', 'webbie.service', True), ('Ollama', 'ollama.service', False), ('AI DJ', 'spider-ai-dj.service', True)]:
            args = ['systemctl'] + (['--user'] if user else []) + ['is-active', unit]
            ok, _ = command(args)
            add(name + ' service', ok, 'Active.' if ok else 'Inactive or unavailable; inspect this service on the installed PC.', required=False)
        for name, url, key in [('Ollama API', 'http://127.0.0.1:11434/api/tags', 'models'), ('AI DJ health', 'http://127.0.0.1:9876/health', 'ok')]:
            try:
                payload = get_json(url)
                ok = isinstance(payload, dict) and (isinstance(payload.get(key), list) if key == 'models' else payload.get(key) is True)
            except (OSError, ValueError):
                ok = False
            add(name, ok, 'Local endpoint responds.' if ok else 'Local endpoint failed its health check.', required=False)
    return {'checks': checks, 'manualChecksPending': MANUAL, 'installedAcceptanceComplete': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', default='/usr/local/lib/spider-os')
    p.add_argument('--system-root', default='/')
    p.add_argument('--media-root', default='/opt/spider-media-center')
    p.add_argument('--reference', default=str(Path(__file__).with_name('media-build.json')))
    p.add_argument('--files-only', action='store_true', help='Check a staged filesystem without querying services.')
    p.add_argument('--json', action='store_true', help='Print a structured report to standard output.')
    args = p.parse_args()
    if os.geteuid() == 0 and not args.files_only:
        p.error('Run without sudo from your normal desktop account, so user services and the session bus are checked correctly.')
    report = verify(args.root, args.system_root, args.media_root, args.reference, live=not args.files_only)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for c in report['checks']:
            print(f"{c['status']}: {c['check']} — {c['detail']}")
        print('\nManual checks still pending:')
        for item in MANUAL:
            print('[ ] ' + item)
        print('\nThis report does not establish successful login, unlock or playback.')
    return 1 if any(c['status'] == 'FAIL' for c in report['checks']) else 0


if __name__ == '__main__':
    raise SystemExit(main())
