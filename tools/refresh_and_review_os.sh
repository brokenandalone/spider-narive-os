#!/usr/bin/env bash
# Native Spider OS ONLY: refresh changed live source snapshot and stage offline review.
# Read-only on actual installed OS; creates NEW private work files under Downloads.
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

if [[ "${EUID}" -eq 0 ]]; then
  echo "BLOCKED: Never run owner source review as root." >&2
  exit 3
fi
if [[ "$#" -ne 3 ]]; then
  echo "Usage: bash tools/refresh_and_review_os.sh ORIGINAL_31_FILE_ZIP NEW_OUTPUT_DIR EXACT_CI_SHA" >&2
  exit 3
fi
old_zip="$(realpath -e -- "$1")"
output="$2"
pin="$3"
source_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
install_root="/usr/local/lib/spider-os"
if [[ ! "$pin" =~ ^[0-9a-f]{40}$ ]]; then
  echo "BLOCKED: supply an exact pinned 40-character CI-reviewed source SHA" >&2
  exit 3
fi
if [[ "$(git -C "$source_root" rev-parse HEAD)" != "$pin" ]]; then
  echo "BLOCKED: checkout does not match verified commit" >&2
  exit 3
fi
if [[ -n "$(git -C "$source_root" status --porcelain --untracked-files=no)" ]]; then
  echo "BLOCKED: tracked checkout source changed" >&2
  exit 3
fi
if [[ ! -f "$old_zip" || -L "$old_zip" ]]; then
  echo "BLOCKED: original conflict ZIP is missing or symlinked" >&2
  exit 3
fi
if [[ -e "$output" || -L "$output" ]]; then
  echo "BLOCKED: destination already exists; choose a fresh name" >&2
  exit 3
fi
absolute_output="$(realpath -m -- "$output")"
case "$absolute_output/" in
  "$source_root/"*|"$install_root/"*)
    echo "BLOCKED: report folder cannot be inside checkout or running OS" >&2
    exit 3 ;;
esac

umask 077
mkdir -p -- "$output"
python3 "$source_root/tools/refresh_owner_snapshot.py" \
  --previous-archive "$old_zip" \
  --installed-root "$install_root" \
  --output-dir "$output/current-owner"

# THIS RECONCILIATION DOES NOT INSTALL UPGRADES. Outdated pinned patches are
# held, never applied over a changed live Webbie or native Nova service.
bash "$source_root/tools/run_private_os_reconciliation.sh" \
  "$output/current-owner/Spider_OS_Current_31_Source.zip" \
  "$output/review" \
  "$pin"

printf '\n=== SPIDER OS ONLY: READ-ONLY RESULTS ===\n'
printf 'Changes in owner source: %s\n' "$output/current-owner/owner-source-drift.json"
printf 'New owner source ZIP (do NOT publish): %s\n' "$output/current-owner/Spider_OS_Current_31_Source.zip"
printf 'Function-level review: %s\n' "$output/review/semantic-reconciliation.json"
printf 'Patch proposals / holds: %s\n' "$output/review/private-proposals"
printf 'NO FILES INSTALLED, NO SERVICE RESTARTS. MEDIA CENTER AND BCN WEBSITE EXCLUDED.\n'
