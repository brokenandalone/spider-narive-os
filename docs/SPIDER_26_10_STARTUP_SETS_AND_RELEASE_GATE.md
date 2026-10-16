# Spider OS 26.10: Release Gate and Startup Sets

Updated October 15, 2026

## Official upstream
Ubuntu Studio 26.10 Stonking Stingray released today and officially supports upgrading from Ubuntu Studio 26.04 LTS. It is supported until July 2027.
- https://ubuntustudio.org/2026/10/ubuntu-studio-26-10-released/
- https://discourse.ubuntu.com/t/ubuntu-studio-26-10-release-notes/88657
- https://documentation.ubuntu.com/release-notes/26.10/

The migration branch configuration points to the final 26.10 ISO, release channel, and stonking codename.

## Primary installation policy: in-place, no USB

**Owner requirement (October 15, 2026): No USB creation, no reformat, no clean install.**
The daily-use Spider OS computer already runs Ubuntu Studio 26.04. Use the
official Ubuntu Studio 26.04 LTS -> 26.10 in-place release upgrader, the
same general method used for the previous operating-system upgrade.

A Spider 26.10 ISO and disposable virtual-machine tests in GitHub Actions are
**optional developer qualifications, not a prerequisite for the owner to burn
a USB or boot an installer**. The user must never be instructed to write a
USB as part of the standard upgrade.

Sequence:
1. Run the read-only readiness/preflight scripts on the installed 26.04 PC.
2. Save a fresh package inventory, the current Spider OS service and file state,
   current GRUB/initramfs/crypttab details and any locally newer bay files.
3. Back up the data you cannot afford to lose to a separately accessible
   network share, cloud account, or other existing storage. A same-disk
   backup alone does not protect against disk failure. A bootable USB is not
   required, but lack of independent recovery media increases the risk of an
   unrecoverable boot failure. Back up the LUKS header securely and privately.
4. Fully update 26.04, then review held/broken packages, foreign apt repos,
   kernel drivers, services, and the release upgrader's proposed removals.
5. Enable prompting for interim Ubuntu releases (Prompt=normal), then run
   the official `do-release-upgrade` for Ubuntu Studio 26.10. Never use
   `do-release-upgrade -d` or rewrite apt release codenames by hand.
6. After reboot, verify that encrypted unlock, KDE, PipeWire, Webbie, all
   native workspaces and Ubuntu Studio applications survived. Repair any
   incompatibilities without indiscriminately replacing locally newer files.
7. Install/test the native Spider SDDM + Plasma splash package in place,
   preserving the existing user configuration. Activate Plymouth on the
   encrypted boot path only after unlock-prompt qualification. This does
   not require any ISO, USB or clean install.

In-place upgrade *normally preserves* installed applications and files, but
third-party packages may be disabled or removed by the release upgrader. Never
promise zero data loss or zero removals; inspect the proposed changes first.

## Startup artwork sets
All assets are existing repo-approved artwork, not replacement stock designs.

| Preset | Existing source image |
|---|---|
| spider-purple (default) | branding/wallpapers/spider-os-wallpaper.png |
| spider-crimson | branding/wallpapers/collection/distressed-crimson-spider-os-wallpaper-e799fd25.png |
| spider-nightfall | branding/wallpapers/collection/neon-purple-grunge-spider-emblem-c882e8d5.png |

All three images are staged under /usr/share/spider-os/startup-sets/ in installed and live images. The selected image is staged for SDDM Breeze background and Plasma 6's new Spider startup package org.spider.os. The system-wide Plasma splash default does not override existing user preferences. The shared Spider splash is branding/splash/spider-os-splash.png.

Build with a different set by setting SPIDER_STARTUP_SET, for example:

    sudo env SPIDER_STARTUP_SET=spider-crimson ./distro/build-iso.sh

The original wallpaper library and native functional workspaces remain distinct and are not removed or replaced. No standalone app launcher is added.

## USB-free, post-upgrade native splash installation

These instructions work on the currently installed PC, not from an ISO.
The source checkout must include the existing branding PNG files.

Read-only preview, safe on either 26.04 or 26.10:

    bash distro/install-startup-screens-inplace.sh --check spider-purple

