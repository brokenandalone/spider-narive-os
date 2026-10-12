#!/usr/bin/env bash
# Spider OS Wave Five PC comparison only. NO install, sudo or service changes.
set -u
SOURCE="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
case "$SOURCE" in
  /usr/local/lib/spider-os|/usr/local/lib/spider-os/*)
    echo "ERROR: run this from a separate downloaded checkout, not live Spider OS." >&2
    exit 3 ;;
esac
if [[ ! -f "$SOURCE/tools/spider_systemwide_readiness.py" ]]; then
  echo "Cannot find Wave Five source. No changes made." >&2
  exit 3
fi
if [[ "$(id -u)" == "0" ]]; then
  echo "Run as your ordinary Spider OS user, without sudo." >&2
  exit 3
fi
STAMP="$(date +%Y%m%d-%H%M%S)"
DEST="$HOME/Downloads/Spider_OS_Wave5_Review_$STAMP"
mkdir -p "$DEST" || exit 3
umask 077
printf '%s\n' "Spider OS Wave Five checkout: $SOURCE" > "$DEST/README.txt"
git -C "$SOURCE" rev-parse HEAD >> "$DEST/README.txt" 2>/dev/null || true
printf '%s\n' "No installation, model replacement, service restart, microphone or webcam capture happened." >> "$DEST/README.txt"
run_readonly() {
  local label="$1"
  shift
  "$@" > "$DEST/$label" 2>&1
  local code=$?
  printf '%s %s\n' "$label" "$code" >> "$DEST/exit-codes.txt"
  return 0
}
run_readonly model_inventory.json python3 "$SOURCE/tools/webbie_model_compatibility.py" --json
run_readonly pc_hardware_readiness.json python3 "$SOURCE/tools/spider_pc_readiness.py" --json
run_readonly combined_source_audit.txt python3 "$SOURCE/tools/combined_release_audit.py" --checkout "$SOURCE"
run_readonly candidate_vs_pc.json python3 "$SOURCE/tools/daily_pc_acceptance.py" --phase before --json
run_readonly wave5_pc_continuity.json python3 "$SOURCE/tools/spider_systemwide_readiness.py" --pc --json
run_readonly release_blockers.json python3 "$SOURCE/tools/daily_release_continuity.py" --json
run_readonly installer_preview.txt python3 "$SOURCE/system/release_batch.py" --check
echo "Read-only review finished: $DEST"
echo "The release is NOT approved or installed. Review these files before any apply:"
echo "  model_inventory.json"
echo "  pc_hardware_readiness.json"
echo "  candidate_vs_pc.json"
echo "  wave5_pc_continuity.json"
echo "  release_blockers.json"
echo "  installer_preview.txt"
