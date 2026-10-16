# Spider OS: Preserve the proven /dev/sda1 boot chain

**Status: engineering preparation, not authorized installation.**
This workflow targets the owner's Ubuntu Studio 26.04.1 LTS / LUKS2-LVM
system, with active UEFI SpiderOS, Secure Boot disabled, and an unmounted
449 MB ext4 boot partition.

## What the firmware actually starts

1. UEFI Boot0002 -> `SPIDER_EFI:/EFI/SpiderOS/grubx64.efi`.
2. `SPIDER_EFI:/EFI/SpiderOS/grub.cfg` finds ext4 partition UUID
   `b8b48e84-c748-4741-9b94-a2f5bab50ca6` (`/dev/sda1`) and
   includes `/grub/grub.cfg` there.
3. The active default menu on `/dev/sda1` loads its own
   `/vmlinuz-7.0.0-38-generic` and
   `/initrd.img-7.0.0-38-generic`, specifying
   `root=/dev/mapper/kali--vg-root`.
4. The initramfs participates in accessing the encrypted root. Kernel
   and initrd also exist under the main encrypted root's `/boot`, but
   that is NOT the firmware's default source.
5. The previous SpiderRoot alternative was not verified functional.
   Never assume it is a recovery path.

On October 15, the **sda1** boot file byte lengths matched the encrypted
root's copies: kernel 17,320,328 bytes; initrd 84,340,560 bytes. The
ext4 partition had 64,941 free 4,096-byte blocks: ~254 MiB free.
Byte-length equality is NOT byte-for-byte verification.

## Read-only audit you can run now

From the checked-out candidate branch:

```bash
sudo python3 distro/spider-sda1-boot-bridge.py audit
```

This checks the expected UUID, the EFI stub, that sda1 is currently
unmounted, the default GRUB kernel/initrd version, that their regular
files are present on sda1 and on root's `/boot`, plus file sizes
and free-space. Nothing is mounted or edited, and no release upgrade is
run. It exits nonzero on missing/mismatched boot assets.
It **does not** prove a successful future boot, compare byte-for-byte
hashes, or certify a backup.

## Byte-for-byte verification of the proven kernel (safe next action)

The additional `verify` subcommand builds on the already-passing
read-only `audit`. It uses `debugfs` to copy the currently selected
sda1 kernel and initramfs to a temporary private directory in
`/var/tmp` **on the main root filesystem**, calculates SHA256 hashes
for these temporary copies and the original root's `/boot` copies,
reports MATCH or MISMATCH, and removes the temporary files. The
sda1 partition is opened **read-only and never mounted**.

From the branch source:

```bash
sudo python3 distro/spider-sda1-boot-bridge.py verify
```

This requires at least approximately 100 MiB of temporary free space
and does not back up any files independently. A mismatch stops
verification and must be investigated; never overwrite either boot
copy to force a match. A match establishes identical bytes, not
whether a future 26.10 boot or restoration will succeed.

## Owner's October 16 live SHA256 verification: PASS

The owner ran the `verify` mode on the actual Ubuntu Studio 26.04.1
Spider OS installation. The audit reported the known default
`7.0.0-38-generic` and **253 MiB** available on `/dev/sda1`.

Both exact-byte comparisons **passed**:

| File on unmounted /dev/sda1 | SHA256, matches root's /boot file |
| --- | --- |
| `/vmlinuz-7.0.0-38-generic` | `9f55ef7253055a9cf68f8a04323c93dead2fca617386d842fbde9ca7b178b27e` |
| `/initrd.img-7.0.0-38-generic` | `9a3d628f34802d68f996db3b1614b82b647242834b50d9c1aea49e6debe94c9e` |

This resolves the previous **kernel/initrd content-equality verification gate**.
The `verify` command reported no changes to sda1 or main /boot.

**Important:** SHA equality is *not* confirmation of an independent
backup, a tested restore route, an upgrade-ready boot synchronization
process, or a 26.10 kernel that fits sda1. Do not remove the
known-good 7.0.0-38 kernel, repartition the disk, change UEFI boot
entries or run the release upgrader. Independent backup and boot
rollback remain required first.

## Offline candidate generator (after a new kernel is available)

Once the new Ubuntu kernel and corresponding initramfs exist in the
*installed root's* `/boot`, the tool can create a **preview-only**
sda1 GRUB menu with a separately selectable test kernel, preserving the
current Spider OS default and recovery entries:

```bash
sudo python3 distro/spider-sda1-boot-bridge.py prepare \
  --version NEW_KERNEL_VERSION_HERE \
  --output /home/spider/Downloads/spider-sda1-candidate-NEW_KERNEL_VERSION_HERE
```

This prints a stop condition if the new kernel or initrd is missing,
either is empty, the current boot is mismatched, the candidate kernel
is already referenced, or free space would drop below a 64 MiB reserve.
The output is a private local directory with `grub.cfg.candidate`
and `manifest.json` containing source-file checksums.

**It does not mount sda1, copy new boot files there, change GRUB
defaults, activate a GRUB entry, or change EFI.** It is a preparation
artifact for a later owner-reviewed, backup-first procedure, NOT an
automatically executable synchronization tool.