After the *official* in-place upgrade has completed successfully, after
verifying the system reports VERSION_ID=26.10, and after Plasma/SDDM work:

    sudo bash distro/install-startup-screens-inplace.sh --apply spider-purple

Use spider-crimson or spider-nightfall instead to select another designed set.
The installer retains a private backup of the system files it replaces under
/var/backups/spider-os/startup/. It does not change user-level overrides,
restart SDDM, call update-initramfs, update GRUB, or enable Plymouth. The
Plasma splash and SDDM backdrop should appear on the next sign-in. No
USB, repartitioning, ISO file, or clean install is involved.

The Plymouth background is copied but not made the default during this
in-place operation because the real LUKS passphrase prompt must be tested
before changing the initramfs boot experience.

## 26.10 boot security caution from actual host (Oct 15)

**Observed in user terminal:** UEFI mode, 512 MB `SPIDER_EFI` on
`/dev/sda2` mounted at `/boot/efi`; `/dev/sda5` LUKS containing
`spider-disk` LVM and the main root; `/boot` is not a separate mount.
There is an unmounted `/dev/sda1` ext4 partition (449 MB) whose
purpose has not been verified. Do not format or repurpose it.
`Prompt=normal` and plasma-distro-release-notifier are already present;
the system still reports no new upgrade offer. Available root space was
roughly 211 GB. The expected external backup mount is missing and a
USB device named PRAM was reported as 0 bytes; no verified external
backup is known.

Under **Secure Boot**, Ubuntu 26.10 restricts signed GRUB support
for `/boot` on LUKS or LVM. `/boot` located under an encrypted
root is an indicator to investigate, but is *not proof* that the
running EFI loader reads kernels through encrypted GRUB.
Check `mokutil --sb-state`, the active EFI/GRUB loader configuration,
the contents of `/boot` and the filesystem where the actual kernels
are loaded from **before allowing the upgrade**.
Never disable Secure Boot, move `/boot`, change partitions or
rebuild GRUB automatically in the migration stage.
The read-only host report now blocks the conservative case of
reported Secure Boot enabled plus an encrypted-root `/boot` directory
pending manual verification.

Official Ubuntu guidance:
https://ubuntu.com/blog/ubuntu-26-10-security
https://documentation.ubuntu.com/release-notes/26.10/

**Independent backup still required.** The earlier application-source
rollback directories and backups inside `/home` do not protect against
loss of the same physical disk. An external installer USB is not
required, and the user specifically declined creating one.

## Firmware boot and Webbie volume evidence (October 15, 2026)

Actual EFI output provided by the owner:
- `BootCurrent: 0002` and `Boot0002* SpiderOS` uses
  `\\EFI\\SpiderOS\\grubx64.efi` from the `SPIDER_EFI` partition,
  **not** the stale Windows/Fedora/Ubuntu firmware entries. These other
  entries must not be removed automatically.
- `/boot/grub/grub.cfg`, `vmlinuz-7.0.0-38-generic` and
  `initrd.img-7.0.0-38-generic` currently live in the
  `/boot` directory on the mounted root volume; no separate `/boot`
  mount was reported.
- The grep of `/etc/default/grub` showed no explicit
  `GRUB_ENABLE_CRYPTODISK` or `GRUB_PRELOAD_MODULES`, which does not
  establish how this existing EFI GRUB executable finds kernels.
- The owner did not include the `mokutil --sb-state` or
  `findmnt -T /boot` portions in the reported result. **Secure Boot is
  not yet confirmed.**
- `/etc/fstab` also references an ext4 filesystem mounted at
  `/var/lib/spider-os/webbie-brain` with UUID
  `bf0d0a18-68ed-4d28-b8b7-d26f6ec967f0`. It was not visible
  as a mounted filesystem in the prior `df -hT` / `lsblk` outputs.
  Determine whether the backing volume exists, and whether any data
  is being written to an unmounted fallback directory. Do not mount,
  format or overwrite it without a separate data-preserving plan.

The upgraded host-readiness script now checks these items. Do not
infer that the 26.10 UEFI encrypted boot path is safe from existing
kernel files alone.

## Confirmed host boot and brain-volume results (Oct 15)

