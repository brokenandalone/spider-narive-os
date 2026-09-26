#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ISO="${ROOT_DIR}/build/spider-narive-os.iso"

[[ -f "$ISO" ]] || { echo "ISO not found; run ./scripts/build.sh first" >&2; exit 1; }
exec qemu-system-x86_64 -cdrom "$ISO" -m 128M -serial stdio
