#!/usr/bin/env bash
# Inspect the actual output image, not only the directory that produced it.
set -Eeuo pipefail
[[ ${EUID} -eq 0 ]] || { echo 'Run ISO verification with sudo' >&2; exit 1; }
spider_iso="$(realpath "${1:?Pass the completed ISO}")"
spider_repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
spider_checks="$(mktemp -d)"
cleanup_verify() (
    set +e
    for directory in merged live standard iso; do
        mountpoint -q "${spider_checks}/${directory}" && umount "${spider_checks}/${directory}"
    done
    rm -rf "${spider_checks}"
    return 0
)
trap cleanup_verify EXIT
mkdir -p "${spider_checks}"/{iso,standard,live,merged}
mount -o loop,ro "${spider_iso}" "${spider_checks}/iso"
spider_casper="${spider_checks}/iso/casper"
for file in standard.squashfs standard.live.squashfs install-sources.yaml vmlinuz initrd; do
    test -s "${spider_casper}/${file}"
done
(cd "${spider_checks}/iso" && md5sum --quiet -c md5sum.txt)
(cd "${spider_casper}" && sha256sum --quiet -c SHA256SUMS)
python3 "${spider_repo}/distro/verify-install-catalog.py" "${spider_casper}"
mount -o loop,ro "${spider_casper}/standard.squashfs" "${spider_checks}/standard"
mount -o loop,ro "${spider_casper}/standard.live.squashfs" "${spider_checks}/live"
bash "${spider_repo}/distro/verify-installed-payload.sh" "${spider_checks}/standard"
mount -t overlay overlay -o "ro,lowerdir=${spider_checks}/live:${spider_checks}/standard" "${spider_checks}/merged"
# Resolve the combined live layers. A launcher alone is not an installer.
compgen -G "${spider_checks}/merged/var/lib/snapd/snaps/ubuntu-desktop-bootstrap_*.snap" >/dev/null
spider_bootstrap=("${spider_checks}"/merged/var/lib/snapd/snaps/ubuntu-desktop-bootstrap_*.snap)
unsquashfs -cat "${spider_bootstrap[0]}" meta/snap.yaml > "${spider_checks}/bootstrap.yaml"
if ! grep -q subiquity "${spider_checks}/bootstrap.yaml"; then
    compgen -G "${spider_checks}/merged/var/lib/snapd/snaps/subiquity_*.snap" >/dev/null
fi
for file in usr/share/applications/install-spider-os.desktop etc/xdg/autostart/the-web.desktop; do
    test -s "${spider_checks}/merged/${file}"
done
# Both installed and live files must contain all approved artwork.
for image in art-lab dev-bay forage kali-bay media recovery studio study system; do
    cmp "${spider_repo}/branding/workspaces/${image}.png" \
        "${spider_checks}/merged/usr/local/lib/spider-os/branding/workspaces/${image}.png"
done
xorriso -indev "${spider_iso}" -report_el_torito plain 2>&1 | tee "${spider_iso}.boot-report.txt"
grep -q 'BIOS' "${spider_iso}.boot-report.txt"
grep -q 'UEFI' "${spider_iso}.boot-report.txt"
echo 'Completed ISO: checksums, install source, live installer, artwork, BIOS and UEFI verified.'
