# Spider OS 26.10: Release Gate and Startup Sets

Updated October 15, 2026

## Official upstream
Ubuntu Studio 26.10 Stonking Stingray released today and officially supports upgrading from Ubuntu Studio 26.04 LTS. It is supported until July 2027.
- https://ubuntustudio.org/2026/10/ubuntu-studio-26-10-released/
- https://discourse.ubuntu.com/t/ubuntu-studio-26-10-release-notes/88657
- https://documentation.ubuntu.com/release-notes/26.10/

The migration branch configuration points to the final 26.10 ISO, release channel, and stonking codename.

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

## Plymouth / LUKS boundary
The existing Spider Plymouth theme now draws the disk-password prompt and masked bullet count. This code is NOT yet verified with a real encrypted-root boot. Do not activate or rebuild the daily-use machine's initramfs from this candidate until a test confirms that the LUKS2 unlock prompt is displayed and responds normally.

The live ISO no longer forces plymouth.enable=0, but its inherited upstream initramfs may still show the upstream Ubuntu Studio splash until a rebuilt initramfs is verified. A bootloader wallpaper stored only inside the encrypted root cannot reliably load before the root is unlocked. That separate GRUB-to-/boot integration is not presented as complete. Bootloader, partition table, disk encryption and existing keys remain untouched by this change.

## Preflight on your existing Ubuntu Studio 26.04 host

    bash distro/check-26-10-readiness.sh
    bash distro/preflight-inplace-upgrade.sh

Both inspect and report. Neither invokes the release upgrade. Back up your files, service configuration, encrypted disk header, boot files, Kali Bay volumes, Webbie models, and all live Bay content to tested external recovery storage. Preserve the exact LUKS unlock flow. Reconcile newer local program files against pinned Git sources before any overlay copy.

Only after review, switch the release upgrader from Prompt=lts to Prompt=normal via Ubuntu Studio's Software Sources settings. Use the supported normal do-release-upgrade path, not the -d development path or manual apt-codename rewriting.

## Required qualification gates
1. Official upstream SHA256/signature verified, Casper layer and installer metadata inspected.
2. Spider ISO builds and has a bootable BIOS/UEFI layout.
3. The live image reaches KDE with Spider identity, functional startup graphics, network and audio.
4. An isolated test virtual disk installs, boots without ISO, starts Spider Core, Webbie and The Web, and reboots again.
5. Separate LUKS2/encrypted disk test demonstrates visible password prompt and successful unlock.
6. Native bays, installed Studio, School, Author, Forage, Kali Bay, Media Center, system Recovery and user configuration pass tests.
7. Known-good rollback media and external backups have been tested.
8. The installed PC gets a fresh preflight after all other gates pass.

This PR is source preparation, not a verified production rollout. The 26.10 workflow is not a substitute for real encrypted boot hardware testing. Do not merge or install until the actual gates pass.

Known upstream hazards: a dangling /lib32 symlink can interrupt upgrades; some future GRUB changes impact unusual encrypted-/boot configurations; and Ubuntu Studio warns that installing tlp can remove power-profiles-daemon and critical desktop packages.
