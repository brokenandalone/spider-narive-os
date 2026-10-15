#!/usr/bin/env bash
# Disposable synthetic overlay: catches missing base files and resurrected deletions.
set -Eeuo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
mkdir -p "$work"/{base/bin,base/var/lib/dpkg,base/etc,delta/etc,casper}
printf '#!/bin/sh\n' > "$work/base/bin/sh"
chmod 755 "$work/base/bin/sh"
printf 'Package: synthetic-base\n' > "$work/base/var/lib/dpkg/status"
printf 'base\n' > "$work/base/etc/override"
printf 'deleted\n' > "$work/base/etc/deleted"
printf 'studio\n' > "$work/delta/etc/override"
ln "$work/delta/etc/override" "$work/delta/etc/hardlink"
ln -s override "$work/delta/etc/symlink"
mknod "$work/delta/etc/deleted" c 0 0
mksquashfs "$work/base" "$work/casper/minimal.squashfs" -noappend -quiet -processors 2
mksquashfs "$work/delta" "$work/casper/minimal.standard.squashfs" -noappend -quiet -processors 2
bash "$repo/distro/materialize-install-root.sh" "$work/casper" "$work/result"
test -x "$work/result/bin/sh"
test "$(cat "$work/result/etc/override")" = studio
test ! -e "$work/result/etc/deleted"
test "$(readlink "$work/result/etc/symlink")" = override
test "$(stat -c %i "$work/result/etc/override")" = "$(stat -c %i "$work/result/etc/hardlink")"
echo 'Installed layer merge preserves the base, overrides, whiteouts, hardlinks and symlinks.'
