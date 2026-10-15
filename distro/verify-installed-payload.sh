#!/usr/bin/env bash
set -euo pipefail
spider_target_root="${1:?Pass the extracted installed-system root}"

for file in \
    usr/local/lib/spider-os/spider_max_source/spider_monster/max_catalog.py \
    usr/local/lib/spider-os/the-web/shell/immersive_bays.py \
    usr/local/lib/spider-os/author/main.py \
    usr/local/lib/spider-os/media/ai-dj/nova_voice.py \
    usr/lib/systemd/system/ollama.service \
    usr/local/lib/spider-os/study/study.py \
    usr/local/lib/spider-os/system/guardian.py \
    usr/local/lib/spider-os/system/vault.py \
    usr/local/lib/spider-os/system/apps.py \
    usr/local/lib/spider-os/webbie/actions/gateway.py \
    usr/local/lib/spider-os/studio/main.py \
    usr/share/applications/studio.desktop \
    usr/share/applications/author.desktop \
    usr/local/lib/spider-os/forage/engine.py \
    usr/local/lib/spider-os/forage/local_index.py \
    usr/local/lib/spider-os/webbie/voice/whisper_listener.py \
    usr/local/share/spider-os/whisper/ggml-base.en.bin \
    usr/share/applications/study.desktop \
    etc/spider-os-release \
    etc/os-release \
    usr/lib/systemd/system/spider-os.service \
    usr/lib/systemd/user/webbie.service \
    etc/xdg/autostart/the-web.desktop \
    usr/share/xsessions/the-web.desktop \
    usr/local/bin/the-web-session \
    usr/local/lib/spider-os/the-web/shell/desktop.py \
    usr/local/lib/spider-os/the-web/shell/workspaces.py \
    usr/local/lib/spider-os/the-web/shell/app_catalog.py \
    usr/local/lib/spider-os/the-web/shell/wallpapers.py \
    usr/local/lib/spider-os/branding/wallpapers/collection.json \
    etc/skel/.config/autostart/the-web.desktop \
    usr/share/backgrounds/spider-os-wallpaper.png \
    usr/share/spider-os/branding/selected-startup-set \
    usr/share/spider-os/branding/spider-os-splash.png \
    usr/share/spider-os/branding/startup-background.png \
    usr/share/spider-os/startup-sets/spider-purple.png \
    usr/share/spider-os/startup-sets/spider-crimson.png \
    usr/share/spider-os/startup-sets/spider-nightfall.png \
    usr/share/plasma/look-and-feel/org.spider.os/metadata.json \
    usr/share/plasma/look-and-feel/org.spider.os/contents/splash/Splash.qml \
    usr/share/plasma/look-and-feel/org.spider.os/contents/splash/images/background.png \
    etc/xdg/ksplashrc \
    usr/share/sddm/themes/breeze/theme.conf.user
do
    test -s "${spider_target_root}/${file}" || {
        echo "Missing installed Spider OS file: ${file}" >&2
        exit 1
    }
done

for file in \
    spider-core/bin/spider-core \
    webbie/webbie \
    webbie/agent/webbie.py \
    webbie/actions/webbie-action \
    the-web/shell/main.py \
    studio/bin/studio \
    author/bin/author \
    media/bin/spider-media-center
do
    test -x "${spider_target_root}/usr/local/lib/spider-os/${file}"
done

test -x "${spider_target_root}/usr/bin/ollama"
test -x "${spider_target_root}/usr/local/bin/the-web-session"
if [[ -e "${spider_target_root}/usr/share/applications/the-web.desktop" ]]; then
    echo 'The Web still has the old application-menu entry' >&2
    exit 1
fi
grep -q '^Exec=/usr/local/bin/the-web-session$' "${spider_target_root}/usr/share/xsessions/the-web.desktop"
python3 - "${spider_target_root}/usr/local/lib/spider-os" <<'PY'
import hashlib, json, sys
from pathlib import Path
root = Path(sys.argv[1]).resolve()
catalog = json.loads((root / 'branding/wallpapers/collection.json').read_text())
for entry in catalog['wallpapers']:
    image = (root / entry['file']).resolve()
    if not image.is_relative_to(root) or not image.is_file():
        raise SystemExit('Missing or unsafe packaged wallpaper')
    if hashlib.sha256(image.read_bytes()).hexdigest() != entry['sha256']:
        raise SystemExit('Packaged wallpaper checksum mismatch')
PY
test -x "${spider_target_root}/usr/local/bin/whisper-cli"
test -x "${spider_target_root}/opt/spider-webbie/bin/edge-tts"
test -L "${spider_target_root}/etc/systemd/system/multi-user.target.wants/ollama.service"
test -L "${spider_target_root}/etc/systemd/system/multi-user.target.wants/spider-os.service"
test -L "${spider_target_root}/etc/systemd/user/default.target.wants/webbie.service"
grep -q '^NAME="Spider OS"$' "${spider_target_root}/etc/os-release"
grep -q '^WantedBy=multi-user.target$' "${spider_target_root}/usr/lib/systemd/system/spider-os.service"
if grep -q 'After=.*graphical.target' "${spider_target_root}/usr/lib/systemd/system/spider-os.service"; then
    echo "Spider Core still has a graphical-target ordering cycle" >&2
    exit 1
fi
for image in art-lab dev-bay forage kali-bay media recovery studio study system; do
    test -s "${spider_target_root}/usr/local/lib/spider-os/branding/workspaces/${image}.png"
done
echo "Installed Spider OS payload checks passed."
