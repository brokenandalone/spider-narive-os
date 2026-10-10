#!/usr/bin/env bash
# Targeted Author Studio + shared Webbie integration, never a desktop reinstall.
# The user's SQLite manuscripts and all HOME documents are outside this script.
set -Eeuo pipefail

mode="${1:---check}"
if [[ "$mode" != --check && "$mode" != --apply ]]; then
    echo 'Usage: bash install-author-webbie.sh [--check|--apply]' >&2
    exit 2
fi
source_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
root=/usr/local/lib/spider-os
baseline_refs=(
  b2a1953e815479324c8a53a68ad51d813438f496
  fb0f6eb5a54cce0bc86ec081a67d18ccff4fc46e
  eec8e47c128a2f796ff5d16d549f8a2b105e32f8
)
managed=(
  author/main.py
  author/store.py
  author/web_features.py
  author/speech.py
  author/publishing.py
  author/review_engine.py
  author/review_cache.py
  author/review_history.py
  author/voice_reader.py
  author/commands.py
  author/commands_client.py
  author/control_socket.py
  the-web/shell/main.py
  the-web/shell/webbie_panel.py
  the-web/shell/webbie_overlay.py
  the-web/shell/webbie_camera.py
  the-web/shell/webbie_faces.py
  the-web/shell/webbie_face_profiles_ui.py
  the-web/shell/webbie_vision_bridge.py
  webbie/agent/vision_query.py
  webbie/agent/author_voice_bridge.py
  webbie/agent/webbie.py
)
if [[ $mode == --apply && $EUID -ne 0 ]]; then
    echo 'Use sudo bash ... --apply from your normal Spider OS user.' >&2
    exit 2
fi
if [[ $mode == --apply && -z ${SUDO_USER:-} ]]; then
    echo 'Run sudo from the signed-in Spider OS account, not a root shell.' >&2
    exit 2
fi
command -v git >/dev/null || { echo 'Missing git.' >&2; exit 2; }
command -v python3 >/dev/null || { echo 'Missing python3.' >&2; exit 2; }
command -v cmp >/dev/null || { echo 'Missing cmp.' >&2; exit 2; }
command -v ffmpeg >/dev/null || { echo 'Webcam vision requires ffmpeg. Install the Ubuntu ffmpeg package first.' >&2; exit 2; }
git -c "safe.directory=$source_root" -C "$source_root" rev-parse --is-inside-work-tree >/dev/null ||
  { echo 'Run from a GitHub worktree of Spider OS.' >&2; exit 2; }

tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT
blocked=0
for relative in "${managed[@]}"; do
    src="$source_root/$relative"
    installed="$root/$relative"
    if [[ ! -s "$src" || -L "$src" ]]; then
        echo "BLOCKED: missing or symlinked source: $relative"
        blocked=1
        continue
    fi
    if ! RELATIVE="$src" python3 - <<'PY'
import ast, os
from pathlib import Path
ast.parse(Path(os.environ['RELATIVE']).read_text(encoding='utf-8'))
PY
    then
        echo "BLOCKED: Python source syntax failed: $relative"
        blocked=1
        continue
    fi
    if [[ -L "$installed" ]]; then
        echo "BLOCKED: installed file is a symlink: $relative"
        blocked=1
        continue
    fi
    if [[ ! -e "$installed" ]]; then
        echo "READY: add new module $relative"
        continue
    fi
    if cmp -s -- "$installed" "$src"; then
        echo "CURRENT: $relative"
        continue
    fi
    recognized=0
    for baseline in "${baseline_refs[@]}"; do
        if git -c "safe.directory=$source_root" -C "$source_root" show "$baseline:$relative" > "$tmp/reference" 2>/dev/null &&
           cmp -s -- "$installed" "$tmp/reference"; then
            recognized=1
            break
        fi
    done
    if [[ $recognized -eq 1 ]]; then
        echo "READY: upgrade recognized desktop module $relative"
    else
        echo "BLOCKED: local customized or unknown module $relative; preserving it"
        blocked=1
    fi
done
if (( blocked )); then
    echo
    echo 'No system files changed. Review BLOCKED paths before upgrading.'
    exit 3
fi

if [[ $mode == --check ]]; then
    echo
    echo 'CHECK PASSED: supported source and installed versions.'
    echo 'No system, Webbie service, library, manuscript, account, or original DOCX file changed.'
    exit 0
fi

# Back up managed application code before any writes. No changes to user data.
stamp="$(date +%Y%m%d-%H%M%S)"
backup="$root/upgrade-backups/author-webbie-$stamp"
install -d -m 0755 -- "$backup"
for relative in "${managed[@]}"; do
    installed="$root/$relative"
    if [[ -f "$installed" ]]; then
        install -d -m 0755 -- "$backup/$(dirname "$relative")"
        cp -a -- "$installed" "$backup/$relative"
    fi
done

# Recheck after backing up so concurrent local customizations are not lost.
for relative in "${managed[@]}"; do
    installed="$root/$relative"
    src="$source_root/$relative"
    if [[ -f "$installed" && ! -f "$backup/$relative" ]]; then
        echo "Concurrent change detected: $relative. Aborting." >&2; exit 4
    fi
    if [[ -f "$installed" && ! -L "$installed" ]]; then
        if ! cmp -s "$installed" "$backup/$relative"; then
            echo "Concurrent modification detected: $relative. Aborting." >&2; exit 4
        fi
    fi
done
for relative in "${managed[@]}"; do
    installed="$root/$relative"
    src="$source_root/$relative"
    if [[ -f "$installed" ]] && cmp -s "$src" "$installed"; then
        continue
    fi
    install -d -m 0755 -- "$(dirname "$installed")"
    staging="$(mktemp "$(dirname "$installed")/.author-webbie.XXXXXXXX")"
    install -m 0644 -- "$src" "$staging"
    mv -f -- "$staging" "$installed"
    echo "Installed: $relative"
done
# Write the rollback record only after all managed code copies succeeded.
# Names are a fixed, audited list; never include user document paths.
manifest="$backup/rollback-manifest.tsv"
for relative in "${managed[@]}"; do
    if [[ -f "$backup/$relative" ]]; then
        action=existing
    else
        action=new
    fi
    sha="$(sha256sum -- "$root/$relative" | cut -d' ' -f1)"
    printf '%s\t%s\t%s\n' "$relative" "$action" "$sha" >> "$manifest"
done
chmod 0600 "$manifest"
echo
echo "Author/Webbie code upgraded. Safe backup: $backup"
echo "To inspect recovery: sudo bash $source_root/the-web/package/rollback-author-webbie.sh --check $backup"
echo 'The active desktop stays running. Save your work and log out later to load the upgraded UI.'
echo 'Webcam vision uses locally installed Ollama gemma3:4b. The microphone configuration is unchanged.'
echo 'Private manuscripts, Webbie voice service, photos, documents and original DOCX files were untouched.'
