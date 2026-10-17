#!/usr/bin/env bash
# One owner-approved Qwen3-8B-Heretic Q4 install into existing local Ollama.
# No root, separate Webbie, service restart, cloud credential or tool-permission change.
set -euo pipefail
umask 077
if [[ "${1:-}" != '--approved-by-owner' || $# -ne 1 ]]; then
  echo 'Start this through Webbie Cognitive Center, or explicitly supply --approved-by-owner.' >&2
  exit 2
fi
MODEL='hf.co/mradermacher/Qwen3-8B-heretic-GGUF:Q4_K_M'
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
ACTIVATE="$ROOT/tools/activate_heretic_brain.py"
if [[ ! -f "$ACTIVATE" || -L "$ACTIVATE" ]]; then
  echo 'Reviewed activation helper unavailable. Original Webbie unchanged.' >&2
  exit 1
fi
command -v ollama >/dev/null || { echo 'Local Ollama command missing.' >&2; exit 1; }
command -v python3 >/dev/null || { echo 'Python 3 missing.' >&2; exit 1; }
command -v flock >/dev/null || { echo 'flock missing.' >&2; exit 1; }
LOCK_DIR="$HOME/.cache/spider-os"
if [[ -L "$LOCK_DIR" ]]; then
  echo 'Unsafe model download lock path.' >&2; exit 1
fi
mkdir -p -m 700 "$LOCK_DIR"
exec 9>"$LOCK_DIR/heretic-install.lock"
flock -n 9 || { echo 'Another Heretic download is already running.' >&2; exit 1; }
echo 'Using quantized Q4_K_M model from Hugging Face community repository.'
echo "Model: $MODEL"
echo 'Source: https://huggingface.co/mradermacher/Qwen3-8B-heretic-GGUF'
echo 'Upstream modified model: https://huggingface.co/p-e-w/Qwen3-8B-heretic'
echo 'Original qwen3:8b stays installed for fallback.'
free_kib="$(df -Pk "$HOME" | awk 'NR==2{print $4}')"
if [[ ! "$free_kib" =~ ^[0-9]+$ || "$free_kib" -lt 10485760 ]]; then
  echo 'Need at least 10 GiB free disk before fetching ~5 GiB model.' >&2
  exit 1
fi
if ! ollama show "$MODEL" >/dev/null 2>&1; then
  echo 'Downloading approved ~5 GiB model to Ollama. This can take time.'
  ollama pull "$MODEL"
else
  echo 'Reviewed Heretic model is already installed in local Ollama.'
fi
python3 "$ACTIVATE" --owner-approved-install
echo 'Heretic is now selected for NORMAL Webbie conversation after source deployment.'
echo 'To restore original: Webbie Cognitive Center > My everyday AI brain > Use original.'
