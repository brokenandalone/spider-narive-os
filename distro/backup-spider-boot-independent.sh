#!/usr/bin/env bash
# Back up the proven SpiderOS EFI + sda1 boot chain to INDEPENDENT media.
# Explicitly does not change boot partitions, EFI entries, GRUB, fstab or LUKS.
set -Eeuo pipefail
umask 077
usage() {
  echo "Usage: sudo bash $0 --check /mounted/external/backup-dir" >&2
  echo "   or: sudo bash $0 --backup /mounted/external/backup-dir" >&2
}
if (( EUID != 0 )); then echo "Run with sudo to read raw boot devices." >&2; exit 2; fi
if (( $# != 2 )); then usage; exit 2; fi
mode="$1"
backup_dir="$2"
if [[ "$mode" != "--check" && "$mode" != "--backup" ]]; then usage; exit 2; fi
if [[ ! -d "$backup_dir" || -L "$backup_dir" ]]; then
  echo "STOP: destination must be an existing non-symlink directory on a mounted independent backup volume." >&2
  exit 2
fi
dest="$(realpath -- "$backup_dir")"
mount_target="$(findmnt -n -o TARGET --target "$dest")"
mount_source="$(findmnt -n -o SOURCE --target "$dest")"
mount_fs="$(findmnt -n -o FSTYPE --target "$dest")"
if [[ "$mount_target" == "/" || -z "$mount_source" || "$mount_target" == "/boot" || "$mount_target" == "/boot/efi" ]]; then
  echo "STOP: independent mounted backup volume required; local root/boot is not independent." >&2
  exit 2
fi
case "$mount_fs" in
  nfs|nfs4|cifs|smb3|fuse.sshfs)
    echo "Verified backup destination is a separate network mount ($mount_fs)."
    ;;
  *)
    if [[ "$mount_source" != /dev/* ]]; then
      echo "STOP: backup volume origin $mount_source ($mount_fs) cannot be verified as independent." >&2
      exit 2
    fi
    # Reject any partition/DM device on the SAME physical /dev/sda as SpiderOS.
    ancestors="$(lsblk -s -n -o NAME -- "$mount_source")" || {
      echo "STOP: cannot verify the backup storage device." >&2; exit 2;
    }
    if grep -Eq '^sda([[:digit:]]+)?$' <<< "$ancestors"; then
      echo "STOP: backup is on the same physical /dev/sda disk as SpiderOS." >&2
      exit 2
    fi
    echo "Backup volume is independent from the SpiderOS /dev/sda disk."
    ;;
esac

for pair in "/dev/sda1:b8b48e84-c748-4741-9b94-a2f5bab50ca6" "/dev/sda2:4DF6-7D67"; do
  dev="${pair%%:*}"
  expected="${pair#*:}"
  actual="$(blkid -s UUID -o value "$dev" || true)"
  if [[ "${actual,,}" != "${expected,,}" ]]; then
    echo "STOP: $dev UUID changed ($actual). No backup was started." >&2
    exit 2
  fi
done
if findmnt -rn --source /dev/sda1 >/dev/null 2>&1; then
  echo "STOP: sda1 is mounted; this backup script expects the observed unmounted boot partition." >&2
  exit 2
fi
if (( $(df -PB1 "$dest" | awk 'NR==2 {print $4}') < 3*1024*1024*1024 )); then
  echo "STOP: reserve at least 3 GiB free on backup destination." >&2
  exit 2
fi
echo "Destination: $dest ($mount_fs: $mount_source)"
echo "This backup contains potentially private GRUB, Webbie and initramfs data. Secure the destination."
if [[ "$mode" == "--check" ]]; then
  echo "CHECK PASS: location is acceptable for a boot-chain backup; no files created."
  exit 0
fi

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
final="$dest/spider-boot-$stamp"
tmp="$dest/.spider-boot-$stamp.partial"
if [[ -e "$final" || -e "$tmp" ]]; then echo "STOP: backup name collision." >&2; exit 2; fi
mkdir -m 0700 -- "$tmp"
echo "Backing up raw unmounted sda1 and EFI partition (READING source only)..."
dd if=/dev/sda1 of="$tmp/sda1.img" bs=4M status=progress conv=fsync
dd if=/dev/sda2 of="$tmp/sda2-efi.img" bs=4M status=progress conv=fsync
echo "Backing up current root boot directory and Webbie brain folder..."
tar -C / -cpf "$tmp/root-boot.tar" boot
tar -C / -cpf "$tmp/webbie-brain.tar" var/lib/spider-os/webbie-brain
sfdisk --dump /dev/sda > "$tmp/sda-partitions.txt"
lsblk -o NAME,SIZE,FSTYPE,UUID,MOUNTPOINTS > "$tmp/drive-layout.txt"
printf '%s\n' "Original sda1 UUID: b8b48e84-c748-4741-9b94-a2f5bab50ca6" \
  "Original sda2 UUID: 4DF6-7D67" \
  "BootCurrent=0002 (owner verified October 15, 2026); EFI/SpiderOS/grubx64.efi" \
  "LUKS header NOT included; make a separately encrypted, tested backup." \
  "This is a BOOT-DATA backup, NOT an entire SpiderOS system restore." > "$tmp/README.txt"
expected1="$(blockdev --getsize64 /dev/sda1)"
expected2="$(blockdev --getsize64 /dev/sda2)"
[[ "$(stat -c %s "$tmp/sda1.img")" == "$expected1" ]] || { echo "STOP: incomplete sda1 image." >&2; exit 2; }
[[ "$(stat -c %s "$tmp/sda2-efi.img")" == "$expected2" ]] || { echo "STOP: incomplete EFI image." >&2; exit 2; }
(
  cd "$tmp"
  sha256sum sda1.img sda2-efi.img root-boot.tar webbie-brain.tar sda-partitions.txt drive-layout.txt README.txt > SHA256SUMS
  sha256sum -c SHA256SUMS
)
mv -- "$tmp" "$final"
echo "BOOT-DATA BACKUP VERIFIED: $final"
echo "Not a complete backup. The main Spider OS system, LUKS header, Webbie models, Nova and creative data still need independent protection."
