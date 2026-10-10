#!/usr/bin/env python3
"""Spider OS single owner-requested upgrade transaction.

One preflight, one backup/manifest, one group of file replacements and one
rollback. Never performs remote login, changes boot/encryption, modifies HOME
documents, reinstalls Kali/Studio/Media, or starts the webcam. Local unknown
customizations block the ENTIRE installation before the first write.
"""
import argparse
import ast
from dataclasses import dataclass
import getpass
import hashlib
import json
import os
from pathlib import Path
import pwd
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INSTALL_ROOT = Path('/usr/local/lib/spider-os')
UNIT_ROOT = Path('/usr/lib/systemd/user')
BACKUP_PREFIX = 'spider-batch-'
BASELINES = (
    'ac26340407837e7c2e0404b49f9a86d26cff5cc9',  # desktop
    'eec8e47c128a2f796ff5d16d549f8a2b105e32f8',  # Author
    '241922a1ad2157c316282166a3b812b8cf687768',  # OneDrive/portrait
    '6370ebde7b79029603747968266ccaf79aa78c00',  # workspace name/model
    '83d692b4c3115a2f4edeed2730a77774c2b49364',  # camera
    'a20727cc3aff0f0e9e5c96e2249663c82c1e0e26',  # quiet sleep
    'd27b0fa48670b8e3efda9e0b410cc2096ea47675',  # selective Kali source #13
)

# Files only. No passwords, auth files, models, service state, databases,
# manuscripts, user preferences or original source documents are in this list.
APP_FILES = (
    'author/main.py', 'author/store.py', 'author/web_features.py',
    'author/speech.py', 'author/publishing.py',
    'the-web/shell/main.py', 'the-web/shell/volume_panel.py',
    'the-web/shell/quick_settings.py',
    'the-web/shell/appearance.py',
    'the-web/shell/gtk_compat.py',
    'the-web/shell/theme_sync_plan.py',
    'the-web/shell/window_overview.py',
    'the-web/shell/notification_center.py',
    'the-web/shell/notification_bridge.py', 'the-web/shell/notification_toast.py',
    'the-web/shell/status_tray.py',
    'the-web/shell/tray_panel.py',
    'the-web/shell/webbie_panel.py',
    'the-web/shell/webbie_camera.py', 'the-web/shell/webbie_faces.py',
    'the-web/shell/webbie_face_profiles_ui.py',
    'the-web/shell/webbie_vision_bridge.py',
    'the-web/overlay/webbie_face.py',
    'the-web/overlay/webbie-face-autostart.desktop',
    'webbie/agent/webbie.py', 'webbie/agent/kali_assistant.py', 'webbie/agent/vision_query.py',
    'webbie/agent/night_mode.py', 'webbie/agent/workspace_names.py',
    'webbie/brain/brain.py', 'system/onedrive.py',
    'kali-bay/bin/kali-bay', 'kali-bay/ui/kali_bay.py',
    'branding/webbie/webbie-face-v1.png',
    'branding/webbie/webbie-face-speaking-v1.png',
)
UNITS = ('webbie-onedrive.service', 'webbie-onedrive.timer')
MENU = ('webbie-face-sleep-tonight.desktop',
        'webbie-face-wake.desktop', 'webbie-onedrive-connect.desktop')


@dataclass(frozen=True)
class Item:
    source: Path
    target: Path
    uid: int = 0
    gid: int = 0
    mode: int = 0o644
    reference: str = ''  # relative source path for strict known-baseline checks


def sha256(path):
    checksum = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(131072), b''):
            checksum.update(chunk)
    return checksum.hexdigest()


