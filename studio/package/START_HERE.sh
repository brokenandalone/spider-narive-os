#!/bin/sh
# Explicit first-run setup for a versioned native Linux beta.
# Double-click this file and choose Run; nothing installs automatically.
set -eu
STUDIO_BUNDLE=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P)
exec python3 "$STUDIO_BUNDLE/installer_gui.py"
