#!/usr/bin/env bash
# Non-destructive preflight for a direct Ubuntu Studio 26.04 -> 26.10
# in-place Spider OS upgrade. No USB, sudo, release upgrade or apt changes.
set -Eeuo pipefail
if (( EUID == 0 )); then
  echo "Run as the normal signed-in Spider OS user, without sudo." >&2
  exit 2
fi
if [[ ! -r /etc/os-release ]]; then echo "Missing /etc/os-release" >&2; exit 2; fi
source /etc/os-release
OUT="${HOME}/SpiderOS-26.10-Readiness-$(date +%Y%m%d-%H%M%S)-$$"
mkdir -m 700 -p "$OUT"
SUMMARY="$OUT/SUMMARY.txt"
: > "$SUMMARY"
BLOCKS=0
WARNINGS=0
mark() {
  local level="$1" name="$2" note="$3"
  printf "[%s] %s: %s\n" "$level" "$name" "$note" | tee -a "$SUMMARY"
  case "$level" in
    BLOCK) BLOCKS=$((BLOCKS+1)) ;;
    REVIEW) WARNINGS=$((WARNINGS+1)) ;;
  esac
}
mark INFO "Report" "Generated for local review; do not post full logs publicly."
mark INFO "Method" "Supported in-place release upgrade, no USB, no install media."
if [[ "${VERSION_ID:-unknown}" == "26.04" ]]; then
  mark PASS "OS base" "26.04 detected; eligible for normal upgrade evaluation"
elif [[ "${VERSION_ID:-unknown}" == "26.10" ]]; then
  mark BLOCK "OS base" "Already on 26.10; do not start another release upgrade"
else
  mark BLOCK "OS base" "Unexpected version ${VERSION_ID:-unknown}; stop and investigate"
fi
if [[ -d /sys/firmware/efi ]]; then
  mark INFO "Boot" "UEFI detected; leave existing EFI entries unchanged"
else
  mark INFO "Boot" "Legacy BIOS detected; preserve the existing GRUB install"
fi
{
  printf "Kernel: %s\n" "$(uname -r)"
  printf "Boot cmdline: %s\n" "$(cat /proc/cmdline)"
  for p in / /boot /boot/efi; do
    printf "Mount containing %s: " "$p"
    findmnt -n -o SOURCE,FSTYPE,TARGET --target "$p" || true
  done
} > "$OUT/boot-mounts.txt" 2>&1
# Ubuntu 26.10 signed GRUB restricts some encrypted/LVM /boot layouts.
# This check is read-only. It never changes EFI, crypttab or GRUB.
boot_on_encrypted_root=0
if findmnt -rn --mountpoint /boot >/dev/null 2>&1; then
  mark INFO "Separate /boot" "Separate mount exists; verify EFI bootloader"
else
  mark REVIEW "/boot location" "/boot is not separately mounted; determine loader/kernel path"
  root_device="$(findmnt -nr -o SOURCE --target / 2>/dev/null || true)"
  if [[ -n "$root_device" ]] && command -v lsblk >/dev/null 2>&1; then
    if lsblk -ns -o FSTYPE -- "$root_device" 2>/dev/null | grep -q 'crypto_LUKS'; then
      boot_on_encrypted_root=1
      mark REVIEW "Encrypted /boot" "Encrypted root contains /boot; verify how GRUB loads kernel"
    fi
  fi
fi
if command -v mokutil >/dev/null 2>&1; then
  sb_state="$(mokutil --sb-state 2>&1 || true)"
  printf "%s\n" "$sb_state" > "$OUT/secure-boot.txt"
  if grep -qi "SecureBoot enabled" <<< "$sb_state"; then
    mark INFO "Secure Boot" "Enabled"
    if (( boot_on_encrypted_root == 1 )); then
      mark BLOCK "Encrypted boot with Secure Boot" "Investigate Ubuntu 26.10 signed-GRUB support before upgrading"
    fi
  elif grep -qi "SecureBoot disabled" <<< "$sb_state"; then
    mark INFO "Secure Boot" "Disabled"
  else
    mark REVIEW "Secure Boot" "State unclear; see secure-boot.txt"
  fi
else
  mark REVIEW "Secure Boot" "mokutil not installed; state unverified"
fi
ls -l /boot/vmlinuz* /boot/initrd.img* /boot/grub/grub.cfg > "$OUT/boot-kernel-files.txt" 2>&1 || true
# The actual firmware entry is important on heavily customized installations.
if command -v efibootmgr >/dev/null 2>&1; then
  efibootmgr > "$OUT/efi-current-entry.txt" 2>&1 || true
  if grep -q "BootCurrent:" "$OUT/efi-current-entry.txt"; then
    mark INFO "EFI boot entry" "Current entry recorded in efi-current-entry.txt"
  else
    mark REVIEW "EFI boot entry" "Could not resolve active boot entry without privileges"
  fi