def prepare_items(root=PROJECT_ROOT, install=INSTALL_ROOT, units=UNIT_ROOT,
                  home=None, uid=0, gid=0):
    if home is None:
        home = Path.home()
    root, install, units, home = map(Path, (root, install, units, home))
    found = []
    for relative in APP_FILES:
        mode = 0o755 if relative in (
            'the-web/shell/main.py', 'the-web/overlay/webbie_face.py',
            'system/onedrive.py', 'kali-bay/bin/kali-bay') else 0o644
        found.append(Item(root / relative, install / relative, mode=mode,
                          reference=relative))
    for unit in UNITS:
        found.append(Item(root / 'system/service' / unit,
                          units / unit, reference='system/service/' + unit))
    found.append(Item(root / 'the-web/overlay/webbie-face-autostart.desktop',
                      home / '.config/autostart/webbie-floating-face.desktop',
                      uid=uid, gid=gid, reference='the-web/overlay/webbie-face-autostart.desktop'))
    for name in MENU:
        found.append(Item(root / 'the-web/overlay/launchers' / name,
                          home / '.local/share/applications' / name, uid=uid, gid=gid,
                          reference='the-web/overlay/launchers/' + name))
    assert len({str(i.target) for i in found}) == len(found), 'Duplicate release target'
    return found


def safe_path(path):
    path = Path(path)
    # Fail closed if target or any existing ancestor below the root is symlinked.
    for parent in (path, *path.parents):
        if parent.is_symlink():
            return False
        if parent == parent.parent:
            break
    return True


def known_baseline(root, relative, observed_hash, refs=BASELINES):
    # Baselines are pinned git commits, never owner data or untrusted scripts.
    for ref in refs:
        try:
            response = subprocess.run(
                ['git', '-C', str(root), 'show', ref + ':' + relative],
                capture_output=True, timeout=8, check=False)
            if response.returncode == 0 and hashlib.sha256(response.stdout).hexdigest() == observed_hash:
                return True
        except (OSError, subprocess.TimeoutExpired):
            pass
    return False


def inspect(items, project_root=PROJECT_ROOT, refs=BASELINES, known_checker=known_baseline):
    results = []
    for item in items:
        src, dest = item.source, item.target
        if not src.is_file() or not safe_path(src):
            results.append((item, 'BLOCKED', 'missing or symlinked source')); continue
        if not safe_path(dest):
            results.append((item, 'BLOCKED', 'symlinked target or parent')); continue
        try:
            if src.suffix == '.py':
                ast.parse(src.read_text(encoding='utf-8'), filename=str(src))
            if src.suffix == '.json':
                json.loads(src.read_text(encoding='utf-8'))
        except (SyntaxError, UnicodeError, ValueError, OSError) as exc:
            results.append((item, 'BLOCKED', 'source parse: ' + str(exc)[:120])); continue
        if not dest.exists():
            results.append((item, 'ADD', 'not installed')); continue
        if not dest.is_file():
            results.append((item, 'BLOCKED', 'not a regular installed file')); continue
        if sha256(src) == sha256(dest):
            results.append((item, 'CURRENT', 'identical bytes')); continue
        if (item.reference and known_checker(project_root, item.reference,
                                             sha256(dest), refs)):
            results.append((item, 'UPGRADE', 'recognized source baseline')); continue
        results.append((item, 'BLOCKED', 'custom or unknown installed content; preserve it'))
    return results


def report(results):
    for item, result, reason in results:
        print(f'{result}: {item.target} ({reason})')
    allowed = not any(result == 'BLOCKED' for _, result, _ in results)
    print('PRE-FLIGHT PASS' if allowed else 'PRE-FLIGHT BLOCKED; no changes made')
    return allowed


