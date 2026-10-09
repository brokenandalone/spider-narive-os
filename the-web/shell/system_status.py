"""Bounded read-only diagnostics. No service, package or configuration changes."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import os
from pathlib import Path
import platform
import shutil
import subprocess
from build_info import inspect_receipt
from audio_controls import output_level

SERVICES = [('Webbie', 'webbie.service', True), ('Ollama', 'ollama.service', False),
            ('AI DJ', 'spider-ai-dj.service', True), ('Spider Core', 'spider-os.service', False),
            ('PipeWire', 'pipewire.service', True), ('WirePlumber', 'wireplumber.service', True)]


def run(arguments):
    try:
        result = subprocess.run(arguments, capture_output=True, text=True, timeout=2)
        return result.returncode, result.stdout[:16384]
    except (OSError, subprocess.TimeoutExpired):
        return None, ''


def service_status(service):
    name, unit, user = service
    code, text = run(['systemctl'] + (['--user'] if user else []) +
                     ['show', unit, '--property=LoadState,ActiveState,SubState,UnitFileState'])
    props = dict(line.split('=', 1) for line in text.splitlines() if '=' in line)
    state = props.get('ActiveState', 'unavailable') if code == 0 else 'unavailable'
    if props.get('LoadState') == 'not-found':
        state = 'not installed'
    return name, unit, state, props.get('SubState', ''), props.get('UnitFileState', '')


def service_states():
    with ThreadPoolExecutor(max_workers=6) as pool:
        return list(pool.map(service_status, SERVICES))


def backup_rows(root, media_root):
    rows = []
    for directory, prefix, kind in [(Path(root) / 'upgrade-backups', 'the-web-', 'Desktop'),
                                   (Path(media_root) / 'resources', 'app.asar.before-', 'Media Center')]:
        try:
            for index, candidate in enumerate(directory.iterdir()):
                if index >= 500: break
                if candidate.name.startswith(prefix) and not candidate.is_symlink():
                    rows.append((kind, candidate.name, str(candidate)))
        except OSError:
            continue
    return sorted(rows, key=lambda row: row[1], reverse=True)[:50]


def file_snapshot(root, home=None, media_root='/opt/spider-media-center'):
    home = Path(home or Path.home())
    overview = [('Kernel', platform.release()), ('Architecture', platform.machine()),
                ('Logical CPUs', str(os.cpu_count() or 'Unknown')),
                ('Session type', os.environ.get('XDG_SESSION_TYPE', 'Unknown'))]
    receipt = inspect_receipt(root)
    overview += [('Desktop build', receipt['version']), ('Build files', receipt['integrity'])]
    for field, label in [('installedAt', 'Installed at'), ('sourceCommit', 'Source commit')]:
        if field in receipt: overview.append((label, receipt[field]))
    storage = []
    for name, location in [('System', Path('/')), ('Home', home)]:
        try:
            usage = shutil.disk_usage(location)
            gib = 1024 ** 3
            storage.append((name, str(location), f'{usage.total / gib:.1f} GiB',
                            f'{usage.free / gib:.1f} GiB', f'{usage.used / usage.total:.0%}' if usage.total else 'Unknown'))
        except OSError:
            storage.append((name, str(location), 'Unavailable', '', ''))
    return {'overview': overview, 'storage': storage, 'backups': backup_rows(root, media_root), 'build': receipt}


def health_summary(report):
    issues = []
    for name, unit, state, detail, startup in report.get('services', []):
        if state == 'failed': issues.append((name, 'Failed', 'Open the service log to identify the failure before restarting.'))
        elif state == 'unavailable': issues.append((name, 'Unavailable', 'The service manager could not be reached. Check your signed-in session.'))
        elif name in {'PipeWire', 'WirePlumber'} and state != 'active':
            issues.append((name, state, 'Audio may be unavailable. Check the audio services and devices.'))
        elif name in {'Webbie', 'Ollama'} and state != 'active':
            issues.append((name, state, 'Voice or local AI may be unavailable. Check whether this service is installed and enabled.'))
    for name, path, total, free, used in report.get('storage', []):
        try:
            if int(used.removesuffix('%')) >= 90:
                issues.append((name + ' storage', used + ' used', 'Review large files and available space before recording or installing upgrades.'))
        except (ValueError, AttributeError): pass
    build = report.get('build', {})
    if build.get('mismatches'): issues.append(('Desktop build', 'Files changed', 'Review the build receipt before assuming all parts belong to the same upgrade.'))
    if not issues:
        issues.append(('Inspection', 'No flagged issues' if 'services' in report else 'Not fully checked',
                       'Manual playback, microphone, login and lock checks are still required.' if 'services' in report else 'Refresh to inspect services and audio.'))
    return issues


def collect(root, home=None, media_root='/opt/spider-media-center'):
    report = file_snapshot(root, home, media_root)
    report['services'] = service_states()
    report['volume'] = output_level()
    for executable, args in [('wpctl', ['status']), ('pactl', ['info'])]:
        if shutil.which(executable):
            code, text = run([executable, *args])
            if code == 0 and text.strip():
                report['audio'] = text.strip()
                break
    else:
        report['audio'] = 'Audio status unavailable. Check PipeWire/WirePlumber in Services.'
    report['checkedAt'] = datetime.now().strftime('%H:%M:%S')
    report['health'] = health_summary(report)
    return report