else
  mark REVIEW "EFI boot entry" "efibootmgr unavailable"
fi

# SpiderOS has a custom EFI GRUB stub. It can chainload an unmounted
# filesystem instead of the current root's /boot/grub/grub.cfg.
# Inspect its textual reference only; do not install or regenerate GRUB.
stub="/boot/efi/EFI/SpiderOS/grub.cfg"
if [[ -r "$stub" ]]; then
  cp -- "$stub" "$OUT/spider-efi-boot-stub.txt"
  stub_uuid="$(awk '$1=="search.fs_uuid" {print $2; exit}' "$stub")"
  if [[ -n "$stub_uuid" ]]; then
    mark INFO "SpiderOS EFI stub" "References filesystem UUID $stub_uuid"
    # The active SpiderOS EFI GRUB can point to a second, unmounted
    # ext4 /boot partition. update-grub writes the mounted system's
    # /boot/grub/grub.cfg instead, so a new kernel can become unbootable.
    # Block the release upgrade until a tested synchronization plan exists.
    target_mount="$(findmnt -rn -S "UUID=$stub_uuid" -o TARGET 2>/dev/null | head -n 1 || true)"
    if [[ -z "$target_mount" ]]; then
      mark BLOCK "Separate unmounted SpiderOS boot filesystem" "EFI stub points to unmounted UUID $stub_uuid; kernel and initramfs may be loaded from it. Require external backup and tested sync/rollback before do-release-upgrade"
    else
      mark REVIEW "SpiderOS boot filesystem" "EFI stub target mounted at $target_mount; verify active GRUB kernel and initramfs match installed files"
    fi
  else
    mark REVIEW "SpiderOS EFI stub" "Cannot identify GRUB filesystem target; inspect spider-efi-boot-stub.txt"
  fi
else
  mark REVIEW "SpiderOS EFI stub" "Custom EFI GRUB text stub absent or unreadable"
fi

# A separate mounted data volume may hold Webbie state; verify it exists
# before a release upgrade. Never mount, format or edit it automatically.
brain_target="/var/lib/spider-os/webbie-brain"
if awk -v tgt="$brain_target" '$1 !~ /^#/ && $2 == tgt {found=1} END {exit !found}' /etc/fstab; then
  if findmnt -rn --mountpoint "$brain_target" >/dev/null 2>&1; then
    mark PASS "Webbie brain storage" "fstab target is mounted"
  else
    mark REVIEW "Webbie brain storage" "fstab target NOT mounted; confirm its UUID and data before upgrading"
  fi
fi
if [[ -s /etc/crypttab ]]; then
  mark INFO "LUKS" "Nonempty crypttab; disk unlock must be verified before and after"
else
  mark REVIEW "LUKS" "No readable crypttab entries; inspect encrypted-root mapping"
fi
if grep -q "plymouth.enable=0" /proc/cmdline; then
  mark REVIEW "Splash" "Plymouth disabled in boot arguments; do not enable until LUKS prompt is tested"
else
  mark INFO "Splash" "Plymouth not explicitly disabled by this kernel command line"
fi
if [[ -L /lib32 && ! -e /lib32 ]]; then
  mark BLOCK "Ubuntu /lib32 known issue" "Dangling symlink; stop for review of the official 26.10 release note"
else
  mark PASS "Ubuntu /lib32 known issue" "No dangling /lib32 symlink detected"
fi
free_kb="$(df -Pk / | awk 'NR==2 {print $4}')"
if [[ "$free_kb" =~ ^[0-9]+$ ]] && (( free_kb >= 20*1024*1024 )); then
  mark PASS "Free root space" "$((free_kb/1024/1024)) GiB free"
else
  mark BLOCK "Free root space" "Less than 20 GiB available or unable to read size"
fi
df -hT > "$OUT/filesystems.txt" 2>&1 || true
if audit="$(dpkg --audit 2>&1)" && [[ -z "$audit" ]]; then
  mark PASS "Package manager" "dpkg audit clean"
else
  printf "%s\n" "$audit" > "$OUT/dpkg-audit.txt"
  mark BLOCK "Package manager" "dpkg audit found issues; see dpkg-audit.txt"
fi
holds="$(apt-mark showhold 2>&1 || true)"
if [[ -z "$holds" ]]; then
  mark PASS "Package holds" "No package holds"
else
  printf "%s\n" "$holds" > "$OUT/package-holds.txt"
  mark REVIEW "Package holds" "Review package-holds.txt"
fi
prompt="$(sed -n 's/^[[:space:]]*Prompt[[:space:]]*=[[:space:]]*//p' /etc/update-manager/release-upgrades 2>/dev/null | tail -n 1)"
if [[ "$prompt" == "normal" ]]; then
  mark PASS "Release notifications" "Prompt=normal"
else
  mark REVIEW "Release notifications" "Current Prompt=${prompt:-unknown}; change to normal only after safety review"
