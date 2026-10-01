#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Features are integrated in the builder; validate without rewriting project files.
exec bash "${ROOT}/distro/validate-feature-complete.sh"
