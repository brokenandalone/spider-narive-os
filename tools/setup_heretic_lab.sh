#!/usr/bin/env bash
# Explicit OPTIONAL Heretic setup, isolated to user's home. No Spider OS install.
set -euo pipefail
umask 077
VENV="$HOME/.local/share/spider-os/heretic-venv"
case "${1:---check}" in
  --check)
    echo "Webbie Heretic AI research lab (optional)"
    echo "Official source: https://github.com/p-e-w/heretic"
    echo "AGPL-3.0-or-later; installation location: $VENV"
    if [[ -x "$VENV/bin/heretic" && ! -L "$VENV/bin/heretic" ]]; then
      echo "Heretic executable present. Inspect from Webbie Cognitive Center."
    else
      echo "Heretic not installed. To opt in: bash tools/setup_heretic_lab.sh --install"
    fi
    exit 0
    ;;
  --install) ;;
  *) echo "Use --check or --install" >&2; exit 2 ;;
esac
echo 'This downloads heavyweight PyTorch/Heretic dependencies into an isolated venv.'
echo 'It does NOT switch Webbie or install a new system service.'
echo 'Heretic experiments can later download models and may offer a public upload.'
read -r -p 'Type INSTALL HERETIC to opt in: ' consent
[[ "$consent" == 'INSTALL HERETIC' ]] || { echo 'Cancelled.'; exit 1; }
if [[ -L "$HOME/.local/share/spider-os" || -L "$VENV" ]]; then
  echo 'Refusing symlinked installation directory' >&2
  exit 1
fi
free_kib="$(df -Pk "$HOME" | awk 'NR==2 {print $4}')"
if [[ ! "$free_kib" =~ ^[0-9]+$ || "$free_kib" -lt 26214400 ]]; then
  echo 'Need at least 25 GiB free disk before installation' >&2
  exit 1
fi
command -v python3 >/dev/null || { echo 'Python3 is required' >&2; exit 1; }
if [[ ! -x "$VENV/bin/python" ]]; then
  mkdir -p "$(dirname "$VENV")"
  python3 -m venv "$VENV"
fi
"$VENV/bin/python" -m pip --version >/dev/null || {
  echo 'This Python venv lacks pip. Install a supported python3-venv separately.' >&2
  exit 1
}
"$VENV/bin/python" -m pip install --no-input heretic-llm
[[ -x "$VENV/bin/heretic" ]] || { echo 'Heretic CLI not found' >&2; exit 1; }
echo 'Heretic is available in its isolated lab. Open Webbie > Cognitive Center > Heretic model lab.'
echo 'Ollama, voice, native bays and Webbie service were NOT modified.'
