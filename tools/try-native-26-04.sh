#!/usr/bin/env bash
# Read-only first phase of a Spider OS 26.04 source upgrade trial.
# Intentionally does NOT sudo, copy program files, restart services,
# install packages, alter disk layout, or change any user data.
set -Eeuo pipefail

EXPECTED_BRANCH="reconciliation/ubuntu-studio-26.04-lts-20261015"
REPO="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALLED_ROOT="${1:-/usr/local/lib/spider-os}"

die() { printf 'STOP: %s\n' "$*" >&2; exit 2; }

[[ "${EUID}" -ne 0 ]] || die "Run as your normal Spider OS account, never with sudo."
command -v git >/dev/null || die "git is required for an isolated source checkout."
command -v python3 >/dev/null || die "Python 3 is required."
[[ -r /etc/os-release ]] || die "/etc/os-release cannot be read."
# shellcheck disable=SC1091
source /etc/os-release

printf '\nSPIDER OS 26.04: READ-ONLY UPGRADE TRIAL\n'
printf 'OS: %s\n' "${PRETTY_NAME:-unknown}"
printf 'Version: %s\n' "${VERSION_ID:-unknown}"
printf 'Kernel: %s\n' "$(uname -r)"

[[ "${VERSION_ID:-}" == 26.04* ]] || die "Expected installed 26.04. No upgrade attempted; inspect the OS version first."
[[ -d "${INSTALLED_ROOT}" ]] || die "Installed program directory does not exist: ${INSTALLED_ROOT}"
[[ -f "${INSTALLED_ROOT}/the-web/shell/main.py" ]] || die "The selected installed root does not contain the native The Web shell."

branch="$(git -C "${REPO}" branch --show-current)"
[[ "${branch}" == "${EXPECTED_BRANCH}" ]] || die "Wrong checkout (${branch}). Clone the approved 26.04 reconciliation branch."
commit="$(git -C "${REPO}" rev-parse --short=12 HEAD)"
printf 'Source branch: %s\n' "${branch}"
printf 'Source commit: %s\n' "${commit}"
printf 'Installed program path: %s\n' "${INSTALLED_ROOT}"

printf '\nChecking trial script and source audit...\n'
bash -n "${REPO}/distro/build-iso.sh" "${REPO}/distro/verify-iso.sh"
(cd "${REPO}" && python3 -B -m unittest discover -s tests -p 'test_installed_source_audit.py' -q)

# Compare only Git-tracked public program paths. Never read arbitrary
# local files or dump user documents, credentials, or home directories.
python3 -B - "${REPO}" "${INSTALLED_ROOT}" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]) / "tools"))
from audit_installed_sources import audit
from audit_upgrade_coverage import audit as coverage_audit

source = Path(sys.argv[1])
installed = Path(sys.argv[2])
r = audit(source, installed)
print("\nINSTALLED CODE COMPARISON")
print("Tracked program files:", r["total_tracked"])
print("Identical:", r["matching"])
print("Different:", len(r["changed"]))
print("Missing on host:", len(r["missing"]))
for area, stats in r["components"].items():
    if any(stats.values()):
        print("  {}: {} matching, {} different, {} missing".format(
            area, stats["matching"], stats["changed"], stats["missing"]))
for kind in ("changed", "missing"):
    examples = r[kind][:12]
    if examples:
        print("\nFirst {} {} paths:".format(len(examples), kind))
        for path in examples:
            print("  ", path)
        if len(r[kind]) > len(examples):
            print("  ... {} more".format(len(r[kind]) - len(examples)))

c = coverage_audit(source)
print("\nGITHUB UPGRADE INVENTORY")
print("Source payload coverage:", "PASS" if c["passes_source_coverage"] else "FAIL")
print("Planned bays not yet implemented:", ", ".join(c["unimplemented_destination_workspaces"]) or "none")
print("Media executable:", c["media_electron_binary"])
print("Eligible for unattended install:", "NO")
print("\nRESULT: No installed files, disk, service or user settings were changed.")
print("Review the different/missing paths before installing the source overlay.")
PY
