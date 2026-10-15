#!/usr/bin/env bash
# Stage Spider OS startup artwork in an extracted installed or live image.
# Does NOT modify the running host, rebuild initramfs, or change encryption.
set -Eeuo pipefail

target_root="$(realpath -m "$1")"
source_root="$(realpath "$2")"
set_name="${3:-spider-purple}"

case "$target_root" in
  /|/boot|/etc|/usr) echo "Refusing unsafe target root" >&2; exit 2 ;;
esac
test -d "$target_root"
test -f "$source_root/branding/splash/spider-os-splash.png"

case "$set_name" in
  spider-purple|spider-crimson|spider-nightfall) selected="$set_name" ;;
  *) echo "Unknown Spider startup set: $set_name" >&2; exit 2 ;;
esac

background_dir="$target_root/usr/share/spider-os/startup-sets"
mkdir -p "$background_dir"
install -m 644 "$source_root/branding/wallpapers/spider-os-wallpaper.png" "$background_dir/spider-purple.png"
install -m 644 "$source_root/branding/wallpapers/collection/distressed-crimson-spider-os-wallpaper-e799fd25.png" "$background_dir/spider-crimson.png"
install -m 644 "$source_root/branding/wallpapers/collection/neon-purple-grunge-spider-emblem-c882e8d5.png" "$background_dir/spider-nightfall.png"

install -Dm644 "$background_dir/$selected.png" \
  "$target_root/usr/share/spider-os/branding/startup-background.png"
install -Dm644 "$source_root/branding/splash/spider-os-splash.png" \
  "$target_root/usr/share/spider-os/branding/spider-os-splash.png"

# Keep the Breeze greeter and Plasma global theme, change the image only.
install -d "$target_root/usr/share/sddm/themes/breeze"
cat > "$target_root/usr/share/sddm/themes/breeze/theme.conf.user" <<'SDDM'
[General]
background=/usr/share/spider-os/branding/startup-background.png
SDDM

# A separate Plasma 6 startup splash, not an application launcher.
theme="$target_root/usr/share/plasma/look-and-feel/org.spider.os"
mkdir -p "$theme/contents/splash/images"
cat > "$theme/metadata.json" <<'META'
{
  "KPackageStructure": "Plasma/LookAndFeel",
  "KPlugin": {
    "Id": "org.spider.os",
    "Name": "Spider OS Startup",
    "Description": "Spider OS startup without changing the global theme",
    "Category": "Plasma Look And Feel",
    "License": "Proprietary",
    "Version": "1.0"
  }
}
META
cat > "$theme/contents/splash/Splash.qml" <<'QML'
import QtQuick

Rectangle {
    id: root
    color: "#08070d"
    property int stage: 0
    Image {
        anchors.fill: parent
        source: "images/background.png"
        fillMode: Image.PreserveAspectCrop
        asynchronous: false
    }
    Rectangle {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: Math.max(52, parent.height * 0.12)
        width: Math.min(parent.width * 0.44, 480)
        height: 3
        color: "#473057"
        Rectangle {
            width: parent.width * Math.max(0.08, Math.min(1, (root.stage + 1) / 7))
            height: parent.height
            color: "#a977e8"
        }
    }
    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: Math.max(19, parent.height * 0.06)
        text: "YOUR LIFE. ONE WEB."
        font.pixelSize: Math.max(12, Math.min(19, parent.height * 0.023))
        font.letterSpacing: 2
        color: "#eee7f5"
    }
}
QML
install -m 644 "$background_dir/$selected.png" "$theme/contents/splash/images/background.png"

# Default for new users; an existing user's ksplashrc takes precedence.
install -d "$target_root/etc/xdg"
cat > "$target_root/etc/xdg/ksplashrc" <<'KSPLASH'
[KSplash]
Theme=org.spider.os
Engine=KSplashQML
KSPLASH

# Plymouth activation and initramfs rebuild on encrypted hardware remain gated.
printf '%s\n' "$selected" > "$target_root/usr/share/spider-os/branding/selected-startup-set"
printf 'Staged Spider OS set %s in %s\n' "$selected" "$target_root"
