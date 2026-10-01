#!/usr/bin/env bash
set -euo pipefail
spider_target_root="${1:?Pass the extracted installed-system root}"

for file in \
    usr/lib/systemd/system/ollama.service \
    usr/local/lib/spider-os/study/study.py \
    usr/local/lib/spider-os/forage/engine.py \
    usr/local/lib/spider-os/webbie/voice/whisper_listener.py \
    usr/local/share/spider-os/whisper/ggml-base.en.bin \
    usr/share/applications/study.desktop \
    etc/spider-os-release \
    etc/os-release \
    usr/lib/systemd/system/spider-os.service \
    usr/lib/systemd/user/webbie.service \
    etc/xdg/autostart/the-web.desktop \
    usr/share/applications/the-web.desktop \
    etc/skel/.config/autostart/the-web.desktop \
    usr/share/backgrounds/spider-os-wallpaper.png
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
    the-web/shell/main.py
do
    test -x "${spider_target_root}/usr/local/lib/spider-os/${file}"
done

test -x "${spider_target_root}/usr/bin/ollama"
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
