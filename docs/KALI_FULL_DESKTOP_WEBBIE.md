# Kali Bay: real Kali Linux desktop with Webbie

## Owner decision
**Kali Bay must run Kali Linux as Kali Linux**, not merely emulate the look of
the Kali desktop. Preserve Spider OS as the host and keep the existing
`kali-linux-everything` Distrobox container intact.

## Two run modes in the same Kali Bay

**Quick tools:** rootless Kali Distrobox; real Kali executables for quick
Wireshark/Burp/ZAP/Ghidra/terminal work. Shares the host kernel and cannot
reproduce every systemd, driver, networking or wireless capability of an
installed Kali system.

**Full Kali Linux desktop:** a separately provisioned QEMU/KVM libvirt guest,
fixed VM name `spider-kali-desktop`, on `qemu:///system`. Use an official
Kali installer ISO, verify its SHA256 against Kali's published checksums, and
choose a complete Kali XFCE desktop. The guest has its own booted kernel,
services, applications, settings, apt repositories and desktop. It is
displayed through `virt-viewer` as a guest console window alongside the
Spider OS Webbie dock. **An embedded SPICE canvas within the Kali Bay Qt
widget is not implemented yet.** A separate guest-console window is the
first qualified step.

The native Kali Bay `DESKTOP HUB` now exposes **CHECK KALI DESKTOP**,
**OPEN FULL KALI DESKTOP**, **SET UP / MANAGE KALI VM** and
**START EXISTING KALI VM** in addition to the existing Kali terminal, tools,
Purple Defense and Webbie links. The first three are non-destructive.
Starting the fixed existing VM requires an explicit GUI Yes/No confirmation.
No install, download, disk allocation, network interface creation, or
permission changes occur in the source build.

## Machine preparation, deliberately separate from the application upgrade

1. After the host's post-outage disk check and verified backup, check that
   the processor supports virtualization and firmware has Intel VT-x or
   AMD-V enabled, then inspect `/dev/kvm` and installed `virsh`,
   `virt-manager`, `virt-viewer` and `qemu-system-x86_64`.
2. Install the Ubuntu host's needed virtualization packages through normal
   explicitly approved system administration. Do not have Webbie silently
   run sudo, add users to libvirt groups, start daemons or configure bridges.
3. Download the **official Kali Linux installer ISO** from
   https://www.kali.org/get-kali/ and verify the checksum against Kali's
   official release. Do not use unverified third-party virtual disks.
4. In virt-manager connect to `qemu:///system`, create a new Kali VM
   specifically named **spider-kali-desktop**, choose the official ISO,
   allocate RAM/CPUs/disk based on actual host capacity and leave the
   default NAT or isolated virtual network. Never overwrite the Spider OS
   LUKS drive; the VM disk is a separate virtual disk.
5. Finish the Kali installation interactively. Use Kali's normal user
   account, password and `sudo` within the guest, as intended. Apply
   guest updates through Kali, not the Ubuntu host's package manager.
6. Start the VM, open the console from Kali Bay, take a usable VM snapshot
   after first verified boot, and test mouse, keyboard, network and tools.
7. For advanced wireless monitoring/injection or USB tools, confirm that
   the adapter is capable of that mode and attach it **explicitly** to the
   Kali guest using virt-manager's device controls. VM NICs and shared
   kernel containers cannot manufacture hardware capabilities. Keep host
   networking unchanged until a specific authorized lab requires more.
8. Webbie can currently explain tools, check VM state, open the console,
   and open virt-manager. It **cannot automatically see the VM display**,
   control a guest terminal, authorize scans, run guest sudo, or act on
   arbitrary model-generated commands. These require a consented guest
   integration phase with per-operation confirmation, visible sharing,
   scoped read-only data and auditable actions.

## Security, backups and rollout

- The VM gateway `kali-bay/vm/kali_desktop.py` has a fixed VM name and
  libvirt URI. Only `status`, `manager`, `console`, `start` are supported.
  Webbie exposes only `status`, `manager`, `console` and **never voice
  power control** while owner/Speakers authorization is unverified.
- The Webbie bridge accepts literal explicit human requests, not webcam
  content, workspace titles, tool output or generated language-model text.
- Kali Bay's Distrobox survives untouched. Installing the new source files
  does not create or boot a VM, download any ISO, alter network settings,
  modify host kernel modules, pass through hardware or change LUKS/GRUB.
- The unified Spider OS release manifest includes the Kali UI, manager
  and gateway, with known-baseline checks and rollback receipts. Inspect
  installed locally customized sources before any write; do not run
  separate overlapping installers on the same release.
- Source Qt/VM/assistant tests use mocked libvirt and never power on a VM.
  Physical installed-PC checks remain necessary before completion.

Official sources:
- https://www.kali.org/docs/virtualization/install-qemu-guest-vm/
- https://www.kali.org/docs/introduction/download-official-kali-linux-images/
- https://www.kali.org/docs/introduction/should-i-use-kali-linux/
