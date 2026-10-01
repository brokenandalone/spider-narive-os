#!/usr/bin/env python3
"""Reject nonexistent installer sources and stale disk-size estimates."""
import sys
from pathlib import Path, PurePosixPath
import yaml


def verify(casper):
    catalog = yaml.safe_load((casper / 'install-sources.yaml').read_text())
    sources = catalog if isinstance(catalog, list) else catalog['sources']
    defaults = [source for source in sources if source.get('default')]
    if len(defaults) != 1:
        raise ValueError('Installer must have exactly one default source')
    installed_size = int((casper / 'standard.size').read_text())
    paths = []
    for source in sources:
        entries = [source, *source.get('variations', {}).values()]
        for entry in entries:
            name = entry.get('path')
            if not name:
                continue
            rel = PurePosixPath(name)
            if rel.is_absolute() or '..' in rel.parts:
                raise ValueError(f'Unsafe installer source path: {name}')
            file = casper / name
            if not file.is_file() or not file.stat().st_size:
                raise ValueError(f'Missing installer source: {name}')
            if name == 'standard.squashfs':
                paths.append(source['id'])
                if entry.get('size') != installed_size:
                    raise ValueError('Installer has a stale standard.squashfs size')
    if defaults[0]['id'] not in paths:
        raise ValueError('Default install does not use the Spider installed-system layer')
    return defaults[0]['id']


if __name__ == '__main__':
    print('Verified default Spider install source:', verify(Path(sys.argv[1])))
