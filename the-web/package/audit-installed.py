#!/usr/bin/env python3
"""Read-only Spider OS installation inventory, designed for owner-PC handoff.

Reports component presence and record COUNTS, not manuscript/record contents,
file names, microphone data, host names, account names or secrets. It does not
start/restart services, run apt, enter Kali, change boot settings, or write files.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import sqlite3
import subprocess
from urllib.parse import quote


SERVICES = (
    ('Webbie', 'webbie.service', True),
    ('Ollama', 'ollama.service', False),
    ('AI DJ', 'spider-ai-dj.service', True),
    ('PipeWire', 'pipewire.service', True),
    ('WirePlumber', 'wireplumber.service', True),
)


def bounded_command(arguments, timeout=3):
    try:
        result = subprocess.run(
            arguments, capture_output=True, text=True, timeout=timeout,
            stdin=subprocess.DEVNULL, check=False
        )
        return result.returncode, result.stdout.strip()[:2048]
    except (OSError, subprocess.TimeoutExpired):
        return None, ''


def file_state(path):
    path = Path(path)
    try:
        if path.is_file(): return 'present'
        if path.is_dir(): return 'directory'
        if path.is_symlink(): return 'broken link'
        return 'not found'
    except OSError:
        return 'unavailable'


def readonly_counts(database, tables):
    """Never open a mutable SQLite connection or create a new database.

    immutable=1 avoids WAL/SHM side effects; counts can lag uncheckpointed edits.
    Table names are fixed constants supplied by the code, never user input.
    """
    if file_state(database) != 'present':
        return {'status': 'not found', 'counts': {}}
    uri = 'file:' + quote(str(Path(database).resolve()), safe='/') + '?mode=ro&immutable=1'
    try:
        with sqlite3.connect(uri, uri=True, timeout=2) as connection:
            connection.execute('PRAGMA query_only=ON')
            counts = {}
            for table in tables:
                try:
                    counts[table] = int(connection.execute(
                        'SELECT COUNT(*) FROM "' + table + '"'
                    ).fetchone()[0])
                except sqlite3.DatabaseError:
                    counts[table] = None
        return {'status': 'readable', 'counts': counts}
    except (OSError, sqlite3.DatabaseError):
        return {'status': 'unavailable (locked, corrupt or unsupported)', 'counts': {}}


def count_originals(directory):
    """Count only regular DOCX, do not read content or return private filenames."""
    try:
        return sum(1 for entry in Path(directory).iterdir()
                   if entry.is_file() and not entry.is_symlink()
                   and entry.suffix.lower() == '.docx')
    except OSError:
        return None


def services_snapshot():
    rows = {}
    for label, unit, is_user in SERVICES:
        args = ['systemctl'] + (['--user'] if is_user else []) + [
            'show', unit, '--property=LoadState,ActiveState'
        ]
        code, output = bounded_command(args)
        values = dict(line.split('=', 1) for line in output.splitlines() if '=' in line)
        if code is None or code != 0:
            rows[label] = 'unavailable'
        elif values.get('LoadState') == 'not-found':
            rows[label] = 'not installed'
        else:
            rows[label] = values.get('ActiveState', 'unknown')
    return rows


def kali_snapshot():
    """Podman inspect does not start or create the existing Distrobox container."""
    code, _ = bounded_command(['podman', 'container', 'exists', 'kali-bay'])
    if code is None: return 'podman unavailable'
    if code != 0: return 'container not found'
    code, state = bounded_command(['podman', 'inspect', '--format', '{{.State.Status}}', 'kali-bay'])
    return state if code == 0 and state in {
        'created', 'running', 'paused', 'restarting', 'removing', 'exited', 'dead',
    } else 'status unavailable'


def receipt_state(installed):
    path = Path(installed) / 'the-web/install-receipt.json'
    if file_state(path) != 'present':
        return {'status': 'not found (older desktop may still be installed)'}
    try:
        if path.stat().st_size > 65536:
            raise ValueError('receipt too large')
        data = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            raise ValueError('invalid receipt')
        # Never trust extra paths, keys, or private fields from local JSON.
        return {'status': 'present', 'version': str(data.get('version', 'unknown'))[:100],
                'installedAt': str(data.get('installedAt', 'unknown'))[:100]}
    except (OSError, UnicodeError, ValueError):
        return {'status': 'unreadable'}


def audit(home=None, installed='/usr/local/lib/spider-os', media='/opt/spider-media-center',
          system='/', include_live=True):
    home = Path(home) if home is not None else Path.home()
    installed, media, system = Path(installed), Path(media), Path(system)
    author = home / 'Documents/Spider OS/Author'
    original = author / 'Originals'
    extraction = home / 'Downloads/Spider-Author-Import/Broken-World-Author-Library.json'

    inventory = {
        'reportType': 'Spider OS read-only installed-system inventory',
        'writesPerformed': False,
        'manualTestingStillRequired': True,
        'operatingSystem': {
            'kernel': platform.release(),
            'sessionType': os.environ.get('XDG_SESSION_TYPE', 'unknown'),
            'theWebSession': os.environ.get('SPIDER_THE_WEB_SESSION') == '1',
        },
        'desktop': {
            'sessionEntry': file_state(system / 'usr/share/xsessions/the-web.desktop'),
            'shell': file_state(installed / 'the-web/shell/main.py'),
            'windowControls': file_state(installed / 'the-web/shell/desktop.py'),
            'buildReceipt': receipt_state(installed),
            'wallpaperCollection': file_state(installed / 'branding/wallpapers/collection.json'),
        },
        'content': {
            'authorDatabase': readonly_counts(author / 'library.sqlite3',
                                               ('books', 'chapters', 'snapshots', 'imported_sources')),
            'originalDocxCount': count_originals(original),
            'extractedBrokenWorldBundle': file_state(extraction),
            'schoolDatabase': readonly_counts(home / '.local/share/spider-os/study/study.db',
                                              ('courses', 'assignments')),
            'schoolDocuments': file_state(home / 'Documents/Spider OS/Study'),
            'studioProjects': file_state(home / 'Documents/Spider Studio'),
            'musicFolder': file_state(home / 'Music'),
            'researchFolder': file_state(home / 'Documents/Spider OS/Research'),
        },
        'installedApplications': {
            'kaliManager': file_state(installed / 'kali-bay/bin/kali-bay'),
            'kaliInterface': file_state(installed / 'kali-bay/ui/kali_bay.py'),
            'mediaCenterArchive': file_state(media / 'resources/app.asar'),
            'webbieAgent': file_state(installed / 'webbie/agent/webbie.py'),
        },
        'boot': {
            'grubConfiguration': file_state(system / 'boot/grub/grub.cfg'),
            'spiderRootEfiLoader': file_state(system / 'boot/efi/EFI/SpiderRoot/grubx64.efi'),
            'note': 'Inventory only: does not verify boot integrity or change GRUB, encryption or initramfs.',
        },
        'limitations': [
            'An installed component may still have runtime bugs.',
            'SQLite uses an immutable read-only view; counts can lag uncheckpointed writes.',
            'Only known workspace paths are checked; missing paths do not imply lost files.',
            'No private text, titles, original filenames or audio are read into the report.',
        ],
    }
    if include_live:
        inventory['services'] = services_snapshot()
        inventory['kaliContainer'] = kali_snapshot()
    return inventory


def display(report):
    def state(value):
        if isinstance(value, dict):
            if 'counts' in value:
                counts = ', '.join(f'{key}={count if count is not None else "unknown"}'
                                   for key, count in value['counts'].items())
                return value['status'] + (f' ({counts})' if counts else '')
            if 'status' in value:
                return value['status'] + (f" / {value['version']}" if 'version' in value else '')
        return str(value)

    print('SPIDER OS | READ-ONLY INSTALLED SYSTEM AUDIT')
    for section in ('desktop', 'content', 'installedApplications', 'boot'):
        print('\n' + section.upper())
        for label, value in report[section].items():
            if label == 'note': continue
            print(f'  {label}: {state(value)}')
    if 'services' in report:
        print('\nSERVICES')
        for label, value in report['services'].items():
            print(f'  {label}: {value}')
        print('  Kali container: ' + report['kaliContainer'])
    print('\nNo configuration or files were changed. Missing components need review, not automatic reinstall.')
    print('Private manuscript text, titles, account information and filenames were not displayed.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', action='store_true', help='Emit a structured privacy-limited report')
    parser.add_argument('--files-only', action='store_true',
                        help='Do not contact user/system services or Podman')
    parser.add_argument('--home', default=None, help=argparse.SUPPRESS)
    parser.add_argument('--installed-root', default='/usr/local/lib/spider-os',
                        help=argparse.SUPPRESS)
    parser.add_argument('--system-root', default='/', help=argparse.SUPPRESS)
    parser.add_argument('--media-root', default='/opt/spider-media-center',
                        help=argparse.SUPPRESS)
    args = parser.parse_args()
    if os.geteuid() == 0 and not args.files_only:
        parser.error('Run as your normal Spider OS desktop user, without sudo.')
    report = audit(home=args.home, installed=args.installed_root,
                   system=args.system_root, media=args.media_root,
                   include_live=not args.files_only)
    if args.json: print(json.dumps(report, indent=2))
    else: display(report)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