## Independent OneDrive candidate confirmed October 16

The owner's live `rclone about webbie_onedrive:` returned **100 GiB
total, 5.600 GiB used, 94.400 GiB available**. The host previously
reported approximately **209 GiB used on the root filesystem**,
so OneDrive is **not** sufficient for a full system image. It can
nevertheless serve as independent off-disk storage for carefully
selected critical recovery files once properly encrypted, budgeted,
uploaded and successfully restored in a test.

**Use a client-side `rclone crypt` overlay**, configured separately
from `webbie_onedrive:` and pointing inside a dedicated directory such
as `webbie_onedrive:SpiderOS-Private-Recovery-2610`. Do not write
unencrypted tar archives, EFI images, encrypted-disk headers or
sensitive service configuration directly to the plain OneDrive remote.
The crypt remote's password and optional salt must be recoverable from
somewhere **other than the same PC or this OneDrive backup**, e.g.
a secure password manager with independent access. Do not paste the
password, any rclone configuration, OAuth tokens or encryption secrets
into chat or public CI logs. The lightly obscured rclone config is
**not** secure encryption of the config itself: see
https://rclone.org/crypt/ .

Before enabling backup uploads, collect a read-only size inventory:
```bash
sudo du -xsh /etc /opt /home/spider /usr/local /srv \
  /var/lib/spider-os /var/lib/containers /var/lib/bcn-broadcast \
  2>/dev/null || true
rclone about webbie_onedrive:
```
Note these categories can contain overlapping data, omitted paths,
large caches, symlinks or project files elsewhere: sizes are a
starting point, not a full inventory or guaranteed upload estimate.
Reserve space for file overhead and future backups. Never purge models,
music or projects automatically to fit the quota.

The new boot-only backup script targets a **mounted independent
filesystem**, not a bare rclone remote. It must **not** be passed a
local same-disk directory that will later be synced to OneDrive
as if it were a verified independent destination. For cloud storage
prepare a separate explicit upload/recovery workflow and confirm a
small restore test before claiming protection. Offline recovery of a
non-booting, LUKS-encrypted PC requires an independently usable rescue
method; an online cloud copy alone does not solve this.

## Independent boot-backup helper

The branch now includes `distro/backup-spider-boot-independent.sh`.
It requires a **separately mounted physical drive or approved network
filesystem** and refuses destinations on the SpiderOS `/dev/sda`
disk. With no backup volume mounted, it stops without changes.

After a proper off-disk destination is mounted and its privacy/encryption
is considered, inspect the target before writing anything:

```bash
sudo bash distro/backup-spider-boot-independent.sh --check /path/to/independent/mounted/backup-directory
```

Only with an independently mounted destination, run the explicit backup
operation:

```bash
sudo bash distro/backup-spider-boot-independent.sh --backup /path/to/independent/mounted/backup-directory
```

The script reads and stores full raw images of `/dev/sda1` and
`/dev/sda2` (never writes to them), root's `/boot` tree,
`/var/lib/spider-os/webbie-brain`, partition table and drive mapping
on that destination. It confirms full image lengths, SHA256 checksums
and archive integrity, and renames the verified backup folder from
`.partial` to final only on success. File copies can contain
sensitive data, so store the result privately on encrypted storage.

This **only protects the boot chain and one Webbie brain directory**.
It does not back up the full encrypted root, all programs, studio,
Nova, users' media, services, Git changes or the LUKS header; those
need a separate full-system backup and recovery plan. There is
currently **no confirmed independent backup destination** on the
owner's PC.

## Hard gates before 26.10

- **Independent backup:** preserve an image of /dev/sda1, the EFI
  partition/SpiderOS files, encrypted LUKS metadata and a separate
  backup of customized system files, Webbie, Nova, bays, models and
  creative data on a confirmed *different physical or network*
  device. Main disk backup folders are NOT independent backup. LUKS
  header backups are sensitive and must be stored securely.
- **Known restore method:** a practical way to recover the machine
  without USB installation media must be available. No tested
  recovery method was demonstrated by the earlier SpiderRoot attempt.
- **Synchronization and fallback:** an owner-reviewed installer must
  copy new kernel/initramfs to sda1 and update its grub.cfg only after
  backing up existing sda1. Keep the proven kernel and initrd as a
  recovery entry and ensure older kernel modules remain available
  until the new kernel actually boots. The change needs a one-time
  manual boot test and explicit confirmation before changing default.
- **Space and integrity:** reserve >64 MiB in addition to the
  new kernel+initramfs; compare full hashes after any transfer.
  If room is insufficient, stop. Do NOT delete proven boot files.
- **Release channel:** use normal offered Ubuntu release upgrade when
  available, not `-d` or manual apt source codename replacement.
- **Package removal review:** do not accept removal of Webbie,
  desktop, Studio, Kali or other essential packages without review.

The source-check CI validates code and offline behavior. It cannot
prove the owner's encrypted system will boot after a kernel or GRUB
update. No USB installer or reformat is proposed.
