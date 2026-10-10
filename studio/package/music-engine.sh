#!/usr/bin/env bash
# User-local ACE-Step setup for Spider Studio. No sudo, OS package changes or service edits.
set -euo pipefail

mode="${1:---check}"
if [[ $# -gt 1 || ! "$mode" =~ ^--(check|install|start|help)$ ]]; then
    echo "Usage: bash studio/package/music-engine.sh [--check|--install|--start|--help]" >&2
    exit 2
fi

engine_dir="${XDG_DATA_HOME:-$HOME/.local/share}/spider-os/music-engine/ACE-Step-1.5"
official_repo="https://github.com/ACE-Step/ACE-Step-1.5.git"

if [[ "$mode" == --help ]]; then
    cat <<'EOF'
Spider Studio local music engine
  --check     Read-only check of tools, GPU, disk and the loopback API (default)
  --install   Explicitly clone ACE-Step and install its Python environment in your home folder
  --start     Explicitly run the local ACE-Step API in the foreground (may download model weights)

No OS packages, Webbie settings, systemd units or existing music files are modified.
Install requires git and uv already available. Models may require 10+ GB on first start.
The app uses http://127.0.0.1:8001 by default. Stop the engine using Ctrl+C.
EOF
    exit 0
fi

if [[ "$mode" == --check ]]; then
    echo "Spider Studio local engine readiness (read-only)"
    echo "Engine folder: $engine_dir"
    for executable in git uv python3; do
        if command -v "$executable" >/dev/null 2>&1; then
            echo "PASS: $executable found"
        else
            echo "MISSING: $executable"
        fi
    done
    if command -v nvidia-smi >/dev/null 2>&1; then
        nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || true
    elif command -v lspci >/dev/null 2>&1; then
        echo "Graphics devices:"
        lspci | grep -Ei 'vga|3d controller|display controller' || true
        echo "GPU/VRAM suitability is NOT established by device listing."
    else
        echo "GPU inventory unavailable (install pciutils or use device settings)."
    fi
    df -h "$HOME" | tail -n 1
    if [[ -d "$engine_dir/.git" ]]; then
        echo "ACE-Step checkout: present (inspect version and model compatibility before use)"
    else
        echo "ACE-Step checkout: not installed at Spider Studio's managed location"
    fi
    if command -v python3 >/dev/null 2>&1; then
        python3 - <<'PY'
import json
from urllib.request import build_opener, ProxyHandler, Request
try:
    opener = build_opener(ProxyHandler({}))
    with opener.open(Request('http://127.0.0.1:8001/health'), timeout=2) as response:
        data = json.loads(response.read(65536))
    healthy = isinstance(data, dict) and data.get('code') == 200 and isinstance(data.get('data'), dict) and data['data'].get('status') == 'ok'
    print('Local API health:', 'ready' if healthy else 'unrecognized response')
except Exception:
    print('Local API health: unavailable (engine may not be started)')
PY
    fi
    echo "Hardware inventory does not prove that ACE-Step will produce a usable render."
    exit 0
fi

if ! command -v uv >/dev/null 2>&1 || ! command -v git >/dev/null 2>&1; then
    echo "Install git and uv using their official documentation before proceeding." >&2
    exit 2
fi

if [[ "$mode" == --install ]]; then
    if [[ -e "$engine_dir" && ! -d "$engine_dir/.git" ]]; then
        echo "Refusing to overwrite the existing path: $engine_dir" >&2
        exit 2
    fi
    if [[ ! -d "$engine_dir/.git" ]]; then
        mkdir -p "$(dirname "$engine_dir")"
        git clone --depth 1 "$official_repo" "$engine_dir"
    fi
    remote="$(git -C "$engine_dir" remote get-url origin)"
    if [[ "$remote" != "$official_repo" ]]; then
        echo "Refusing an unverified ACE-Step checkout: $remote" >&2
        exit 2
    fi
    echo "Installing ACE-Step's isolated Python dependencies. This may download significant data."
    (cd "$engine_dir" && uv sync)
    echo "Engine Python environment prepared. Start explicitly using: bash studio/package/music-engine.sh --start"
    exit 0
fi

if [[ ! -f "$engine_dir/pyproject.toml" || ! -d "$engine_dir/.git" ]]; then
    echo "No prepared ACE-Step checkout; run --install first." >&2
    exit 2
fi
remote="$(git -C "$engine_dir" remote get-url origin)"
if [[ "$remote" != "$official_repo" ]]; then
    echo "Refusing to run an unverified ACE-Step checkout." >&2
    exit 2
fi
echo "Starting ACE-Step on loopback only. First start may download large model weights."
cd "$engine_dir"
exec env ACESTEP_API_HOST=127.0.0.1 ACESTEP_API_PORT=8001 uv run acestep-api
