#!/usr/bin/env bash
# Read-only 26.04 -> 26.10 host inspection; never starts an upgrade.
set -Eeuo pipefail
if [[ "$EUID" -eq 0 ]]; then
  echo "Run as the logged-in Spider OS user (without sudo)." >&2
  exit 2
fi

echo "Spider OS 26.10 readiness inspection (read-only)"
echo "Date: $(date -Is)"
echo "Host: $(hostname)"
echo

source /etc/os-release
echo "Current base: $PRETTY_NAME | VERSION_ID=$VERSION_ID"
if [[ "$VERSION_ID" != "26.04" ]]; then
  if [[ "$VERSION_ID" == "26.10" ]]; then
    echo "Already on 26.10; do not run another release upgrade."
  else
    echo "BLOCK: Supported direct path for this tool is 26.04 -> 26.10."
  fi
  exit 1
fi

if [[ -d /sys/firmware/efi ]]; then
  echo "Boot firmware: UEFI"
else
  echo "Boot firmware: legacy BIOS; preserve existing GRUB boot method"
fi

printf '\nMounted boot partitions:\n'
findmnt -no SOURCE,FSTYPE,TARGET / /boot /boot/efi 2>/dev/null || true
printf '\nRoot free space:\n'
df -h /
free_kb="$(df --output=avail -k / | tail -n 1 | tr -d ' ')"
if (( free_kb < 20 * 1024 * 1024 )); then
  echo "BLOCK: less than 20 GiB free on root."
fi

printf '\nEncryption/boot state (no secrets printed):\n'
if [[ -s /etc/crypttab ]]; then
  echo "crypttab exists; retain LUKS mapping, initramfs hooks and keyboard unlock."
else
  echo "WARNING: crypttab is empty or absent; verify how root encryption is configured."
fi
if [[ -L /usr/share/plymouth/themes/default.plymouth ]]; then
  echo "Plymouth default theme: $(readlink /usr/share/plymouth/themes/default.plymouth)"
fi
if grep -q 'plymouth.enable=0' /proc/cmdline; then
  echo "WARNING: Plymouth is disabled in the active boot command line."
fi

printf '\nPackage status:\n'
if [[ -z "$(dpkg --audit)" ]]; then
  echo "dpkg audit: clean"
else
  echo "BLOCK: dpkg audit reports interrupted or inconsistent packages."
  dpkg --audit
fi
holds="$(apt-mark showhold)"
if [[ -z "$holds" ]]; then
  echo "Package holds: none"
else
  echo "WARNING: package holds present"
  printf '%s\n' "$holds"
fi

printf '\nRelease upgrader configuration:\n'
grep -h '^Prompt=' /etc/update-manager/release-upgrades 2>/dev/null || true
if ! grep -qx 'Prompt=normal' /etc/update-manager/release-upgrades 2>/dev/null; then
  echo "HOLD: Prompt=normal is required to offer interim Ubuntu 26.10."
  echo "Do not change it before completing the preflight and verified external backup."
fi

printf '\nSpider components:\n'
for name in spider-os.service ollama.service; do
  printf '%s: ' "$name"
  systemctl is-active "$name" 2>/dev/null || true
done
printf 'webbie.service (user): '
systemctl --user is-active webbie.service 2>/dev/null || true
printf 'KDE session: %s\n' "\${XDG_CURRENT_DESKTOP:-unknown}"

printf '\nThird-party package-source inventory:\n'
grep -RhlE '^[[:space:]]*(deb |URIs:)' /etc/apt/sources.list /etc/apt/sources.list.d 2>/dev/null || true
echo
echo "REQUIRED HUMAN GATES: external backup and restore test; LUKS header backup"
echo "stored offline; third-party apt source review; audio and Webbie baseline;"
echo "boot recovery media; two successful 26.04 reboots; Spider 26.10 VM install,"
echo "encrypted-unlock test, live login and second reboot; splash password prompt test."
echo "No changes made. Do not run do-release-upgrade until these are reviewed."
