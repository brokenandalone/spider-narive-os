#!/usr/bin/env bash
set -Eeuo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
output_dir="$project_root/output"
native_root="$output_dir/spider-native-root"

export PATH="$project_root/tools/bin:$PATH"

fedora_release="${FEDORA_RELEASE:-44}"
fedora_kde_version="${FEDORA_KDE_VERSION:-1.7}"
fedora_iso="${FEDORA_KDE_ISO:-}"

fedora_iso_url="${FEDORA_KDE_ISO_URL:-https://download.fedoraproject.org/pub/fedora/linux/releases/${fedora_release}/KDE/x86_64/iso/Fedora-KDE-Desktop-Live-${fedora_release}-${fedora_kde_version}.x86_64.iso}"

if ! command -v mkksiso >/dev/null 2>&1; then
  printf '%s\n' 'mkksiso is required to build the customized Fedora installer.' >&2
  printf '%s\n' 'Install the lorax package on Fedora.' >&2
  exit 1
fi

bash "$project_root/build-native.sh" "$native_root"

if [[ -z "$fedora_iso" ]]; then
  if ! command -v curl >/dev/null 2>&1; then
    printf '%s\n' 'curl is required when FEDORA_KDE_ISO is not set.' >&2
    exit 1
  fi

  cache_dir="$project_root/.fedora-kde-iso"
  mkdir -p "$cache_dir"

  fedora_iso="$cache_dir/Fedora-KDE-Desktop-Live-${fedora_release}-${fedora_kde_version}.x86_64.iso"

  if [[ ! -f "$fedora_iso" ]]; then
    curl --fail --location --continue-at - \
      --output "$fedora_iso" \
      "$fedora_iso_url"
  fi
fi

if [[ ! -f "$fedora_iso" ]]; then
  printf 'Fedora KDE ISO not found: %s\n' "$fedora_iso" >&2
  exit 1
fi

mkdir -p "$output_dir"

output_iso="$output_dir/Spider_OS_native_${fedora_release}.iso"

rm -f "$output_iso" "$output_iso.sha256"

mkksiso_cmd=(
  mkksiso
  --add "$native_root"
  --ks "$project_root/installer/spider-os.ks"
  -V SPIDER_OS
  "$fedora_iso"
  "$output_iso"
)

if [[ "$EUID" -eq 0 ]]; then
  "${mkksiso_cmd[@]}"
else
  if ! command -v sudo >/dev/null 2>&1; then
    printf '%s\n' 'mkksiso must run as root; install sudo or run this script as root.' >&2
    exit 1
  fi

  sudo "${mkksiso_cmd[@]}"
  sudo chown "$(id -u):$(id -g)" "$output_iso"
fi

sha256sum "$output_iso" > "$output_iso.sha256"

printf 'Spider OS writable installer ISO: %s\n' "$output_iso"
printf 'SHA-256: %s\n' "$output_iso.sha256"
