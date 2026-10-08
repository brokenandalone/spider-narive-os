#!/usr/bin/env bash
# Selective installed-PC upgrade. Does not replace Webbie or native workspace apps.
set -Eeuo pipefail
source_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
# Installed package/ is inside the-web/, hence parent-parent is the repository.
if [[ -d "$source_root/the-web" ]]; then :; else source_root="$(dirname "$source_root")"; fi
if [[ "${1:-}" == --check ]]; then
    for command in startplasma-x11 python3 dbus-send wmctrl systemctl; do
        command -v "$command" >/dev/null || { echo "Missing: $command" >&2; exit 1; }
    done
    python3 -c 'from PyQt5.QtWidgets import QApplication'
    echo 'Desktop prerequisites passed.'; exit 0
fi
if [[ $EUID -ne 0 ]]; then echo 'Run with sudo; this installs a selectable desktop session.' >&2; exit 1; fi
user="${SUDO_USER:-}"
if [[ -z "$user" || "$user" == root ]]; then echo 'Run sudo from your normal desktop account.' >&2; exit 1; fi
user_home="$(getent passwd "$user" | cut -d: -f6)"
root=/usr/local/lib/spider-os
for command in startplasma-x11 python3 dbus-send systemctl; do
    command -v "$command" >/dev/null || { echo "Missing desktop dependency: $command" >&2; exit 1; }
done
if ! command -v wmctrl >/dev/null || ! /usr/bin/python3 -c 'from PyQt5.QtWidgets import QApplication' >/dev/null 2>&1; then
    apt-get install -y wmctrl python3-pyqt5
fi
for relative in the-web/shell/main.py the-web/session/the-web-session branding/wallpapers/collection.json distro/config/sessions/the-web.desktop; do
    test -s "$source_root/$relative" || { echo "Incomplete build: $relative" >&2; exit 1; }
done
stamp="$(date +%Y%m%d-%H%M%S)"
backup="$root/upgrade-backups/the-web-$stamp"
install -d "$backup" "$root/the-web" "$root/branding/wallpapers" /usr/share/xsessions /usr/local/bin
for relative in the-web/shell author/main.py studio/main.py study/study.py; do
    if [[ -e "$root/$relative" ]]; then
        install -d "$backup/$(dirname "$relative")"
        cp -a "$root/$relative" "$backup/$relative"
    fi
done
cp -a "$source_root/the-web/shell" "$root/the-web/"
cp -a "$source_root/the-web/session" "$root/the-web/"
cp -a "$source_root/branding/wallpapers/collection" "$root/branding/wallpapers/"
install -m644 "$source_root/branding/wallpapers/collection.json" "$root/branding/wallpapers/collection.json"
# Existing original backgrounds are retained. Supply only missing required assets.
for relative in branding/wallpapers/spider-os-wallpaper.png branding/splash/spider-os-splash.png branding/icons/spider-os-logo.png; do
    if [[ ! -s "$root/$relative" ]]; then install -Dm644 "$source_root/$relative" "$root/$relative"; fi
done
# Supply missing native app source only. Never replace existing owner workspace code.
for workspace in author studio study; do
    if [[ ! -d "$root/$workspace" && -d "$source_root/$workspace" ]]; then cp -a "$source_root/$workspace" "$root/"; fi
done
if [[ ! -f "$root/system/apps.py" ]]; then install -Dm644 "$source_root/system/apps.py" "$root/system/apps.py"; fi
python3 "$source_root/the-web/package/patch-native-imports.py" "$root"
install -m755 "$source_root/the-web/session/the-web-session" /usr/local/bin/the-web-session
install -m644 "$source_root/distro/config/sessions/the-web.desktop" /usr/share/xsessions/the-web.desktop
# The Web belongs in the session chooser; remove its old app/autostart entries.
for entry in /etc/xdg/autostart/the-web.desktop /usr/share/applications/the-web.desktop; do
    if [[ -f "$entry" ]]; then cp -a "$entry" "$backup/$(basename "$(dirname "$entry")")-the-web.desktop"; rm "$entry"; fi
done
install -d -o "$user" -g "$(id -gn "$user")" "$user_home/.config/autostart"
if [[ -f "$user_home/.config/autostart/the-web.desktop" ]]; then
    cp -a "$user_home/.config/autostart/the-web.desktop" "$backup/user-the-web.desktop"
fi
printf '[Desktop Entry]\nType=Application\nName=The Web\nHidden=true\n' > "$user_home/.config/autostart/the-web.desktop"
chown "$user:$(id -gn "$user")" "$user_home/.config/autostart/the-web.desktop"
/usr/local/bin/the-web-session --check
if ! runuser -u "$user" -- python3 "$root/the-web/session/apply-lock-screen.py"; then
    echo 'Desktop installed; lock-screen artwork could not be applied. The secure KDE locker is unchanged.' >&2
fi
printf 'Installed The Web desktop. Backup: %s\nLog out, then choose The Web (X11). Plasma remains available.\n' "$backup"
