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
# Reject incomplete packages before installing dependencies or changing files.
for relative in the-web/shell/main.py the-web/shell/system_panel.py the-web/shell/system_status.py the-web/shell/webbie_panel.py the-web/shell/media_panel.py the-web/shell/media_transport.py the-web/shell/audio_controls.py the-web/shell/build_info.py branding/webbie/webbie-face-v1.png branding/webbie/webbie-face-speaking-v1.png the-web/session/the-web-session the-web/session/apply-lock-screen.py the-web/package/patch-native-imports.py the-web/package/reconcile-native.py branding/wallpapers/collection.json distro/config/sessions/the-web.desktop system/apps.py; do
    test -s "$source_root/$relative" || { echo "Incomplete build: $relative" >&2; exit 1; }
done
if [[ -f "$source_root/SHA256SUMS" ]]; then
    (cd "$source_root" && sha256sum --strict -c SHA256SUMS) || { echo 'Build checksum verification failed.' >&2; exit 1; }
fi
if ! command -v startplasma-x11 >/dev/null; then
    # Ubuntu 25.10/26.04 split the X11 session out of plasma-workspace.
    candidate="$(apt-cache policy plasma-session-x11 | sed -n 's/^[[:space:]]*Candidate: //p')"
    if [[ -n "$candidate" && "$candidate" != '(none)' ]]; then
        apt-get install -y plasma-session-x11 kwin-x11
    else
        echo 'Missing KDE X11 session. Install plasma-session-x11 and kwin-x11 using your Ubuntu package sources, then retry.' >&2
        exit 1
    fi
fi
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
for relative in the-web/shell the-web/install-receipt.json branding/webbie author/main.py studio/main.py study/study.py system/apps.py; do
    if [[ -e "$root/$relative" ]]; then
        install -d "$backup/$(dirname "$relative")"
        cp -a "$root/$relative" "$backup/$relative"
    fi
done
cp -a "$source_root/the-web/shell" "$root/the-web/"
cp -a "$source_root/the-web/session" "$root/the-web/"
install -Dm644 "$source_root/branding/webbie/webbie-face-v1.png" "$root/branding/webbie/webbie-face-v1.png"
install -Dm644 "$source_root/branding/webbie/webbie-face-speaking-v1.png" "$root/branding/webbie/webbie-face-speaking-v1.png"
cp -a "$source_root/branding/wallpapers/collection" "$root/branding/wallpapers/"
install -m644 "$source_root/branding/wallpapers/collection.json" "$root/branding/wallpapers/collection.json"
# Existing original backgrounds are retained. Supply only missing required assets.
for relative in branding/wallpapers/spider-os-wallpaper.png branding/splash/spider-os-splash.png branding/icons/spider-os-logo.png; do
    if [[ ! -s "$root/$relative" ]]; then install -Dm644 "$source_root/$relative" "$root/$relative"; fi
done
# Fill missing workspace originals without replacing installed backgrounds.
for image in "$source_root"/branding/workspaces/*.png; do
    [[ -f "$image" ]] || continue
    target="$root/branding/workspaces/$(basename "$image")"
    if [[ ! -s "$target" ]]; then install -Dm644 "$image" "$target"; fi
done
# Reconcile partially installed workspaces file-by-file. A pre-existing directory
# does not mean new Author, Studio or APA modules exist. Never replace existing
# owner files, project databases, manuscripts or application customizations.
for workspace in author studio study; do
    source_dir="$source_root/$workspace"
    [[ -d "$source_dir" ]] || continue
    while IFS= read -r -d '' candidate; do
        relative="${candidate#"$source_dir/"}"
        case "$relative" in *.py|bin/*) ;; *) continue ;; esac
        target="$root/$workspace/$relative"
        if [[ ! -e "$target" && ! -L "$target" ]]; then
            install -d "$(dirname "$target")"
            cp -a -- "$candidate" "$target"
            printf 'Added missing %s source: %s\n' "$workspace" "$relative"
        fi
    done < <(find "$source_dir" -type f -print0)
done
if [[ ! -f "$root/system/apps.py" ]]; then install -Dm644 "$source_root/system/apps.py" "$root/system/apps.py"; fi
# The owner's known nine-line Author launcher difference and Studio spacing
# customizations can be reconciled exactly. Unknown differences are skipped.
if ! python3 "$source_root/the-web/package/reconcile-native.py" "$source_root" "$root"; then
    echo 'One or more native workspaces needs a manual code review; existing files were preserved.' >&2
fi
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
python3 "$root/the-web/shell/build_info.py" "$source_root" "$root" "$backup"
if ! runuser -u "$user" -- python3 "$root/the-web/session/apply-lock-screen.py"; then
    echo 'Desktop installed; lock-screen artwork could not be applied. The secure KDE locker is unchanged.' >&2
fi
printf 'Installed The Web desktop. Backup: %s\nLog out, then choose The Web (X11). Plasma remains available.\n' "$backup"
