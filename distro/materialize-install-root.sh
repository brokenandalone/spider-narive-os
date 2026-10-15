#!/usr/bin/env bash
# Resolve overlay whiteouts and metadata before customizing a complete root.
set -Eeuo pipefail
casper="${1:?Pass the mounted upstream casper directory}"
destination="${2:?Pass an empty destination directory}"
[[ ${EUID} -eq 0 ]] || { echo 'Root is required for squashfs/overlay mounts' >&2; exit 1; }
[[ ! -e "$destination" ]] || { echo 'Destination already exists' >&2; exit 1; }
work="$(mktemp -d)"
cleanup_layers() (
    set +e
    for directory in merged standard minimal; do
        mountpoint -q "$work/$directory" && umount "$work/$directory"
    done
    rm -rf "$work"
)
trap cleanup_layers EXIT
mkdir -p "$work"/{minimal,standard,merged}
for layer in minimal minimal.standard; do
    test -s "$casper/$layer.squashfs"
done
mount -o loop,ro "$casper/minimal.squashfs" "$work/minimal"
mount -o loop,ro "$casper/minimal.standard.squashfs" "$work/standard"
mount -t overlay overlay -o "ro,lowerdir=$work/standard:$work/minimal" "$work/merged"
mkdir -p "$destination"
rsync -aHAX --numeric-ids "$work/merged/" "$destination/"
test -s "$destination/var/lib/dpkg/status"
test -x "$destination/bin/sh"