The owner has now run the actual firmware and GRUB checks:

- `mokutil --sb-state` reports **SecureBoot disabled**. Canonical says
  the restriction on LUKS/LVM `/boot` applies to signed GRUB under
  Secure Boot and that full GRUB features remain available when it is
  disabled; this is not by itself a boot incompatibility on the PC.
  Source: https://ubuntu.com/blog/ubuntu-26-10-security
- `findmnt -T /boot` resolves to the ext4 root on
  `/dev/mapper/kali--vg-root`; the root is inside an LVM volume on
  LUKS2. Current GRUB config explicitly includes `insmod cryptodisk`,
  `insmod luks2`, `insmod lvm`, and a `cryptomount` against the
  LUKS root. The 26.10 upgrader may upgrade GRUB; preserve the working
  UEFI `EFI/SpiderOS` grub binary, minimal config and current
  `/boot/grub` setup. Do not install a signed-only GRUB that cannot
  reach the encrypted root. Never change firmware Secure Boot settings.
- The root disk inventory (`sda`, with EFI `sda2`, encrypted
  `sda5`, LVM root/swap) contains **no filesystem with UUID
  `bf0d0a18-68ed-4d28-b8b7-d26f6ec967f0`**. This UUID is in
  `/etc/fstab` for `/var/lib/spider-os/webbie-brain`
  with `nofail` and `x-systemd.device-timeout=10`; the mount is
  not active. It may be a missing storage drive or obsolete config.
  Inspect directory contents and `blkid` before attempting a
  repair. Do not create a new volume, format one, or overwrite data.
- The source-check workflow succeeded for commit
  `f6a72f1c1a085aa6ded09b7f86306af168ebfc80`; this doesn't
  certify the actual GRUB upgrade or backup restorability.

User-facing USB policy remains: do not make installer media. No 26.10
package upgrade should start before independent backup and a
clear way to restore the working EFI plus encrypted boot chain.

## New authoritative boot stub and Webbie storage findings

The owner's October 15 read-only results now prove the installed
`/boot/efi/EFI/SpiderOS/grub.cfg` contains:

    search.fs_uuid b8b48e84-c748-4741-9b94-a2f5bab50ca6 root hd0,gpt1
    set prefix=($root)'/grub'
    configfile $prefix/grub.cfg

UUID `b8b48e84-c748-4741-9b94-a2f5bab50ca6` identifies unmounted
**`/dev/sda1` ext4, 449 MB**. Hence the EFI stub expects a
`/grub/grub.cfg` file **on `sda1`**, a partition omitted from
`/etc/fstab`. Do not assume the large root's
`/boot/grub/grub.cfg` is the config that the firmware actually runs.
The current root config contains `cryptodisk`, `luks2`, `lvm`, and
`cryptomount`, but the **effective config on sda1 is not yet inspected**.
The machine currently boots, so the partition may be part of the active
boot chain; preserve all three locations: EFI on sda2, potential
`sda1:/grub/`, and encrypted root's `/boot` files.

Safest next inspection: `sudo debugfs -R 'ls -l /' /dev/sda1` and
`sudo debugfs -R 'ls -l /grub' /dev/sda1`, followed by a read-only
`debugfs -R 'cat /grub/grub.cfg'` check if present. **Never pass
`-w`**, mount the partition read-write, run `grub-install`,
or rewrite this EFI stub until its boot chain is documented. Debugfs
opens ext filesystems read-only by default.

The dedicated `/var/lib/spider-os/webbie-brain` ext4 fstab UUID
`bf0d0a18-68ed-4d28-b8b7-d26f6ec967f0` was not found by
`blkid`; `findmnt -T` resolves the directory to the *main encrypted
root filesystem*, and `du -sh` shows **40 MB** currently under
`research/` and `voice/`. No evidence yet verifies all running
Webbie models, settings or research are there. **Do not mount a
different filesystem over this directory**, which would hide existing
data, or delete its `nofail` fstab line until its intended use has
been assessed. Back up current files on independent storage.

Upgrade decision: **HOLD**, pending inspection of sda1, independent
backup, compatibility checks of actual 26.10 release-upgrader removals,
and an official upgrade offer. No installer USB requested or required.

