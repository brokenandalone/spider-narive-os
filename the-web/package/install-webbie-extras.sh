#!/usr/bin/env bash
# Safe ADD-ON installer: keep the working Plasma/The Web/agent untouched.
set -Eeuo pipefail
source_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
if [[ ! -d "$source_root/the-web/overlay" ]]; then
  echo "Incomplete Webbie add-on package." >&2; exit 1
fi
for file in the-web/overlay/webbie_face.py the-web/overlay/webbie-face-autostart.desktop system/onedrive.py system/service/webbie-onedrive.service system/service/webbie-onedrive.timer branding/webbie/webbie-face-v1.png branding/webbie/webbie-face-speaking-v1.png; do
  [[ -s "$source_root/$file" ]] || { echo "Missing: $file" >&2; exit 1; }
done
# No boot, encryption, agent, existing shell or private-data changes.
if [[ "${1:-}" == --check ]]; then
  python3 - "$source_root" <<'PY'
import ast, pathlib, sys
root = pathlib.Path(sys.argv[1])
for name in ('the-web/overlay/webbie_face.py', 'system/onedrive.py'):
    ast.parse((root / name).read_text(), filename=name)
print('PASS: Webbie add-on source syntax and package files present.')
PY
  exit 0
fi
if [[ "$EUID" -ne 0 || -z "${SUDO_USER:-}" || "${SUDO_USER:-}" == root ]]; then
  echo "Run with sudo from your normal Spider OS user account." >&2; exit 1
fi
user="$SUDO_USER"
home="$(getent passwd "$user" | cut -d: -f6)"
group="$(id -gn "$user")"
root=/usr/local/lib/spider-os
stamp="$(date +%Y%m%d-%H%M%S)"
backup="$root/upgrade-backups/webbie-accessories-$stamp"
install -d "$backup"
for relative in the-web/overlay/webbie_face.py system/onedrive.py branding/webbie/webbie-face-v1.png branding/webbie/webbie-face-speaking-v1.png; do
  if [[ -f "$root/$relative" ]]; then
    install -d "$backup/$(dirname "$relative")"
    cp -a -- "$root/$relative" "$backup/$relative"
  fi
done
for name in webbie-onedrive.service webbie-onedrive.timer; do
  if [[ -e "/usr/lib/systemd/user/$name" ]]; then
    cp -a "/usr/lib/systemd/user/$name" "$backup/$name"
  fi
done
if [[ -f "$home/.config/autostart/webbie-floating-face.desktop" ]]; then
  cp -a "$home/.config/autostart/webbie-floating-face.desktop" "$backup/user-webbie-floating-face.desktop"
fi
install -Dm755 "$source_root/the-web/overlay/webbie_face.py" "$root/the-web/overlay/webbie_face.py"
install -Dm755 "$source_root/system/onedrive.py" "$root/system/onedrive.py"
install -Dm644 "$source_root/the-web/overlay/webbie-face-autostart.desktop" "$root/the-web/overlay/webbie-face-autostart.desktop"
for item in webbie-face-v1.png webbie-face-speaking-v1.png; do
  target="$root/branding/webbie/$item"
  if [[ ! -s "$target" ]]; then
    install -Dm644 "$source_root/branding/webbie/$item" "$target"
  fi
done
for name in webbie-onedrive.service webbie-onedrive.timer; do
  install -Dm644 "$source_root/system/service/$name" "/usr/lib/systemd/user/$name"
done
install -d -o "$user" -g "$group" "$home/.config/autostart"
autostart="$home/.config/autostart/webbie-floating-face.desktop"
if [[ ! -e "$autostart" && ! -L "$autostart" ]]; then
  install -o "$user" -g "$group" -m644 "$source_root/the-web/overlay/webbie-face-autostart.desktop" "$autostart"
else
  echo "Preserved existing Webbie overlay autostart override."
fi
uid="$(id -u "$user")"
if [[ -S "/run/user/$uid/bus" ]]; then
  runuser -u "$user" -- env XDG_RUNTIME_DIR="/run/user/$uid" \
    DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$uid/bus" \
    systemctl --user daemon-reload || true
  if ! runuser -u "$user" -- env XDG_RUNTIME_DIR="/run/user/$uid" \
    DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$uid/bus" \
    systemctl --user enable --now webbie-onedrive.timer; then
    echo "Run without sudo: systemctl --user enable --now webbie-onedrive.timer"
  fi
else
  echo "After login run: systemctl --user enable --now webbie-onedrive.timer"
fi
echo "Webbie X11 overlay and deferred OneDrive adapter installed."
echo "Backup: $backup"
echo "No voice agent, desktop shell, login, boot, manuscripts or existing user files were replaced."
echo "Sign out/in once for the portrait to autostart. OneDrive sign-in is OPTIONAL."
