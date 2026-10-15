#!/usr/bin/env python3
"""Normalize a verified Studio three-layer catalog to Spider's full install.

The builder materializes the two installed layers first. This script only
rewrites metadata; it must never be used to rename a delta into a full root.
"""
import copy
import re
import sys
from pathlib import Path

import yaml


def normalize(catalog):
    result = copy.deepcopy(catalog)
    sources = result if isinstance(result, list) else result['sources']
    defaults = [source for source in sources if source.get('default')]
    if len(defaults) != 1:
        raise ValueError('Expected exactly one upstream default install source')
    source = defaults[0]
    entries = [source, *source.get('variations', {}).values()]
    paths = {entry['path'] for entry in entries if entry.get('path')}
    if paths != {'minimal.standard.squashfs'}:
        raise ValueError(f'Unverified default installed layer paths: {paths}')
    if source.get('type') != 'fsimage-layered' or source.get('preinstalled_langs'):
        raise ValueError('Unsupported installer source type or language layers')
    for entry in entries:
        if entry.get('path'):
            entry['path'] = 'standard.squashfs'
    # Spider retains the Studio applications. Offer only the fully customized
    # source, retaining its upstream ID, kernel metadata and variation IDs.
    sources[:] = [source]
    return result


def normalize_grub(directory):
    replacements = {}
    for path in Path(directory).rglob('*.cfg'):
        text = path.read_text()
        paths = set(re.findall(r'layerfs-path=([^\s"\x27]+)', text))
        if paths - {'minimal.standard.live.squashfs'}:
            raise ValueError(f'Unverified live boot layer selection: {paths}')
        if paths:
            replacements[path] = text.replace('layerfs-path=minimal.standard.live.squashfs',
                                              'layerfs-path=standard.live.squashfs')
    if not replacements:
        raise ValueError('No verified upstream live-layer boot argument')
    # Validate every menu before writing any of them.
    for path, text in replacements.items():
        path.write_text(text)


if __name__ == '__main__':
    path = Path(sys.argv[1])
    result = normalize(yaml.safe_load(path.read_text()))
    if len(sys.argv) > 2:
        normalize_grub(sys.argv[2])
    path.write_text(yaml.safe_dump(result, sort_keys=False, allow_unicode=True))