## Active sda1 GRUB configuration independently confirmed

Owner's read-only `debugfs` results from October 15 conclusively show:

- `/dev/sda1:/grub/grub.cfg` is present: **7,946 bytes**, last modified
  October 2, 2026. This corresponds to the filesystem UUID searched by
  the active `EFI/SpiderOS/grub.cfg` stub.
- The small partition also contains `/grub/x86_64-efi/`,
  `/grub/i386-pc/`, `grubenv`, fonts and a wallpaper cache.
- The unmounted `sda1` GRUB config defines
  `Spider OS GNU/Linux` plus Linux `7.0.0-38-generic` and its
  recovery mode. Its menu entries search for `sda1` by UUID.
- **NOT YET VERIFIED:** Which `linux` and `initrd` file paths are
  referenced and whether those boot files also exist on `sda1`.
  The grep used `linux ` and `initrd `, which can miss commands
  using tabs. Get the actual menu entry lines with
  `debugfs -R 'cat /grub/grub.cfg' /dev/sda1` piped into
  `grep -nE '^[[:space:]]*(linux|initrd|linuxefi|initrdefi)[[:space:]]'`,
  then list the corresponding `sda1` files using read-only debugfs.
- An ordinary `update-grub` that writes the encrypted root's
  `/boot/grub/grub.cfg` may not update the **active sda1**
  `/grub/grub.cfg`. The risk is a mismatched kernel, initramfs
  and GRUB menu after a release upgrade.

Release gate remains HOLD until the kernel/initrd file paths, the
sda1 synchronization/rollback method, independent backup and normal
26.10 release-upgrade offer have all been reviewed. Do not run
`update-grub`, `grub-install`, reformat or change /dev/sda1
just to prepare these checks. Existing installer media is not needed.

## Boot path follow-up: /dev/sda1 has no /boot directory

The user's next read-only `debugfs` check confirmed that
`/dev/sda1` **does not contain a `/boot` directory**, while
the *main encrypted root's* `/boot/grub/grub.cfg` contains
`linux /boot/vmlinuz-7.0.0-38-generic` and
`initrd /boot/initrd.img-7.0.0-38-generic`.
This **does not prove** that the sda1 configuration directly loads
the same files or that they are unreachable. GRUB can load modules,
decrypt a LUKS container, select a different root and then invoke the
kernel from that filesystem. GNU GRUB documents `cryptomount` for
this purpose: https://www.gnu.org/software/grub/manual/grub/html_node/cryptomount.html

The owner's last terminal excerpt did **not include** the
`ACTIVE SDA1 KERNEL COMMANDS` output. Before any install,
read the *effective* sda1 boot commands and their surrounding
`set root` / `search` / `cryptomount` / `configfile` lines.
For example:

    sudo debugfs -R 'cat /grub/grub.cfg' /dev/sda1 2>/dev/null | grep -nE 'menuentry|linux|initrd|cryptomount|cryptodisk|insmod lvm|configfile|search|set root|set prefix|vmlinuz' | head -95
    sudo debugfs -R 'ls -l /' /dev/sda1 2>&1 | head -45

Read-only; never `debugfs -w`. Without the active command
sequence, do not presume a boot partition synchronization
strategy or attempt an upgrade. Independent backup and normal
release availability remain required.

## Previous boot relocation history and current fallback (October 5–6)

Historical Spider OS repair sessions matter for this upgrade:

- On **October 5**, `/boot` had been moved or staged off the legacy
  `/dev/sda1` ext4 boot partition into the encrypted
  `/dev/mapper/kali--vg-root`; `/dev/sda1` was intentionally kept
  as a fallback and had been inspected under `/mnt/spider-real-boot`.
- A separate `SpiderRoot` UEFI loader was prepared, with an attempted
  one-shot firmware selection (`BootNext 0007`). The resulting test
  did **not** establish a healthy boot into SpiderRoot; the machine
  reached GRUB command-line recovery and subsequently an emergency
  system state. Never assume that this experimental alternate boot
  option is validated, or automatically select it for the 26.10 upgrade.
- The **currently proven** firmware entry is `BootCurrent 0002`,
  `SpiderOS`, which loads its boot menu, kernel and initramfs from
  `/dev/sda1`. The on-disk root's `/boot` is a second location,
  not the tested firmware's immediate kernel source.
