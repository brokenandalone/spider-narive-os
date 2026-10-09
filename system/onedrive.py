#!/usr/bin/env python3
"""Optional OneDrive workspace for Webbie. Local-first; never blocks her agent.

The user signs in interactively through rclone config. Nothing is uploaded until
a named OneDrive remote exists and the user finishes Connect. Only explicit
files in Documents/Spider OS/Webbie/OneDrive are eligible for background copies.
Webbie conversations, system state, models and manuscripts are never scanned.
"""
import argparse
import configparser
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

CONFIG = Path.home() / '.config/spider-os/onedrive.json'
RCLONE = Path.home() / '.config/rclone/rclone.conf'
FOLDER = Path.home() / 'Documents/Spider OS/Webbie/OneDrive'
REMOTE_NAME = 'webbie_onedrive'
REMOTE_FOLDER = 'Spider OS/Webbie'


def load_config(config=CONFIG):
    try:
        data = json.loads(Path(config).read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def read_remote_type(config=RCLONE, name=REMOTE_NAME):
    """Read *only* the remote type; never print or store OAuth credentials."""
    config = Path(config)
    if not config.is_file() or config.is_symlink():
        return None
    parser = configparser.RawConfigParser(interpolation=None)
    try:
        parser.read(config, encoding='utf-8')
        return parser.get(name, 'type') if parser.has_section(name) else None
    except (OSError, configparser.Error):
        return None


def status(config=CONFIG, rclone_config=RCLONE, folder=FOLDER):
    optin = load_config(config).get('enabled') is True
    remote = read_remote_type(rclone_config)
    installed = shutil.which('rclone') is not None
    if not optin:
        label = 'Not connected. Webbie continues locally.'
    elif not installed:
        label = 'Paused: rclone is unavailable. Webbie continues locally.'
    elif remote != 'onedrive':
        label = 'Paused: OneDrive authorization unavailable. Webbie continues locally.'
    else:
        label = ('OneDrive account configured. Background sync is enabled; '
                 'the Microsoft session has not been live-tested here.')
    return {'connected': bool(optin and remote == 'onedrive' and installed),
            'enabled': optin, 'remoteConfigured': remote == 'onedrive',
            'rcloneAvailable': installed, 'status': label,
            'syncFolderExists': Path(folder).is_dir()}


def enable(config=CONFIG, rclone_config=RCLONE, folder=FOLDER):
    if read_remote_type(rclone_config) != 'onedrive':
        raise ValueError('Create the named Microsoft OneDrive remote first.')
    folder = Path(folder)
    if folder.is_symlink():
        raise ValueError('Refusing to sync a symbolic-link workspace folder')
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    destination = Path(config)
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix='.onedrive-', dir=destination.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as output:
            json.dump({'enabled': True, 'remote': REMOTE_NAME}, output)
            output.write('\n')
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def disable(config=CONFIG):
    destination = Path(config)
    if not destination.exists(): return
    data = load_config(destination)
    data['enabled'] = False
    fd, temporary = tempfile.mkstemp(prefix='.onedrive-', dir=destination.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as output:
            json.dump(data, output)
            output.write('\n')
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def sync_folder(config=CONFIG, rclone_config=RCLONE, folder=FOLDER, runner=subprocess.run):
    """Bounded optional upload, never delete or overwrite a cloud file.

    Use uniquely named/versioned documents for updates; no raw Webbie state is
    automatically uploaded. Network errors return failure only to timer, never
    reach or block the Webbie resident AI service.
    """
    info = status(config, rclone_config, folder)
    if not info['connected']:
        return 'offline'
    folder = Path(folder)
    if not folder.is_dir() or folder.is_symlink(): return 'unsafe workspace'
    try:
        # Never upload links that escape the selected folder.
        if not any(entry.is_file() and not entry.is_symlink() for entry in folder.rglob('*')):
            return 'empty'
        options = ['rclone', '--config', str(rclone_config), 'copy',
                   str(folder), REMOTE_NAME + ':' + REMOTE_FOLDER,
                   '--immutable', '--max-duration', '2m',
                   '--transfers', '1', '--checkers', '2',
                   '--exclude', '**/.**', '--exclude', '*.key',
                   '--exclude', '*.pem', '--exclude', '*credentials*',
                   '--exclude', '*token*',
                   '--skip-links']
        outcome = runner(options, capture_output=True, text=True, timeout=145,
                         stdin=subprocess.DEVNULL)
        return 'copied' if outcome.returncode == 0 else 'retry later'
    except (OSError, subprocess.TimeoutExpired):
        return 'retry later'


def connect():
    if not shutil.which('rclone'):
        print('rclone is not installed. Install it first; Webbie still works offline.')
        return 2
    print('OPTIONAL WEBBIE ONEDRIVE SIGN-IN')
    print('In rclone config: choose n (new remote), name it "webbie_onedrive",')
    print('select Microsoft OneDrive, then complete the browser Microsoft sign-in.')
    print('Use a separate Webbie folder; Webbie never syncs the whole OneDrive.')
    print('Close/quit the rclone menu when finished. No login deadline.')
    print('rclone stores its OAuth configuration locally; protect your user account.')
    try:
        result = subprocess.run(['rclone', 'config'], check=False)
    except OSError:
        return 2
    if result.returncode or read_remote_type() != 'onedrive':
        print('Not connected. Webbie continues working locally.')
        return 1
    enable()
    print('OneDrive configuration saved. Workspace folder:', FOLDER)
    print('Cloud access is verified by an actual background copy, not config alone.')
    print('Background sync is optional and never blocks Webbie.')
    # Triggering a timer asynchronously never makes sign-in wait for the cloud.
    if shutil.which('systemctl'):
        subprocess.Popen(['systemctl', '--user', 'start', '--no-block',
                          'webbie-onedrive.service'], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('status', 'connect', 'enable', 'pause',
                                           'sync', 'folder'))
    args = parser.parse_args(argv)
    if args.action == 'status':
        print(status()['status']); return 0
    if args.action == 'connect': return connect()
    if args.action == 'enable':
        try: enable()
        except ValueError as error:
            print(str(error)); return 2
        return 0
    if args.action == 'pause':
        disable(); print('OneDrive paused; Webbie continues locally.'); return 0
    if args.action == 'folder':
        print(FOLDER); return 0
    if args.action == 'sync':
        result = sync_folder()
        # Scheduled background failure is quiet and never affects voice service.
        return 0 if result in ('offline', 'empty', 'copied') else 1
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