fi
if command -v do-release-upgrade >/dev/null 2>&1; then
  mark PASS "Release upgrader" "do-release-upgrade installed, but not run"
else
  mark BLOCK "Release upgrader" "do-release-upgrade is unavailable"
fi
for unit in spider-os.service ollama.service sddm.service display-manager.service; do
  if systemctl is-active --quiet "$unit" 2>/dev/null; then
    mark PASS "$unit" "active"
  else
    mark REVIEW "$unit" "not active or not installed; identify local service name"
  fi
done
if systemctl --user is-active --quiet webbie.service 2>/dev/null; then
  mark PASS "webbie.service (user)" "active"
else
  mark REVIEW "webbie.service (user)" "not active in this user session; inspect before upgrading"
fi
if systemctl --user is-active --quiet pipewire.service 2>/dev/null; then
  mark PASS "PipeWire audio" "active"
else
  mark REVIEW "PipeWire audio" "PipeWire user service not active; verify audio route"
fi
if [[ -d /usr/local/lib/spider-os ]]; then
  mark PASS "Spider source payload" "System Spider OS directory exists"
else
  mark REVIEW "Spider source payload" "Not at /usr/local/lib/spider-os; verify your installed path"
fi
for name in "Music" "Documents"; do
  if [[ -d "$HOME/$name" ]]; then
    mark INFO "$name" "Present in home directory; back up before upgrading"
  fi
done
if command -v podman >/dev/null 2>&1; then
  (podman ps -a --format "{{.Names}} | {{.Status}}" 2>&1 || true) > "$OUT/containers.txt"
  mark INFO "Kali containers" "Podman inventory saved; contents/volumes are not backed up"
fi
if command -v dpkg-query >/dev/null 2>&1; then
  dpkg-query -W -f='${binary:Package}\t${Version}\n' > "$OUT/installed-packages.tsv" 2>/dev/null || true
fi
# Inventory pre-existing Ubuntu Studio and creative apps; do not install them.
{
  for pkg in ubuntustudio-desktop ubuntustudio-audio ardour audacity              carla hydrogen mixxx qjackctl qtractor krita gimp kdenlive              blender inkscape scribus obs-studio yoshimi zynaddsubfx              lmms supercollider sonic-pi; do
    dpkg-query -W -f='${binary:Package}\t${Status}\t${Version}\n' "$pkg" 2>/dev/null || true
  done
} > "$OUT/creative-apps-baseline.tsv"
mark INFO "Creative applications" "Pre-upgrade package baseline saved for post-upgrade comparison"
if command -v systemctl >/dev/null 2>&1; then
  systemctl list-unit-files --type=service --no-pager > "$OUT/installed-system-services.txt" 2>/dev/null || true
  systemctl --user list-unit-files --type=service --no-pager > "$OUT/installed-user-services.txt" 2>/dev/null || true
fi
if command -v apt-get >/dev/null 2>&1; then
  if apt-get -s full-upgrade > "$OUT/26.04-package-simulation.txt" 2>&1; then
    if grep -q "^Remv " "$OUT/26.04-package-simulation.txt"; then
      grep "^Remv " "$OUT/26.04-package-simulation.txt" > "$OUT/26.04-proposed-removals.txt"
      mark REVIEW "Current package simulation" "Potential removals: see 26.04-proposed-removals.txt"
    else
      mark INFO "Current package simulation" "No simulated removals (26.04 only, NOT the 26.10 plan)"
    fi
  else
    mark REVIEW "Current package simulation" "Simulation failed; inspect 26.04-package-simulation.txt"
  fi
fi
{
  [[ -f /etc/apt/sources.list ]] && echo /etc/apt/sources.list
  find /etc/apt/sources.list.d -maxdepth 1 -type f \( -name "*.sources" -o -name "*.list" \) -print 2>/dev/null || true
} > "$OUT/apt-source-filenames.txt"
mark REVIEW "APT source files" "Inspect source file names; third-party repos may be disabled or incompatible"
mark REVIEW "Backup" "Verify separately accessible backups of your home, all bays, models, Kali volumes, and LUKS recovery details"
mark REVIEW "Rollback" "No USB required, but plan for recovery if GRUB/LUKS boot fails; same-disk files are not enough"
mark REVIEW "Actual release upgrade" "The 26.10 package removal proposal is not known until do-release-upgrade runs; inspect before accepting"
printf "\nRESULT: %d blocker(s); %d review item(s).\n" "$BLOCKS" "$WARNINGS" | tee -a "$SUMMARY"
printf "REPORT_DIR=%s\n" "$OUT" | tee -a "$SUMMARY"
printf "%s\n" "NO CHANGES to apt sources, bootloader, packages, services, or encryption." | tee -a "$SUMMARY"
printf "%s\n" "Do not start do-release-upgrade yet. Review blockers, backups, and the report." | tee -a "$SUMMARY"
if (( BLOCKS > 0 )); then exit 2; fi
