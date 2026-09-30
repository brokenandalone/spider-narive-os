#!/usr/bin/env bash
set -euo pipefail
spider_target_root="${1:?Pass the extracted installed-system root}"

for file in \
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

test -L "${spider_target_root}/etc/systemd/system/multi-user.target.wants/spider-os.service"
test -L "${spider_target_root}/etc/systemd/user/default.target.wants/webbie.service"
grep -q '^NAME="Spider OS"$' "${spider_target_root}/etc/os-release"
grep -q '^WantedBy=multi-user.target$' "${spider_target_root}/usr/lib/systemd/system/spider-os.service"
if grep -q 'After=.*graphical.target' "${spider_target_root}/usr/lib/systemd/system/spider-os.service"; then
    echo "Spider Core still has a graphical-target ordering cycle" >&2
    exit 1
fi
echo "Installed Spider OS payload checks passed."
