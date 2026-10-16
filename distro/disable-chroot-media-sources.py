#!/usr/bin/env python3
"""Disable unavailable installer-media APT sources in a STAGED chroot only.

Handles legacy *.list and deb822 *.sources, preserving online mirrors.
Never run against /; a separate explicit --rootfs is mandatory.
This changes only the staged rootfs's /etc/apt files, not the build host.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

LEGACY = re.compile(r"^(\s*)(deb(?:-src)?)(\s+)(\[[^\]]+\]\s+)?(\S+)(.*)$")
FIELD = re.compile(r"^([a-zA-Z0-9-]+):[ \t]*(.*)$")
MEDIA_PATHS = ("/cdrom", "/media/cdrom", "/mnt/cdrom")


def installer_media(uri: str) -> bool:
    if uri.lower().startswith("cdrom:"):
        return True
    parsed = urlsplit(uri)
    if parsed.scheme.lower() != "file" or parsed.netloc not in ("", "localhost"):
        return False
    path = unquote(parsed.path).rstrip("/")
    return any(path == name or path.startswith(name + "/") for name in MEDIA_PATHS)


def clean_list(text: str) -> tuple[str, int]:
    output = []
    changed = 0
    for line in text.splitlines(keepends=True):
        matched = LEGACY.match(line)
        if matched and installer_media(matched.group(5)):
            output.append("# spider-build: disabled missing installer media: " + line)
            changed += 1
        else:
            output.append(line)
    return "".join(output), changed


def clean_sources(text: str) -> tuple[str, int]:
    # Keep paragraphs/comments unchanged unless they contain active media URIs.
    parts = re.split(r"(\r?\n[ \t]*\r?\n)", text)
    changed = 0
    for idx in range(0, len(parts), 2):
        stanza = parts[idx]
        lines = stanza.splitlines(keepends=True)
        if not lines:
            continue
        fields: dict[str, tuple[int, int, str]] = {}
        pos = 0
        while pos < len(lines):
            m = FIELD.match(lines[pos])
            if m:
                first = pos
                key = m.group(1).lower()
                values = [m.group(2).strip()]
                pos += 1
                while pos < len(lines) and lines[pos].startswith((" ", "\t")):
                    values.append(lines[pos].strip())
                    pos += 1
                fields[key] = (first, pos, " ".join(values))
            else:
                pos += 1
        if "uris" not in fields:
            continue
        enabled = fields.get("enabled")
        if enabled and enabled[2].strip().lower() == "no":
            continue
        uris = fields["uris"][2].split()
        media = [u for u in uris if installer_media(u)]
        if not media:
            continue
        remaining = [u for u in uris if not installer_media(u)]
        edits: list[tuple[int, int, str]] = []
        if remaining:
            start, end, _ = fields["uris"]
            # Other valid repository URIs in a mixed stanza stay enabled.
            newline = "\r\n" if lines[start].endswith("\r\n") else "\n"
            edits.append((start, end, "URIs: " + " ".join(remaining) + newline))
        elif enabled:
            start, end, _ = enabled
            newline = "\r\n" if lines[start].endswith("\r\n") else "\n"
            edits.append((start, end, "Enabled: no" + newline))
        else:
            newline = "\r\n" if "\r\n" in stanza else "\n"
            # Appending Enabled: no to an all-media stanza avoids
            # disabling any separate online mirror paragraph.
            end_newline = "" if not lines or lines[-1].endswith(("\n", "\r")) else newline
            edits.append((len(lines), len(lines), end_newline + "Enabled: no" + newline))
        for start, end, replacement in sorted(edits, reverse=True):
            lines[start:end] = [replacement]
        parts[idx] = "".join(lines)
        changed += len(media)
    return "".join(parts), changed


def process_rootfs(rootfs: Path, apply: bool) -> int:
    rootfs = rootfs.resolve(strict=True)
    if rootfs == Path("/"):
        raise ValueError("Refusing to change the running host's /etc/apt")
    apt = rootfs / "etc/apt"
    if not apt.is_dir() or apt.is_symlink():
        raise ValueError("Expected staged /etc/apt directory is missing or unsafe")
    paths = [apt / "sources.list"]
    paths.extend(sorted((apt / "sources.list.d").glob("*.list")))
    paths.extend(sorted((apt / "sources.list.d").glob("*.sources")))
    changed = 0
    for path in paths:
        if not path.exists():
            continue
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(apt):
            raise ValueError(f"Unsafe source file path: {path}")
        text = path.read_text()
        cleaned, count = (clean_sources(text) if path.suffix == ".sources"
                          else clean_list(text))
        if count:
            print(f"{path.relative_to(rootfs)}: {count} enabled installer-media URI(s)")
            if apply:
                path.write_text(cleaned)
            changed += count
    if apply:
        print(f"DISABLED: {changed} installer-media APT source(s) in staged rootfs")
        return 0
    if changed:
        print(f"BLOCK: {changed} enabled installer-media APT source(s) remain in staged rootfs")
        return 3
    print("PASS: no enabled installer-media APT source in staged rootfs")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rootfs", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--apply", action="store_true", help="change staged rootfs sources")
    mode.add_argument("--check", action="store_true", help="read-only check; fails if media is enabled")
    args = parser.parse_args()
    try:
        return process_rootfs(args.rootfs, args.apply)
    except (ValueError, OSError) as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
