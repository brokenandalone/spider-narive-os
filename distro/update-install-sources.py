#!/usr/bin/env python3
"""Refresh the installed-system size without changing Ubuntu's source IDs."""
import sys
from pathlib import Path

import yaml


def update_catalog(catalog, installed_size):
    sources = catalog if isinstance(catalog, list) else catalog["sources"]
    matches = 0
    for source in sources:
        matched = False
        if source.get("path") == "standard.squashfs":
            source["size"] = installed_size
            matched = True
        for variation in source.get("variations", {}).values():
            if variation.get("path") == "standard.squashfs":
                variation["size"] = installed_size
                matched = True
        if matched:
            # Parent size is also consumed by older installer releases.
            source["size"] = installed_size
            matches += 1
    if not matches:
        raise ValueError("Installer catalog does not reference standard.squashfs; refusing to build an unverified install source")
    return matches


def main():
    path = Path(sys.argv[1])
    size = int(sys.argv[2])
    if size <= 0:
        raise ValueError("Installed-system size must be positive")
    catalog = yaml.safe_load(path.read_text())
    count = update_catalog(catalog, size)
    path.write_text(yaml.safe_dump(catalog, sort_keys=False, allow_unicode=True))
    print(f"Updated {count} Spider OS install source(s): {size} bytes")


if __name__ == "__main__":
    main()
