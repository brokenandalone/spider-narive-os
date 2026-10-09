"""Installed desktop receipt and bounded checks of the managed build files."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

BUILD_VERSION = '2026.10.09-batch-2'
TRACKED = tuple('the-web/shell/' + name for name in (
    'main.py', 'desktop.py', 'app_catalog.py', 'wallpapers.py', 'workspace_files.py',
    'workspaces.py', 'system_panel.py', 'system_status.py', 'webbie_panel.py',
    'media_panel.py', 'media_transport.py', 'audio_controls.py', 'build_info.py')) + (
    'branding/webbie/webbie-face-v1.png', 'branding/webbie/webbie-face-speaking-v1.png',
    'branding/wallpapers/collection.json', 'the-web/session/the-web-session')


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_receipt(source, installed, backup):
    source, installed = Path(source), Path(installed)
    hashes = {relative: digest(source / relative) for relative in TRACKED}
    for relative, expected in hashes.items():
        if digest(installed / relative) != expected:
            raise ValueError('Installed build differs from source: ' + relative)
    commit = 'unavailable (archive or non-git source)'
    try:
        result = subprocess.run(['git', '-c', 'safe.directory=' + str(source), '-C', str(source), 'rev-parse', '--show-toplevel', 'HEAD'],
                                capture_output=True, text=True, timeout=2)
        lines = result.stdout.strip().splitlines()
        if result.returncode == 0 and len(lines) == 2 and Path(lines[0]).resolve() == source.resolve() and re.fullmatch(r'[a-f0-9]{40}', lines[1]):
            commit = lines[1]
    except (OSError, subprocess.TimeoutExpired):
        pass
    receipt = {'version': BUILD_VERSION, 'installedAt': datetime.now(timezone.utc).isoformat(),
               'sourceCommit': commit, 'backup': str(backup), 'sha256': hashes}
    destination = installed / 'the-web/install-receipt.json'
    temporary = destination.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(receipt, indent=2) + '\n'); temporary.chmod(0o644); temporary.replace(destination)
    return receipt


def inspect_receipt(root):
    root = Path(root); path = root / 'the-web/install-receipt.json'
    try:
        if path.stat().st_size > 65536: raise ValueError('Receipt is too large')
        receipt = json.loads(path.read_text())
        if not isinstance(receipt, dict) or not isinstance(receipt.get('sha256'), dict):
            raise ValueError('Invalid receipt')
        hashes = receipt['sha256']
        if set(hashes) != set(TRACKED): raise ValueError('Receipt has an unfamiliar file list')
        mismatches = []
        for relative in TRACKED:
            expected = hashes[relative]
            if not isinstance(expected, str) or not re.fullmatch(r'[a-f0-9]{64}', expected):
                raise ValueError('Invalid checksum')
            try:
                if digest(root / relative) != expected: mismatches.append(relative)
            except OSError:
                mismatches.append(relative)
        # Expose only managed build metadata, never arbitrary receipt fields.
        summary = {key: str(receipt.get(key, 'Unknown'))[:1024] for key in ('version', 'installedAt', 'sourceCommit', 'backup')}
        summary.update(integrity='Files changed or missing' if mismatches else 'Managed files match receipt', mismatches=mismatches)
        return summary
    except FileNotFoundError:
        return {'version': 'No installed-build receipt', 'integrity': 'Not recorded'}
    except (OSError, ValueError, TypeError):
        return {'version': 'Receipt unavailable', 'integrity': 'Could not validate receipt'}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(); parser.add_argument('source'); parser.add_argument('installed'); parser.add_argument('backup')
    args = parser.parse_args(); write_receipt(args.source, args.installed, args.backup)
    print('Installed desktop files verified; build receipt saved.')
