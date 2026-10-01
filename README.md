# Spider Narive OS

Native Spider OS development build based on Ubuntu Studio 24.04.5 and KDE Plasma.
Ubuntu remains the package and hardware foundation. Spider OS supplies the visible
identity, The Web desktop launcher, and Webbie resident service. Ubuntu Studio
applications are retained.

This repository replaces the experimental kernel scaffold with the Ubuntu-based
ISO builder from Spider-OS1.

## Build through GitHub

Open Actions, select **Build Native Spider OS**, and choose **Run workflow**.
The workflow publishes a development release with split ISO pieces, a checksum,
and reassembly instructions. Reassemble and verify the ISO before writing a USB.

## Local build

On an Ubuntu Linux build machine with sufficient free disk space:

```bash
sudo apt-get install curl rsync squashfs-tools xorriso python3-yaml
sudo -E ./distro/build-iso.sh
```

The builder verifies the official base ISO and adds Spider files to both the
installed `standard.squashfs` and live layers. It updates installer source-size
metadata and produces `build/Spider_OS_24.04.5_amd64.iso`.

The installer is Ubuntu desktop bootstrap/Subiquity. Calamares shellprocess YAML
is not used. The installed image contains the payload, Spider Core system service,
globally enabled Webbie user service, and KDE autostart entries.

## Repair status

- Spider Core starts under multi-user.target without waiting on graphical.target.
- Webbie remains a user service: `systemctl --user status webbie`.
- Installer source IDs and paths are preserved while installed size is refreshed.
- os-release is written safely when the upstream file is a symlink.

An ISO build, installation to a writable virtual disk, and reboot are still needed
to validate this migration end to end. Live USB boot alone does not prove installation.
The feature-complete branch supplies Webbie voice and local Ollama AI, Forage and
Deep Forage, Study, Kali Bay, and the expanded The Web launcher. The builder bundles
Whisper base.en and qwen3:1.7b; neural TTS and web search require a network connection.

All ten approved backgrounds (The Web and nine workspace images), the splash, and
logo are included in both image layers. The Web provides a background selector and
switches its background when opening a workspace.

The default GitHub workflow builds the public image. Private Kabel/AI DJ packages
remain excluded from public distribution, following the existing profile split.
For a personal build, place the approved normalized Kabel ZIP in
`distro/assets/media/` and run `sudo -E ./distro/build-personal.sh`. The ZIP is ignored
by Git. This command fails clearly if the private package is missing.

Branch audit: `brokenandalone-patch-1`, `fix/install-and-boot`, and
`fix/live-boot-branding` are already ancestors of Spider-OS1 main. The Codespace
branch matches main. The two unmerged `spider-os-feature-complete` commits are now
integrated, retaining the later service, installer, and live-session repairs.
`finish-spider-os.sh` now validates the integrated source rather than overwriting it.
