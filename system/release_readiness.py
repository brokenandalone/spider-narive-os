#!/usr/bin/env python3
"""Read-only Spider OS upgrade readiness report. No camera activation or cloud login."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import hashlib
import importlib.util

def read_cmd(command, timeout=4):
    try:
        r = subprocess.run(command, text=True, capture_output=True, timeout=timeout, check=False)
        return r.stdout.strip() if r.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None

def digest(path):
    try:
        h = hashlib.sha256()
        with Path(path).open('rb') as f:
            for part in iter(lambda: f.read(131072), b''):
                h.update(part)
        return h.hexdigest()
    except OSError:
        return None

def inspect(home=None, install=None, env=None, runner=read_cmd):
    home = Path(home) if home is not None else Path.home()
    install = Path(install) if install is not None else Path('/usr/local/lib/spider-os')
    env = dict(os.environ if env is None else env)
    spider_config = home / '.config/spider-os'
    originals = list((home / 'Documents').glob('**/*.docx')) if (home / 'Documents').is_dir() else []
    # Count without reading document contents, and do not scan the whole HOME.
    author = install / 'author'
    agent = install / 'webbie/agent/webbie.py'
    shell = install / 'the-web/shell/main.py'
    data = {
        'display': {'session_type':env.get('XDG_SESSION_TYPE','unknown'),
                    'desktop':env.get('DESKTOP_SESSION','unknown'),
                    'x11_eligible':env.get('XDG_SESSION_TYPE','').lower() == 'x11'},
        'installed_sources': {
            'webbie_agent': {'present': agent.is_file(), 'sha256':digest(agent)},
            'web_shell': {'present': shell.is_file(), 'sha256':digest(shell)},
            'author_code_present':author.is_dir(),
        },
        'dependencies': {name: bool(shutil.which(name)) for name in
                         ('python3', 'git', 'ffmpeg', 'xprop', 'rclone', 'ollama',
                          'wpctl', 'nmcli', 'bluetoothctl', 'brightnessctl',
                          'systemsettings')},
        'optional_desktop_support': {
            'dbus_next_notifications': importlib.util.find_spec('dbus_next') is not None,
            'note': 'Missing optional tools disable individual controls, not the resident Webbie voice service.',
        },
        'ollama_models': runner(['ollama','list']) if shutil.which('ollama') else None,
        'audio_services': {name:runner(['systemctl','--user','is-active',name]) for name in
                           ('webbie.service','ollama.service','ai-dj.service','pipewire.service','wireplumber.service')}
                          if shutil.which('systemctl') else {},
        'author_originals': {'documents_tree_docx_count':len(originals),
                             'backup_verified':False},
        'disk': {},
        'one_drive': {'oauth_not_attempted':True,
                      'config_exists':(spider_config/'onedrive.json').is_file()},
        'camera': {'not_opened':True, 'device_nodes': sorted(str(p) for p in Path('/dev').glob('video[0-9]*'))},
    }
    try:
        st = shutil.disk_usage(install if install.exists() else home)
        data['disk']={'free_bytes':st.free,'total_bytes':st.total}
    except OSError:
        pass
    blockers=[]
    if not data['display']['x11_eligible']:blockers.append('X11 session not confirmed')
    if not agent.is_file():blockers.append('Existing Webbie agent not found')
    if not shell.is_file():blockers.append('Existing The Web shell not found')
    if not data['dependencies']['ffmpeg']:blockers.append('ffmpeg missing for opt-in camera')
    blockers.append('Independent Author DB and original DOCX backups require owner verification')
    data['manual_release_blockers']=blockers
    return data

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json',action='store_true')
    args=parser.parse_args(argv)
    data=inspect()
    if args.json:
        print(json.dumps(data,indent=2))
    else:
        print('SPIDER OS | READ-ONLY RELEASE READINESS')
        for section in ('display','installed_sources','dependencies',
                        'optional_desktop_support','audio_services',
                        'author_originals','disk','one_drive','camera'):
            print(section+': '+json.dumps(data[section]))
        print('Remaining checks:')
        for issue in data['manual_release_blockers']:print(' - '+issue)
        print('No files, services, camera permissions, credentials or boot settings changed.')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
