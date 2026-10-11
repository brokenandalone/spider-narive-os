#!/usr/bin/env python3
"""Read-only Spider Studio installed-vs-source qualification report.

Does not alter packages, services, projects, models, files or credentials.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess

PARTS = (
    'studio/main.py',
    'studio/ai_panel.py',
    'studio/band_mix.py',
    'studio/band_mixer_panel.py',
    'studio/band_projects.py',
    'studio/release_export.py',
    'studio/release_panel.py',
    'studio/mix_presets.py',
    'studio/music_backend.py',
    'studio/voice_profile.py',
    'studio/voice_conversion.py',
    'studio/song_mix.py',
    'studio/multitrack.py',
    'studio/multitrack_dialog.py',
    'studio/package/music-engine.sh',
    'studio/package/voice-engine.sh',
)
FILTERS = ('amix', 'alimiter', 'stereotools', 'adelay', 'aformat')


def digest(file):
    hash_ = hashlib.sha256()
    with file.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            hash_.update(block)
    return hash_.hexdigest()


def source_status(source_root, installed_root):
    records = {}
    for relative in PARTS:
        source, installed = source_root / relative, installed_root / relative
        if source.is_symlink() or installed.is_symlink():
            state = 'symlink_review_required'
        elif not source.is_file():
            state = 'source_not_present'
        elif not installed.is_file():
            state = 'not_installed'
        else:
            state = ('matches_source' if digest(source) == digest(installed)
                     else 'different_inspect_before_replacing')
        records[relative] = state
    return records


def ffmpeg_status():
    binary = shutil.which('ffmpeg')
    if not binary:
        return {'available': False, 'required_filters': []}
    try:
        result = subprocess.run(
            [binary, '-hide_banner', '-filters'],
            capture_output=True, text=True, check=True, timeout=12,
        )
    except (OSError, subprocess.TimeoutExpired, subprocess.CalledProcessError):
        return {'available': True, 'filter_check_failed': True}
    # Match filter names at the column boundary, not anywhere in descriptions.
    present = set()
    for line in result.stdout.splitlines():
        tokens = line.strip().split()
        if len(tokens) >= 2 and tokens[1] in FILTERS:
            present.add(tokens[1])
    return {'available': True, 'required_filters': sorted(present),
            'missing_filters': sorted(set(FILTERS) - present)}


def inspect(source_root, installed_root):
    source_root = Path(source_root).expanduser().resolve()
    installed_root = Path(installed_root).expanduser().resolve()
    return {
        'schema': 1,
        'read_only': True,
        'installed_october_10_baseline_must_be_preserved': True,
        'source_root': str(source_root),
        'installed_root': str(installed_root),
        'status': source_status(source_root, installed_root),
        'ffmpeg': ffmpeg_status(),
        'qt5_available': importlib.util.find_spec('PyQt5') is not None,
        'warning': (
            'Different files may contain owner modifications. Do not replace them '
            'without backup and review. GitHub checks do not prove PC audio acceptance.'
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path,
                        default=Path(__file__).resolve().parents[2])
    parser.add_argument('--installed-root', type=Path,
                        default=Path('/usr/local/lib/spider-os'))
    args = parser.parse_args()
    report = inspect(args.source_root, args.installed_root)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