- On October 15, read-only `debugfs` confirmed
  `sda1:/vmlinuz-7.0.0-38-generic` is **17,320,328 bytes** and
  `sda1:/initrd.img-7.0.0-38-generic` is **84,340,560 bytes**,
  exactly matching sizes of their counterparts under root's `/boot`.
  Sizes do not guarantee identical contents. The sda1 ext4 filesystem
  reports **64,941 free 4,096-byte blocks**, about **254 MiB free**.
  The free-space estimate must account for bigger future initramfs
  files, staged fallbacks and other GRUB files. Never purge the known
  working kernel merely to make space.
- Preserve the working `SpiderOS` EFI entry and the small ext4
  `sda1` layout. Do **not** redo the previous relocation, activate
  SpiderRoot, update boot entries, or install kernels/hooks on the host
  as part of preparation.
- Develop/test a *separate* kernel/initramfs/config synchronization
  procedure and independent recovery strategy first. Keep the
  current custom kernel and initrd until the new boot path has been
  proven after the eventual in-place 26.10 upgrade.

This historical finding does not remove the **HOLD**: official
upgrader availability, an independently accessible data/boot backup,
the 26.10 actual proposed package removals and tested startup recovery
must still be established before starting a release upgrade.

## Confirmed boot chain and release-upgrade synchronization blocker

The October 15 complete `debugfs -R 'cat /grub/grub.cfg'` output settles
the outstanding command path. The active EFI stub loads
`/dev/sda1:/grub/grub.cfg`, whose default Spider OS menu sets
`root='hd0,gpt1'` and searches `/dev/sda1` UUID
`b8b48e84-c748-4741-9b94-a2f5bab50ca6` before executing:

    linux  /vmlinuz-7.0.0-38-generic root=/dev/mapper/kali--vg-root ro quiet splash ...
    initrd /initrd.img-7.0.0-38-generic

The recovery and advanced entries also reference those `/dev/sda1`-root
paths. There is no `/boot` directory on sda1. This means the current
EFI GRUB menu does **not** read the main encrypted root's
`/boot/vmlinuz-7.0.0-38-generic` and
`/boot/initrd.img-7.0.0-38-generic`; it attempts to load files
from the root of the separate sda1 ext4 filesystem. The exact presence
and consistency of these two sda1 files must still be verified using
read-only `debugfs stat`.

This is an upgrade **BLOCKER**. The conventional Ubuntu kernel/postinst
and `update-grub` path updates the installed root's
`/boot` and `/boot/grub/grub.cfg`, whereas the current active
`/dev/sda1` is not mounted and therefore may be skipped. A new kernel
and removed old `/lib/modules` can make the old sda1 boot menu fail.
Do **not** start `do-release-upgrade` until a backup, boot partition
synchronization, free-space and rollback plan are tested.

The preflight script now marks an EFI stub targeting an unmounted
filesystem as BLOCK, regardless of a clean package manager, free space,
or disabled Secure Boot. No installer USB is necessary, but a usable
independent backup and realistic rescue method are required.

Safe current-machine validation without mounting/writing:

    sudo debugfs -R 'stat /vmlinuz-7.0.0-38-generic' /dev/sda1
    sudo debugfs -R 'stat /initrd.img-7.0.0-38-generic' /dev/sda1
    sudo debugfs -R 'stats' /dev/sda1
    stat -c '%n %s bytes' /boot/vmlinuz-7.0.0-38-generic /boot/initrd.img-7.0.0-38-generic

Compare expected sizes and available blocks. It is **not yet safe**
to mount sda1 read/write, copy files, `grub-install`,
`update-grub`, edit fstab, install automated kernel hooks or
start the upgrade. Those tasks require staged/tested backup and
manual review first.

## Plymouth / LUKS boundary
The existing Spider Plymouth theme now draws the disk-password prompt and masked bullet count. This code is NOT yet verified with a real encrypted-root boot. Do not activate or rebuild the daily-use machine's initramfs from this candidate until a test confirms that the LUKS2 unlock prompt is displayed and responds normally.

