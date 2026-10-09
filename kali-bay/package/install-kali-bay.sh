#!/usr/bin/env bash
# Install/update ONLY the Spider OS Kali Bay host manager and UI.
# Does not run Podman, Distrobox, apt, Kali package setup or container updates.
set -Eeuo pipefail

SOURCE_ROOT="$(cd -- "$(dirname -- "$0")/../.." && pwd)"
DEST="/usr/local/lib/spider-os"
BIN="/usr/local/bin"
APPS="/usr/share/applications"
ACTION="$(printf '%s' "$@")"

usage() {
    printf 'Usage: bash kali-bay/package/install-kali-bay.sh --check | --apply\n'
}

source_checks() {
    if [[ ! -s "$SOURCE_ROOT/kali-bay/bin/kali-bay" || ! -s "$SOURCE_ROOT/kali-bay/ui/kali_bay.py" ]]; then
        echo 'Missing Kali Bay manager or UI in this source checkout.' >&2
        exit 1
    fi
    bash -n "$SOURCE_ROOT/kali-bay/bin/kali-bay"
    python3 - "$SOURCE_ROOT/kali-bay/ui/kali_bay.py" <<'PY'
from pathlib import Path
import sys
source = Path(sys.argv[1])
compile(source.read_bytes(), str(source), 'exec')
PY
}

check() {
    source_checks
    echo 'Kali Bay-only package: source files and Python syntax passed.'
    if python3 -c 'from PyQt5.QtWidgets import QApplication' >/dev/null 2>&1; then
        echo 'PyQt5: available'
    else
        echo 'PyQt5: unavailable (the graphical UI requires python3-pyqt5)'
    fi
    for tool in podman distrobox; do
        if command -v "$tool" >/dev/null 2>&1; then
            echo "$tool: installed (not started or modified)"
        else
            echo "$tool: not in PATH (installing the launcher does not provision a container)"
        fi
    done
    for item in "$DEST/kali-bay/bin/kali-bay" "$DEST/kali-bay/ui/kali_bay.py" "$BIN/kali-bay" "$APPS/spider-kali-bay.desktop"; do
        if [[ -e "$item" || -L "$item" ]]; then echo "Existing: $item"; else echo "Not installed: $item"; fi
    done
    echo 'Read-only check complete. No container was touched.'
}

apply() {
    if (( EUID != 0 )); then
        echo 'Run --apply with sudo from your Spider OS user account.' >&2
        exit 1
    fi
    if [[ ! -v SUDO_USER || "$SUDO_USER" == root || -z "$SUDO_USER" ]]; then
        echo 'Do not run this from a root login. Use sudo from Spider OS.' >&2
        exit 1
    fi
    source_checks
    test -d "$DEST" || { echo 'Spider OS installation root not found.' >&2; exit 1; }
    BACKUP="$DEST/upgrade-backups/kali-bay-$(date +%Y%m%d-%H%M%S)-$$"
    mkdir -p "$BACKUP/existing" "$DEST/kali-bay/bin" "$DEST/kali-bay/ui" "$BIN" "$APPS"

    # Preserve exact previous versions, including symlinks. This is the
    # entire set of existing paths this script is authorized to replace.
    for file in \
        "$DEST/kali-bay/bin/kali-bay" \
        "$DEST/kali-bay/ui/kali_bay.py" \
        "$BIN/kali-bay" \
        "$APPS/spider-kali-bay.desktop"; do
        if [[ -e "$file" || -L "$file" ]]; then
            mkdir -p "$BACKUP/existing$(dirname "$file")"
            cp -a -- "$file" "$BACKUP/existing$file"
        fi
    done

    cat > "$BACKUP/rollback.sh" <<'ROLLBACK'
#!/usr/bin/env bash
set -Eeuo pipefail
if (( EUID != 0 )); then
    echo 'Run with sudo.' >&2
    exit 1
fi
BACKUP="$(cd -- "$(dirname -- "$0")" && pwd)"
for file in \
    /usr/local/lib/spider-os/kali-bay/bin/kali-bay \
    /usr/local/lib/spider-os/kali-bay/ui/kali_bay.py \
    /usr/local/bin/kali-bay \
    /usr/share/applications/spider-kali-bay.desktop; do
    original="$BACKUP/existing$file"
    if [[ -e "$original" || -L "$original" ]]; then
        mkdir -p "$(dirname "$file")"
        rm -f -- "$file"
        cp -a -- "$original" "$file"
    else
        rm -f -- "$file"
    fi
done
echo 'Prior Kali Bay host files restored. No container changes were made.'
ROLLBACK
    chmod 700 "$BACKUP/rollback.sh"

    # Replace only the two Kali Bay host-source files; all former copies
    # are available under this install's backup directory.
    install -m 755 "$SOURCE_ROOT/kali-bay/bin/kali-bay" "$DEST/kali-bay/bin/kali-bay"
    install -m 644 "$SOURCE_ROOT/kali-bay/ui/kali_bay.py" "$DEST/kali-bay/ui/kali_bay.py"

    # System-wide host command. Does not shell into or initialize Kali.
    rm -f -- "$BIN/kali-bay"
    ln -s "$DEST/kali-bay/bin/kali-bay" "$BIN/kali-bay"

    cat > "$APPS/spider-kali-bay.desktop" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=Kali Bay
Comment=Spider OS security workspace
Exec=/usr/local/bin/kali-bay ui
TryExec=/usr/local/bin/kali-bay
Icon=utilities-terminal
Terminal=false
Categories=System;Security;
DESKTOP
    chmod 644 "$APPS/spider-kali-bay.desktop"

    # Original, already-installed Kali Bay wallpaper is retained.
    # No user home/data, Distrobox container, Podman image, apt cache,
    # host service, autostart configuration or Plasma session is altered.
    printf 'Kali Bay host UI and launchers updated.\nBackup and rollback: %s\n' "$BACKUP"
    echo 'To open: kali-bay ui'
    echo 'To inspect without changes: kali-bay doctor'
    echo 'Kali container and its installed tools were not modified.'
}

case "$ACTION" in
    --check) check ;;
    --apply) apply ;;
    *) usage; exit 2 ;;
esac
