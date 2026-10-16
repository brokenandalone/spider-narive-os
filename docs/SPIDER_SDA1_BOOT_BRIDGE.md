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
