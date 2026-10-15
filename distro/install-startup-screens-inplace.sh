#!/usr/bin/env bash
# USB-free post-upgrade Spider OS graphical startup branding installer.
# Does not change bootloader, crypttab, initramfs or Plymouth selection.
set -Eeuo pipefail

mode="--check"
if (( $# >= 1 )); then mode="$1"; fi
preset="spider-purple"
if (( $# >= 2 )); then preset="$2"; fi
source_root="$(cd "$(dirname "$0")/../.." && pwd)"

if [[ "$mode" != "--check" && "$mode" != "--apply" ]]; then
    echo "Usage: $0 [--check|--apply] [spider-purple|spider-crimson|spider-nightfall]" >&2
    exit 2
fi

case "$preset" in
  spider-purple|spider-crimson|spider-nightfall) ;;
  *) echo "Unknown startup set: $preset" >&2; exit 2 ;;
esac

# Use the same staging code for ISO builds and in-place installs.
scratch="$(mktemp -d -t spider-startup-XXXXXX)"
trap 'rm -rf "$scratch"' EXIT
bash "$source_root/distro/config/branding/install-startup-screens.sh" \
    "$scratch" "$source_root" "$preset"

if [[ "$mode" == "--check" ]]; then
    printf '%s\n' "Spider OS startup set: $preset"
    printf '%s\n' "Art sources: PASS"
    printf '%s\n' "Staged Plasma, SDDM and Plymouth artwork: PASS"
    printf '%s\n' "This is a preview; the installed PC has NOT changed."
    exit 0
fi

if (( EUID != 0 )); then
    echo "Apply requires sudo. No changes made." >&2
    exit 2
fi

# Protect the working 26.04 host. Run only after the supported in-place
# release upgrade and a stable 26.10 KDE/SDDM session.
source /etc/os-release
if [[ "$VERSION_ID" != "26.10" ]]; then
    echo "Refusing to apply until the running base is Ubuntu Studio 26.10." >&2
    exit 1
fi
if [[ ! -d /usr/share/sddm/themes/breeze ]]; then
    echo "Breeze SDDM theme was not found. Review the installed display manager." >&2
    exit 1
fi

umask 077
install -d -m 700 /var/backups/spider-os/startup
backup="$(mktemp -d /var/backups/spider-os/startup/backup-XXXXXXXX)"
manifest="$backup/manifest.tsv"
printf '# path (relative to root)\texisted before apply\n' > "$manifest"

# Keep a copy of each overwritten file/directory and its original absence.
# Intentionally exclude /boot, /etc/default/grub, crypttab and initramfs.
copy_staged() {
    local rel="$1"
    local from="$scratch/$rel"
    local dest="/$rel"
    test -e "$from" || { echo "Missing staged source: $from" >&2; exit 1; }
    if [[ -e "$dest" || -L "$dest" ]]; then
        mkdir -p "$backup/original/$(dirname "$rel")"
        cp -a -- "$dest" "$backup/original/$rel"
        printf '%s\tpresent\n' "$rel" >> "$manifest"
    else
        printf '%s\tabsent\n' "$rel" >> "$manifest"
    fi
    mkdir -p "$(dirname "$dest")"
    if [[ -d "$from" ]]; then
        mkdir -p "$dest"
        cp -a -- "$from/." "$dest/"
    else
        install -m 644 -- "$from" "$dest"
    fi
}

copy_staged usr/share/spider-os/startup-sets
copy_staged usr/share/spider-os/branding/startup-background.png
copy_staged usr/share/spider-os/branding/spider-os-splash.png
copy_staged usr/share/spider-os/branding/selected-startup-set
copy_staged usr/share/plymouth/themes/spider-os/spider-os-background.png
copy_staged usr/share/plasma/look-and-feel/org.spider.os
copy_staged usr/share/sddm/themes/breeze/theme.conf.user
copy_staged etc/xdg/ksplashrc

printf '%s\n' "$preset" > "$backup/selected-set.txt"
printf '\nApplied Spider OS %s startup artwork.\n' "$preset"
printf 'Backup of replaced files and original state: %s\n' "$backup"
printf '%s\n' "The new greeter/splash appears at the NEXT sign-in."
printf '%s\n' "No reboot, SDDM restart, GRUB modification, or initramfs rebuild was performed."
printf '%s\n' "Plymouth image was staged only; do not activate it until LUKS prompt tests pass."
