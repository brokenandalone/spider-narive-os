#!/usr/bin/env bash
# Spider OS ONLY: private review staging. No service actions, sudo, or install.
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

if [[ "${EUID}" -eq 0 ]]; then
  printf 'BLOCKED: do not run owner review as root.\n' >&2
  exit 3
fi
if [[ "$#" -ne 3 ]]; then
  printf 'Usage: bash tools/run_private_os_reconciliation.sh OWNER_ZIP NEW_OUTPUT_DIR EXACT_CI_SHA\n' >&2
  exit 3
fi

archive="$(realpath -- "$1")"
dest="$2"
pin="$3"
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source_root="$(dirname -- "$script_dir")"
live_root="/usr/local/lib/spider-os"

if [[ ! "$pin" =~ ^[a-f0-9]{40}$ ]]; then
  printf 'BLOCKED: require exact full 40-digit reviewed Git SHA.\n' >&2
  exit 3
fi
if [[ ! -f "$archive" || -L "$archive" ]]; then
  printf 'BLOCKED: owner conflict archive not found or symlink.\n' >&2
  exit 3
fi
if [[ -e "$dest" || -L "$dest" ]]; then
  printf 'BLOCKED: review output already exists. No overwrites.\n' >&2
  exit 3
fi

# Compare fully resolved new output against source and actual installed root.
dest_parent="$(realpath -m -- "$dest")"
case "$dest_parent/" in
  "$source_root/"*|"$live_root/"*)
    printf 'BLOCKED: must stage outside live OS and Git checkout.\n' >&2
    exit 3 ;;
esac

actual="$(git -C "$source_root" rev-parse --verify HEAD)"
if [[ "$actual" != "$pin" ]]; then
  printf 'BLOCKED: checkout HEAD is not the exact CI reviewed commit.\n' >&2
  exit 3
fi
if [[ -n "$(git -C "$source_root" status --porcelain --untracked-files=no)" ]]; then
  printf 'BLOCKED: unreviewed tracked changes in Git checkout.\n' >&2
  exit 3
fi

umask 077
mkdir -p -- "$dest"
chmod 700 -- "$dest"

# No uploaded owner code enters GitHub; only private review copies are written.
python3 "$script_dir/build_owner_preserving_stage.py" \
  --source "$source_root" \
  --owner-archive "$archive" \
  --installed-root "$live_root" \
  --expected-commit "$pin" \
  --output "$dest/owner-stage"

python3 "$script_dir/owner_source_semantic_audit.py" \
  --source "$source_root" \
  --owner-archive "$archive" \
  --installed-root "$live_root" \
  --expected-commit "$pin" \
  --output "$dest/semantic-reconciliation.json"

mkdir -p -- "$dest/private-proposals/webbie/agent" "$dest/private-proposals/media/ai-dj"
python3 "$script_dir/patch_owner_session_detection.py" \
  --owner-archive "$archive" \
  --installed-root "$live_root" \
  --output "$dest/private-proposals/webbie/agent/webbie.py"

python3 "$script_dir/patch_owner_nova_voices.py" \
  --owner-archive "$archive" \
  --installed-root "$live_root" \
  --candidate-source "$source_root" \
  --output "$dest/private-proposals/media/ai-dj/service.py"

# Deliberately do not replace files in owner-stage/staged-source with the
# two proposals; these are not proven safe at runtime.
printf '\nNATIVE SPIDER OS RECONCILIATION REVIEW COMPLETE.\n'
printf 'Owner source snapshot: %s\n' "$dest/owner-stage/staged-source"
printf 'Private reviewed proposals: %s\n' "$dest/private-proposals"
printf 'SAFE-TO-SHARE METADATA REPORT: %s\n' "$dest/semantic-reconciliation.json"
printf 'No live files changed. No new voices deployed. No service restarted.\n'
printf 'NOT INSTALLABLE. Media Center and BCN website are completely separate.\n'
