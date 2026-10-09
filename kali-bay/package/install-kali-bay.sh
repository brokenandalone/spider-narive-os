#!/usr/bin/env bash
# Selectively install Kali Bay's UI and manager. Never modify the container.
set -Eeuo pipefail

usage() {
    cat <<'EOF'
Usage: install-kali-bay.sh --check | --install

--check    Read-only compatibility inventory and file comparison.
--install  Back up both installed Kali Bay scripts, then update just
           the application source. Does not run Podman, Distrobox, apt,
           scans or start any security services.
EOF
}
mode="${1:-}"
if [[ "$mode" != "--check" && "$mode" != "--install" ]]; then
    usage >&2
    exit 2
fi
source_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
installed_root=/usr/local/lib/spider-os
declare -a relative_files=(
    kali-bay/bin/kali-bay
    kali-bay/ui/kali_bay.py
)
for file in "${relative_files[@]}"; do
    [[ -f "$source_root/$file" && ! -L "$source_root/$file" ]] || {
        printf 'Missing or linked source: %s\n' "$source_root/$file" >&2
        exit 1
    }
done
if [[ "$mode" == "--check" ]]; then
    for relative in "${relative_files[@]}"; do
        target="$installed_root/$relative"
        if [[ -L "$target" ]]; then
            printf 'REFUSE symlink: %s\n' "$target"
        elif [[ ! -f "$target" ]]; then
            printf 'MISSING: %s\n' "$target"
        elif cmp -s "$source_root/$relative" "$target"; then
            printf 'UNCHANGED: %s\n' "$target"
        else
            printf 'DIFFERENT (backup required): %s\n' "$target"
        fi
    done
    echo 'Read-only check complete. No containers or services touched.'
    exit 0
fi

[[ "$EUID" -eq 0 ]] || {
    echo 'Installation requires sudo (run from your normal user session).' >&2
    exit 1
}
[[ -d "$installed_root/kali-bay" ]] || {
    echo 'Kali Bay is not installed; refusing to create a new runtime.' >&2
    exit 1
}
# Refuse anything that could follow a symlink to some unrelated file.
for relative in "${relative_files[@]}"; do
    target="$installed_root/$relative"
    if [[ -L "$target" || ! -f "$target" ]]; then
        printf 'Expected an existing regular Kali Bay file: %s\n' "$target" >&2
        exit 1
    fi
done
command -v python3 >/dev/null || { echo 'Python 3 missing.' >&2; exit 1; }
python3 -m py_compile "$source_root/kali-bay/ui/kali_bay.py"
bash -n "$source_root/kali-bay/bin/kali-bay"

stamp="$(date +%Y%m%d-%H%M%S)"
backup="$installed_root/upgrade-backups/kali-bay-$stamp"
mkdir -p "$backup"
for relative in "${relative_files[@]}"; do
    mkdir -p "$backup/$(dirname "$relative")"
    cp -a -- "$installed_root/$relative" "$backup/$relative"
done
# No writes to the existing Podman image or Distrobox home.
for relative in "${relative_files[@]}"; do
    mode_bits=0644
    [[ "$relative" == kali-bay/bin/kali-bay ]] && mode_bits=0755
    install -m "$mode_bits" "$source_root/$relative" "$installed_root/$relative"
done
echo "Kali Bay UI/manager installed. Backup: $backup"
echo 'Kali container, installed packages and Spider services were unchanged.'
echo 'Check: /usr/local/lib/spider-os/kali-bay/bin/kali-bay doctor'
