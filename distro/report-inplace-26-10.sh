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
mark INFO "APT source files" "File names saved; review third-party repos before release upgrade"
mark REVIEW "Backup" "Verify separately accessible backups of your home, all bays, models, Kali volumes, and LUKS recovery details"
mark REVIEW "Rollback" "No USB required, but plan for recovery if GRUB/LUKS boot fails; same-disk files are not enough"
mark REVIEW "Actual release upgrade" "The 26.10 package removal proposal is not known until do-release-upgrade runs; inspect before accepting"
printf "\nRESULT: %d blocker(s); %d review item(s).\n" "$BLOCKS" "$WARNINGS" | tee -a "$SUMMARY"
printf "REPORT_DIR=%s\n" "$OUT" | tee -a "$SUMMARY"
printf "%s\n" "NO CHANGES to apt sources, bootloader, packages, services, or encryption." | tee -a "$SUMMARY"
printf "%s\n" "Do not start do-release-upgrade yet. Review blockers, backups, and the report." | tee -a "$SUMMARY"
if (( BLOCKS > 0 )); then exit 2; fi
