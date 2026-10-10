#!/usr/bin/env python3
"""Read-only Spider OS installed Webbie reconciliation audit.

Run from a clean checkout as the desktop user, NEVER with sudo. Reads only
specific Python sources/metadata, not history, recordings, notes or credentials.
No files are written, imported/executed, copied to GitHub, or installed.
A match is NOT authorization to overwrite anything. Always preserve the live
customized agent until a separately reviewed, verified integration exists.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import os
import subprocess

ROOT = Path(__file__).resolve().parents[2]
INSTALL = Path('/usr/local/lib/spider-os')
SOURCES = {
    'webbie/agent/webbie.py': (
        'on_interrupt', 'on_text', 'stop_speaking', 'CONVERSATION_WINDOW_SECONDS',
    ),
    'webbie/brain/brain.py': (
        'load_conversation', 'recall_memories', 'remember_turn', 'research_response',
    ),
    'webbie/voice/whisper_listener.py': (),
    'webbie/voice/tts.py': (),
    'the-web/overlay/webbie_face.py': ('paintEvent',),
    'the-web/shell/webbie_camera.py': ('capture_jpeg',),
}
# Historical owner-installed snapshot: informative only, NEVER an automatic
# overwrite permission; owner has performed further PC fixes since October 9.
OCT9_AGENT_SHA = 'f8a66bc844b7229e9af8f544c73237aef31091c75260fa5cac630ea6eb8d96ad'


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(65536), b''):
            digest.update(chunk)
    return digest.hexdigest()


def inventory(path, needles):
    path = Path(path)
    if path.is_symlink():
        return {'state': 'symlink-blocked'}
    if not path.is_file():
        return {'state': 'absent'}
    try:
        raw = path.read_text('utf-8')
        tree = ast.parse(raw, filename=str(path))
    except (OSError, UnicodeError, ValueError, SyntaxError) as error:
        return {'state': 'invalid-python', 'error_type': type(error).__name__}
    funcs = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            funcs.add(node.name)
    return {
        'state': 'present',
        'sha256': sha(path),
        'lines': len(raw.splitlines()),
        'missing_repair_symbols': sorted(set(needles) - funcs),
    }


def report(root=ROOT, install=INSTALL):
    root = Path(root).resolve()
    install = Path(install).resolve()
    results = {}
    blocked = False
    modified = []
    for relative, needles in SOURCES.items():
        checked_in = inventory(root / relative, ())
        live = inventory(install / relative, needles)
        same = (checked_in['state'] == 'present' and
                live['state'] == 'present' and
                checked_in['sha256'] == live['sha256'])
        if live['state'] != 'present' or live.get('missing_repair_symbols'):
            blocked = True
        if live['state'] == 'present' and not same:
            modified.append(relative)
        results[relative] = {
            'installed': live,
            'checkout': checked_in,
            'byte_identical': same,
            'action': 'keep installed; reconciliation required' if not same
                      else 'identical; review required before deploying',
        }
    agent = results['webbie/agent/webbie.py']['installed']
    # Even an identical old branch is not reason to overwrite the PC's code.
    if modified:
        blocked = True
    result = {
        'read_only': True,
        'install_allowed': False,
        'overall': 'RECONCILIATION_HOLD' if blocked else 'REVIEW_REQUIRED',
        'historical_oct9_agent_match': agent.get('sha256') == OCT9_AGENT_SHA,
        'changed_or_missing_modules': modified,
        'files': results,
        'next_step': (
            'Compare current PC modules with this exact source revision, '
            'port new features into the preserved PC code, test on a detached '
            'copy, then run a separate backup-first installer preflight.'
        ),
    }
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', type=Path, default=ROOT)
    parser.add_argument('--installed-root', type=Path, default=INSTALL)
    args = parser.parse_args(argv)
    if os.geteuid() == 0:
        raise SystemExit('Run as the Spider OS desktop user, not sudo/root.')
    result = report(args.checkout, args.installed_root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result['overall'] == 'REVIEW_REQUIRED' else 2


if __name__ == '__main__':
    raise SystemExit(main())
