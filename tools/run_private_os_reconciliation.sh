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
# Proposals have ORIGINAL live-source pins. If a service has legitimately
# changed since that reviewed baseline, do not silently patch new code.
# Continue the SOURCE AUDIT, but put that proposed patch explicitly on hold.
webbie_pin="08673fb0080d2974a0310e462a9f8d29a19d798a0f0cb74ff699dd271e67258c"
nova_pin="5a59dca3f83a4cc7b9c49af5b3fa5a1cf0d4eb2c3652445cf17ae4898dc96089"
webbie_now="$(sha256sum -- "$live_root/webbie/agent/webbie.py" | awk '{print $1}')"
nova_now="$(sha256sum -- "$live_root/media/ai-dj/service.py" | awk '{print $1}')"
if [[ "$webbie_now" == "$webbie_pin" ]]; then
  python3 "$script_dir/patch_owner_session_detection.py" \
    --owner-archive "$archive" \
    --installed-root "$live_root" \
    --output "$dest/private-proposals/webbie/agent/webbie.py"
  printf 'WEBBIE PROPOSAL: WRITTEN FOR OWNER REVIEW ONLY\\n'
else
  printf '%s\\n' 'HOLD: Installed Webbie is a different version. Patch not generated.' \
    'Review installed changes and update the patch without overwriting them.' \
    > "$dest/private-proposals/WEBBIE-PATCH-HOLD.txt"
  printf 'WEBBIE PROPOSAL: ON HOLD (new owner source fingerprint)\\n'
fi

if [[ "$nova_now" == "$nova_pin" ]]; then
  python3 "$script_dir/patch_owner_nova_voices.py" \
    --owner-archive "$archive" \
    --installed-root "$live_root" \
    --candidate-source "$source_root" \
    --output "$dest/private-proposals/media/ai-dj/service.py"
  printf 'NOVA PROPOSAL: WRITTEN FOR OWNER REVIEW ONLY\\n'
else
  printf '%s\\n' 'HOLD: Installed native Nova DJ service changed since original review.' \
    'Newer owner service remains authoritative. A fresh semantic code review' \
    'is required before integrating Australian voices into this service.' \
    > "$dest/private-proposals/NOVA-PATCH-HOLD.txt"
  printf 'NOVA PROPOSAL: ON HOLD (new installed service fingerprint)\\n'
fi

# Deliberately do not replace files in owner-stage/staged-source with the
# two proposals; these are not proven safe at runtime.
printf '\nNATIVE SPIDER OS RECONCILIATION REVIEW COMPLETE.\n'
printf 'Owner source snapshot: %s\n' "$dest/owner-stage/staged-source"
printf 'Private reviewed proposals: %s\n' "$dest/private-proposals"
printf 'SAFE-TO-SHARE METADATA REPORT: %s\n' "$dest/semantic-reconciliation.json"
printf 'No live files changed. No new voices deployed. No service restarted.\n'
printf 'NOT INSTALLABLE. Media Center and BCN website are completely separate.\n'