The live ISO no longer forces plymouth.enable=0, but its inherited upstream initramfs may still show the upstream Ubuntu Studio splash until a rebuilt initramfs is verified. A bootloader wallpaper stored only inside the encrypted root cannot reliably load before the root is unlocked. That separate GRUB-to-/boot integration is not presented as complete. Bootloader, partition table, disk encryption and existing keys remain untouched by this change.

## Preflight on your existing Ubuntu Studio 26.04 host

First run the one-command **unprivileged and non-invasive** host report,
from a checked-out copy of this migration branch:

    bash distro/report-inplace-26-10.sh

This saves a local SUMMARY.txt, exact installed package inventory,
current 26.04-only apt simulation, source file names, service snapshot and
the known /lib32 dangling-link hazard. It makes no package, boot, service,
root-filesystem or release-upgrade changes. It needs no sudo or USB and never
contains a 26.10 proposed-removal simulation because that list is not available
until the release upgrader actually calculates it.

If a source checkout is not yet on the PC, a single safe fetch and execution
from the branch can be used in Konsole:

    curl -fL --retry 3 https://raw.githubusercontent.com/brokenandalone/spider-narive-os/upgrade/2610-startup-sets-20261015/distro/report-inplace-26-10.sh -o "$HOME/Downloads/spider-2610-readiness.sh"
    bash "$HOME/Downloads/spider-2610-readiness.sh"

Review the displayed SUMMARY.txt and blocker list first. The existing
full preflight remains available for an **optional later privileged audit**:

    bash distro/preflight-inplace-upgrade.sh

That existing full preflight asks for sudo and copies sensitive system config
into the user's home. Keep its report private, especially the crypttab and
system-service archives. Do not upload it publicly.

Neither preflight invokes the actual release upgrade. Back up your files, service configuration, encrypted disk header, boot files, Kali Bay volumes, Webbie models, and all live Bay content to a separately accessible location such as network storage or cloud storage. No USB creation is required. Preserve the exact LUKS unlock flow. Reconcile newer local program files against pinned Git sources before any overlay copy.

Only after review, switch the release upgrader from Prompt=lts to Prompt=normal via Ubuntu Studio's Software Sources settings. Use the supported normal do-release-upgrade path, not the -d development path or manual apt-codename rewriting.

## Optional developer ISO qualification (GitHub runner; no owner USB)
1. Official upstream SHA256/signature verified, Casper layer and installer metadata inspected.
2. Spider ISO builds and has a bootable BIOS/UEFI layout.
3. The live image reaches KDE with Spider identity, functional startup graphics, network and audio.
4. An isolated test virtual disk installs, boots without ISO, starts Spider Core, Webbie and The Web, and reboots again.
5. Separate LUKS2/encrypted disk test demonstrates visible password prompt and successful unlock.
6. Native bays, installed Studio, School, Author, Forage, Kali Bay, Media Center, system Recovery and user configuration pass tests.
7. A separately accessible backup and a realistic recovery route have been reviewed; no removable installation media is mandated.
8. The installed PC gets a fresh preflight before any in-place release upgrade. The actual release-upgrader proposal and removal list must be reviewed.

This PR is source preparation, not a verified production rollout. The 26.10 workflow is not a substitute for real encrypted boot hardware testing. Do not merge or install until the actual gates pass.

Known upstream hazards: a dangling /lib32 symlink can interrupt upgrades; some future GRUB changes impact unusual encrypted-/boot configurations; and Ubuntu Studio warns that installing tlp can remove power-profiles-daemon and critical desktop packages.


## Required in-place 26.04 -> 26.10 checks (no USB)

- Confirm the running OS really is Ubuntu Studio 26.04 and the package manager is clean.
- Confirm LUKS unlock and the installed GRUB boot path still work on two baseline boots.
- Capture enabled services, apt source list, package inventory, locally modified workspaces, and encrypted-disk mapping.
- Make a suitable independently accessible backup, and record what recovery is actually possible without USB.
- Inspect the release upgrader's specific proposed removals before consenting.
- Verify the boot, audio and bays after the normal release upgrade.
- Test new SDDM/Plasma images independently from Plymouth/initramfs before enabling a boot splash that affects encrypted unlock.