def atomic_copy(src, dest, uid=0, gid=0, mode=0o644):
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not safe_path(dest):
        raise RuntimeError('Symlink appeared while staging: ' + str(dest))
    fd, temporary = tempfile.mkstemp(prefix='.spider-upgrade-', dir=dest.parent)
    try:
        with os.fdopen(fd, 'wb') as out, Path(src).open('rb') as stream:
            shutil.copyfileobj(stream, out)
            out.flush()
            os.fsync(out.fileno())
        os.chmod(temporary, mode)
        if os.geteuid() == 0:
            os.chown(temporary, uid, gid)
        os.replace(temporary, dest)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def apply(items, backup_root, project_root=PROJECT_ROOT,
          refs=BASELINES, known_checker=known_baseline):
    checks = inspect(items, project_root, refs, known_checker)
    if not report(checks):
        raise RuntimeError('No files were changed. Review blocked paths first.')
    changing = [(item, state) for item, state, _ in checks if state in ('ADD', 'UPGRADE')]
    if not changing:
        print('Already current; no installation necessary.')
        return None
    backup_root = Path(backup_root)
    if not safe_path(backup_root):
        raise RuntimeError('Unsafe backup root')
    backup_root.mkdir(parents=True, exist_ok=True)
    backup = backup_root / (BACKUP_PREFIX + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    backup.mkdir(mode=0o700)
    records = []
    for index, (item, action) in enumerate(changing):
        original = item.target
        prior = None
        if action == 'UPGRADE':
            prior = backup / f'original-{index:04d}'
            shutil.copy2(original, prior, follow_symlinks=False)
        st = original.stat() if action == 'UPGRADE' else None
        records.append({
            'index': index, 'target': str(original),
            'action': 'existing' if st else 'new',
            'expected': sha256(item.source),
            'prior': sha256(prior) if prior else None,
            'old_mode': stat.S_IMODE(st.st_mode) if st else None,
            'old_uid': st.st_uid if st else None, 'old_gid': st.st_gid if st else None,
        })
    manifest = backup / 'manifest.json'
    with manifest.open('x', encoding='utf-8') as output:
        json.dump({'version': 1, 'files': records}, output, indent=2)
        output.write('\n')
    manifest.chmod(0o600)
    applied = []
    try:
        # Recheck every target immediately before modifying anything.
        if not report(inspect(items, project_root, refs, known_checker)):
            raise RuntimeError('Target changed after backup; all changes cancelled')
        for item, action in changing:
            if not safe_path(item.target):
                raise RuntimeError('Target path changed: ' + str(item.target))
            atomic_copy(item.source, item.target, item.uid, item.gid, item.mode)
            applied.append(item.target)
        print('BATCH INSTALLED; backup:', backup)
        print('Webbie OneDrive sign-in remains optional. Save work and log out/in once after validation.')
        print('Only new application sources and launchers were written; no manuscripts, boot or services were restarted.')
        return backup
    except Exception:
        # A failure may occur after os.replace committed the current file but
        # before atomic_copy returned. Inspect all recorded destinations and
        # restore ONLY those whose hashes match the release's expected bytes.
        # Leave pre-existing, untouched files alone; stop on unfamiliar edits.
        touched = []
        for record in records:
            target = Path(record['target'])
            if target.is_file() and safe_path(target) and sha256(target) == record['expected']:
                touched.append(record)
        if touched:
            _restore(touched, backup, {str(i.target): i for i in items})
        raise


def _restore(records, backup, allowed, allow_missing=False):
    for record in records:
        target = record.get('target')
        if target not in allowed:
            raise RuntimeError('Unknown rollback target: ' + str(target))
        if not safe_path(target):
            raise RuntimeError('Unsafe rollback target: ' + str(target))
        expected = record.get('expected')
        if not isinstance(expected, str) or len(expected) != 64:
            raise RuntimeError('Invalid expected source hash')
        path = Path(target)
        if not path.is_file():
            if allow_missing: continue
            raise RuntimeError('Installed target missing: ' + target)
        if sha256(path) != expected:
            raise RuntimeError('Target modified since batch: ' + target)
    for record in reversed(records):
        target = Path(record['target'])
        if record['action'] == 'new':
            target.unlink()
            continue
        index = record['index']
        if type(index) is not int or index < 0 or index >= 10000:
            raise RuntimeError('Invalid rollback index')
        prior = backup / f'original-{index:04d}'
        if not prior.is_file() or prior.is_symlink() or sha256(prior) != record.get('prior'):
            raise RuntimeError('Original backup missing or corrupt')
        atomic_copy(prior, target, record['old_uid'], record['old_gid'],
                    record['old_mode'])


def rollback(items, backup, backup_root, dry_run=True):
    backup_root, backup = Path(backup_root), Path(backup)
    if (backup.parent != backup_root or not backup.name.startswith(BACKUP_PREFIX)
            or not safe_path(backup) or not (backup / 'manifest.json').is_file()
            or (backup / 'manifest.json').is_symlink()):
        raise RuntimeError('Select an exact Spider OS batch backup directory')
    manifest = json.loads((backup / 'manifest.json').read_text())
    if manifest.get('version') != 1 or not isinstance(manifest.get('files'), list):
        raise RuntimeError('Unrecognized rollback manifest')
    entries = manifest['files']
    allowed = {str(item.target): item for item in items}
    if len({rec.get('target') for rec in entries}) != len(entries):
        raise RuntimeError('Duplicate rollback destinations')
    # Validate ALL destinations, hashes and copies before restoring ANY file.
    for rec in entries:
        target = rec.get('target')
        if target not in allowed or not safe_path(target):
            raise RuntimeError('Unknown rollback destination')
        if rec.get('action') not in ('existing', 'new'):
            raise RuntimeError('Unknown rollback action')
        if not Path(target).is_file() or sha256(target) != rec.get('expected'):
            raise RuntimeError('Installed file was customized after upgrade: ' + str(target))
        if rec['action'] == 'existing':
            n = rec.get('index')
            if type(n) is not int or not (0 <= n < 10000):
                raise RuntimeError('Bad backup number')
            prior = backup / f'original-{n:04d}'
            if not prior.is_file() or prior.is_symlink() or sha256(prior) != rec.get('prior'):
                raise RuntimeError('Original file backup corrupt')
    if dry_run:
        print(f'ROLLBACK CHECK PASSED: {len(entries)} changes, no files modified.')
        return
    _restore(entries, backup, allowed)
    print('BATCH RESTORED. User documents, Ollama models and credentials unchanged.')


def user_info(for_apply=False):
    name = os.environ.get('SUDO_USER') or getpass.getuser()
    if for_apply and (os.geteuid() != 0 or not os.environ.get('SUDO_USER')
                      or os.environ['SUDO_USER'] == 'root'):
        raise RuntimeError('Run --apply/--rollback with sudo from your Spider OS account')
    user = pwd.getpwnam(name)
    return Path(user.pw_dir), user.pw_uid, user.pw_gid


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('check', 'apply', 'rollback-check', 'rollback'))
    parser.add_argument('backup', nargs='?', default=None)
    if argv is None:
        argv = sys.argv[1:]
    # Accept familiar --check/--apply flags while retaining a single mode.
    if argv and argv[0] in ('--check', '--apply', '--rollback-check', '--rollback'):
        argv = [argv[0][2:], *argv[1:]]
    args = parser.parse_args(argv)
    try:
        active = args.action in ('apply', 'rollback')
        home, uid, gid = user_info(for_apply=active)
        items = prepare_items(home=home, uid=uid, gid=gid)
        backup_root = INSTALL_ROOT / 'upgrade-backups'
        if args.action == 'check':
            return 0 if report(inspect(items)) else 3
        if args.action == 'apply':
            apply(items, backup_root)
            return 0
        if not args.backup:
            parser.error('Rollback requires the exact backup path from the installation receipt.')
        rollback(items, args.backup, backup_root, dry_run=args.action == 'rollback-check')
        return 0
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as error:
        print('Spider OS batch stopped: ' + str(error), file=sys.stderr)
        return 3


if __name__ == '__main__':
    raise SystemExit(main())
