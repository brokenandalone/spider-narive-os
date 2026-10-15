#!/usr/bin/env bash
# Revert only the application files installed by a specific Author/Webbie upgrade.
# Does not touch documents, manuscripts, user data, OS services, or configuration.
set -Eeuo pipefail
mode="${1:---check}"
backup="${2:-}"
root=/usr/local/lib/spider-os
case "$mode" in --check|--apply) ;; *) echo 'Usage: rollback-author-webbie.sh --check|--apply BACKUP_DIR' >&2; exit 2;; esac
if [[ -z "$backup" || "$backup" != "$root"/upgrade-backups/author-webbie-* ]]; then
  echo 'Supply an exact Author/Webbie backup directory.' >&2; exit 2
fi
if [[ -L "$backup" || ! -d "$backup" || -L "$backup/rollback-manifest.tsv" ]]; then
  echo 'Backup does not exist or is not a safe directory.' >&2; exit 2
fi
if [[ "$mode" == --apply && ( "$EUID" -ne 0 || -z ${SUDO_USER:-} ) ]]; then
  echo 'Apply needs sudo from the signed-in Spider OS account.' >&2; exit 2
fi
command -v sha256sum >/dev/null || exit 2
manifest="$backup/rollback-manifest.tsv"
[[ -s "$manifest" ]] || { echo 'No rollback manifest found. No changes made.' >&2; exit 2; }
# Compare every installed module with the recorded upgrade result before
# doing ANY restoration. Unrecognized edits after the upgrade are protected.
declare -a paths=() modes=()
problem=0
while IFS=$'\t' read -r relative action expected; do
  [[ "$relative" =~ ^(author|the-web/shell|webbie/agent)/[A-Za-z0-9_.-]+[.]py$ ]] || { echo "Unsafe manifest entry: $relative" >&2; exit 3; }
  [[ "$action" == existing || "$action" == new ]] || { echo "Unsafe rollback action for $relative" >&2; exit 3; }
  [[ "$expected" =~ ^[0-9a-f]{64}$ ]] || { echo "Unsafe hash for $relative" >&2; exit 3; }
  target="$root/$relative"
  if [[ -L "$target" || ! -f "$target" ]]; then
    echo "BLOCKED: $relative absent or symlinked"; problem=1; continue
  fi
  observed="$(sha256sum -- "$target" | cut -d' ' -f1)"
  if [[ "$observed" != "$expected" ]]; then
    echo "BLOCKED: locally modified after upgrade: $relative"; problem=1; continue
  fi
  if [[ "$action" == existing && ( -L "$backup/$relative" || ! -f "$backup/$relative" ) ]]; then
    echo "BLOCKED: original backup unavailable: $relative"; problem=1; continue
  fi
  paths+=("$relative"); modes+=("$action")
  echo "READY: $relative ($action)"
done < "$manifest"
(( problem == 0 )) || { echo 'No rollback performed.' >&2; exit 4; }
if [[ "$mode" == --check ]]; then
  echo 'Rollback CHECK PASSED: no application files changed.'
  exit 0
fi
for i in "${!paths[@]}"; do
  relative="${paths[$i]}"
  target="$root/$relative"
  if [[ "${modes[$i]}" == new ]]; then
    rm -- "$target"
  else
    temporary="$(mktemp "$root/$(dirname "$relative")/.webbie-restore.XXXXXXXX")"
    cp -a -- "$backup/$relative" "$temporary"
    mv -f -- "$temporary" "$target"
  fi
  echo "RESTORED: $relative"
done
echo 'Application code restored. User data and microphone settings untouched.'
echo 'Save work and restart The Web/Webbie service later to activate restored code.'
