#!/usr/bin/env bash
# Optional, isolated RVC training UI preparation. No sudo or OS service edits.
set -euo pipefail

mode="${1:---check}"
if [[ $# -gt 1 ]] || [[ ! "$mode" =~ ^--(help|check|clone|prepare-cpu|launch-local)$ ]]; then
    echo "Usage: voice-engine.sh [--help|--check|--clone|--prepare-cpu|--launch-local]" >&2
    exit 2
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source_root="$(cd -- "$script_dir/../.." && pwd)"
rvc_root="${XDG_DATA_HOME:-$HOME/.local/share}/spider-os/voice-engine/Retrieval-based-Voice-Conversion-WebUI"
remote_url="https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI.git"

if [[ "$mode" == --help ]]; then
    cat <<'EOF'
Spider Studio: locally trained My Voice
  --check        Read-only inventory of Python, ffmpeg, GPU and local RVC installation
  --clone        Explicitly clone RVC to your private home data folder, no downloads of models
  --prepare-cpu  Explicitly install RVC Python dependencies in its own venv (large download)
  --launch-local Start RVC's training WebUI on LOOPBACK only; manual consented training

IMPORTANT:
  The standard upstream RVC WebUI binds publicly; Spider Studio refuses to
  launch that original file. A known-source copy is patched for 127.0.0.1.
  Training and model downloads may consume many gigabytes and take hours.
  Do not run commands from strangers or load untrusted .pth model files.
  --check does not modify packages, models, Webbie or boot.
EOF
    exit 0
fi

if [[ "$mode" == --check ]]; then
    echo "RVC local training readiness (read-only)"
    for utility in git python3.12 ffmpeg ffprobe; do
        if command -v "$utility" >/dev/null 2>&1; then
            echo "PASS: $utility"
        else
            echo "MISSING: $utility"
        fi
    done
    if command -v nvidia-smi >/dev/null 2>&1; then
        nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || true
    elif command -v lspci >/dev/null 2>&1; then
        lspci | grep -Ei 'vga|3d controller|display controller' || true
    fi
    df -h "$HOME" | tail -n 1
    if [[ -f "$rvc_root/webui.py" ]]; then
        echo "RVC checkout: present at $rvc_root"
    else
        echo "RVC checkout: not prepared"
    fi
    if [[ -x "$rvc_root/.venv/bin/python" ]]; then
        echo "Isolated Python interpreter: present (does not prove all RVC dependencies installed)"
    else
        echo "Isolated Python interpreter: not prepared"
    fi
    echo "A private singing dataset, trained .pth and RVC index are all separate steps."
    exit 0
fi

if ! command -v git >/dev/null 2>&1; then
    echo "Git is needed for the official RVC checkout." >&2
    exit 2
fi

if [[ "$mode" == --clone ]]; then
    if [[ -e "$rvc_root" && ! -d "$rvc_root/.git" ]]; then
        echo "Refusing to replace an existing non-RVC folder: $rvc_root" >&2
        exit 2
    fi
    if [[ ! -d "$rvc_root/.git" ]]; then
        mkdir -p "$(dirname "$rvc_root")"
        git clone --depth 1 "$remote_url" "$rvc_root"
    fi
    echo "RVC checkout prepared. Model weights and Python dependencies are not installed."
    exit 0
fi

if [[ ! -f "$rvc_root/webui.py" || ! -d "$rvc_root/.git" ]]; then
    echo "Run --clone first; refusing to use an unknown voice engine." >&2
    exit 2
fi
origin="$(git -C "$rvc_root" remote get-url origin)"
if [[ "$origin" != "$remote_url" ]]; then
    echo "Refusing an unrecognized RVC repository origin." >&2
    exit 2
fi

if [[ "$mode" == --prepare-cpu ]]; then
    if ! command -v python3.12 >/dev/null 2>&1; then
        echo "This RVC version needs Python 3.12; no host packages will be changed." >&2
        exit 2
    fi
    if [[ ! -f "$rvc_root/requirments_cpu_py312.txt" ]]; then
        echo "The pinned CPU dependency list is missing; refusing install." >&2
        exit 2
    fi
    echo "Installing isolated CPU-capable RVC dependencies. This explicitly downloads packages."
    python3.12 -m venv "$rvc_root/.venv"
    ( cd "$rvc_root" && .venv/bin/python -m pip install -r requirments_cpu_py312.txt )
    echo "Private Python environment prepared. Training models and source samples still required."
    exit 0
fi

if [[ "$mode" == --launch-local ]]; then
    if [[ ! -x "$rvc_root/.venv/bin/python" ]]; then
        echo "No isolated Python runtime: use --prepare-cpu or manually configure CUDA." >&2
        exit 2
    fi
    echo "Preparing RVC local-only UI from a verified source pattern (no public bind)."
    python3 "$source_root/studio/rvc_loopback.py" \
        "$rvc_root/webui.py" "$rvc_root/.spider-webui-local.py"
    echo "Launching localhost-only voice training at http://127.0.0.1:7865"
    echo "Use the RVC training interface to create your model from the prepared owner dataset."
    echo "RVC may choose another port if occupied. Never expose this service publicly."
    cd "$rvc_root"
    export PYTHONPATH="$rvc_root${PYTHONPATH:+:$PYTHONPATH}"
    exec "$rvc_root/.venv/bin/python" "$rvc_root/.spider-webui-local.py" --noautoopen
fi
