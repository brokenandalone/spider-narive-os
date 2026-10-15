# Spider OS 26.04 LTS: installed-build reconciliation

**Status, 2026-10-15:** The owner reports that the currently running PC is on Ubuntu 26.04 LTS. This is a user-reported installed OS version, **not independently read from the PC by GitHub**. The checked-out Git source and the live system have not yet been proven identical.

## Release and source authority

- Current installed host foundation: Ubuntu 26.04 LTS (owner-reported, point version not yet established)
- Image pinned for fresh-build tests: **Ubuntu Studio 26.04.1 LTS, Resolute Raccoon**
- Canonical source project: `brokenandalone/spider-narive-os`
- This safe comparison branch: `reconciliation/ubuntu-studio-26.04-lts-20261015`
- Previous source foundation: `baseline/24.04.5-working-20261004`
- Separate test-only 26.10 branch: `migration/ubuntu-studio-26.10`
- `Spider-OS1` is a companion/staging repo. Do not overwrite mature native source with its older scaffold.
- `brokenandalone/Spider-OS` and `justinhobsonstudios-byte/Spider-OS` are Aurora/Fedora-era repos, not the present native Ubuntu build.
- `Spider-Media-Center` and private `bcn-network` are separate project integrations, **not duplicate OS roots**.

The 26.04 reconciliation branch inherits recent work on The Web, Webbie, School/Study, Author, Studio, Media Center integration, Forage, Deep Forage, Kali Bay, and immersive bays from the migration snapshot. **Inherited code is not evidence those features are installed or working on the PC.**

## First trial on the existing PC: no installer, no root writes

The candidate source contains a **read-only trial command**. It verifies the
installed 26.04 base, checks audit tooling, inventories source upgrades and
reports file-level differences against the real native program directory.

Run this as the normal desktop user, **without** `sudo`. It does not switch
or reset your existing working Git checkout:

```bash
git clone --depth 1 --single-branch \
  --branch reconciliation/ubuntu-studio-26.04-lts-20261015 \
  https://github.com/brokenandalone/spider-narive-os.git \
  "$HOME/spider-os-2604-trial"
bash "$HOME/spider-os-2604-trial/tools/try-native-26-04.sh"
```

If the trial folder exists already, do not overwrite it automatically.
Review the code-difference counts and relevant local files before installing
*any* update. This is a trial **comparison**, not an applied upgrade.
Do not run `do-release-upgrade` on an already installed 26.04 base.

## Confirmed ISO builder blocker, 2026-10-15

Ubuntu Studio's official 26.04.1 ISO file listing specifies
`/casper/minimal.squashfs`, `/casper/minimal.standard.squashfs` and
`/casper/minimal.standard.live.squashfs`:

https://cdimage.ubuntu.com/ubuntustudio/releases/26.04/release/ubuntustudio-26.04.1-desktop-amd64.list

Our older builder and verifier currently require `standard.squashfs` and
`standard.live.squashfs` and rewrite the old `standard` install source.
Those source names **do not exist** on this release. The new three-layer
install source has not been reconstructed and installation-tested. **Do not
build or flash this custom ISO as an upgrade path** until its installer
catalog, layer overlay logic, ISO verification and disposable VM install pass.
A successful 26.04 release-signature check alone does not cover this blocker.

## How to compare the local PC without touching it

From the Spider OS machine, first save outstanding work and inspect the real version:

```bash
cat /etc/os-release
cat /etc/spider-os-release 2>/dev/null || true
uname -r
git -C ~/spider-narive-os remote -v
```

If the working clone is at `~/spider-narive-os`, do not reset it, discard uncommitted files or switch its branch automatically. Instead, create a separate disposable checkout to run the audit against the selected source:

```bash
git clone --branch reconciliation/ubuntu-studio-26.04-lts-20261015 \
  --single-branch https://github.com/brokenandalone/spider-narive-os.git \
  ~/spider-os-2604-audit
python3 ~/spider-os-2604-audit/tools/audit_installed_sources.py \
  --repository ~/spider-os-2604-audit \
  --installed-root /usr/local/lib/spider-os
```

This script is **read-only**: it hashes paths already tracked in the public repository and compares them to the same installed program paths. It does not change anything, enumerate unknown/private installed files, collect LUKS data, or upload output. A mismatch is a review item, not permission to copy the Git file over the working one.

If your installed Spider OS programs live elsewhere, give `--installed-root` the right root. Never infer installation success from a passing CI build.

## Qualification gates

1. Validate source syntax and 26.04.1 upstream SHA256SUMS signature on disposable GitHub runners.
2. Compare installed program revisions with the pinned Git revision, and **preserve local-only fixes** before any merge.
3. Inspect 26.04.1 ISO installer source/catalog and live/install layer paths. Do not assume the 24.04.5 casper layers are unchanged.
4. Build a disposable ISO and verify its checksum, installer/backend, BIOS and UEFI metadata.
5. Install only to an isolated disposable virtual disk. Test writable installed root, KDE/The Web, Spider Core, Webbie, all native bays, shutdown and second reboot.
6. Separately qualify encrypted install/unlock, audio production stack, GPU effects, multiple displays, devices and physical-machine recovery.
7. Merge only verified changes to the appropriate protected native development/release branch. Do not auto-replace local installations or publish an experiment as a stable release.

**No stage may assume access to the owner's private host, music, manuscripts, credentials, backups, encryption keys or local radio configuration.**

## Ubuntu Studio 26.10

Ubuntu Studio 26.10 is a **short-lived experimental comparison target**, not the installed or production base. Its existing experimental branch and CI stay isolated. Test Qt/KDE, audio, kernel, installer, services and the workspaces in a VM before considering any migration. Never silently move the installed PC from 26.04 LTS to 26.10.
