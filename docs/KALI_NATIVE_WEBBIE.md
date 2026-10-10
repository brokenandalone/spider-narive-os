# Kali Bay Native: full Kali tool experience within Spider OS

## Product decision (2026-10-10)
The owner wants to **use Kali Linux from inside the Spider OS Kali Bay**, with
Webbie's help, without a separate virtual machine as the default workflow.

The existing Kali Distrobox is the primary environment. It provides **real
Kali Linux userspace, Kali apt repositories, graphical applications and an
interactive shell**, all accessed from Spider OS/The Web. A VM is not a
prerequisite or background dependency. The separate draft PR #41 VM option
may be retained for advanced hardware cases only, not installed as part of
this native release.

## Behavior delivered by the source upgrade
- **KALI TERMINAL** opens the existing Kali container's login shell in
  Konsole. If the Kali container does not exist, the launcher now stops
  and directs the owner to explicit setup rather than silently creating a
  new container.
- **KALI PACKAGE MANAGER** opens a Kali shell and explains apt; it does
  not update, install or remove packages automatically. The owner can
  operate `apt`, `dpkg` and `sudo` inside Kali interactively as Kali
  intends, subject to container and user permissions.
- **INSTALLED KALI PACKAGES** presents a read-only package inventory by
  querying the existing, running container, without starting it.
- Existing Kali tools, Offensive and Purple categories, searchable native
  app launcher and persistent Kali files all remain in place.
- Webbie can answer questions about Kali tools and open the interactive
  terminal, Kali package manager or read-only inventory on an **explicit,
  literal user request**. No model-generated, camera-generated or
  workspace-metadata text may supply executable commands.
- The existing Webbie voice profile and The Web assistant dock are reused;
  Kali Bay does not spawn a second Webbie.

## What is Kali and what is Spider OS
- The GUI/window manager and desktop integrations are **Spider OS**.
- Kali's package database, installed Kali applications and CLI tools live
  **inside the existing Kali Distrobox**. Do not add Kali APT repositories
  to the Ubuntu host. Do not replace the host kernel with Kali's kernel.
- Kali GUI apps are displayed as native windows on Spider OS's KDE/X11
  session. A separate entire Kali XFCE login session is not needed.
- Distrobox is heavily integrated with the host, shares its kernel and is
  not a high-isolation security boundary. Do not assume root in a
  rootless container grants host kernel or device-level capabilities.
- Some wireless monitor/injection, driver, USB, privileged network and
  systemd features require separate hardware and carefully reviewed host
  or VM/boot provisioning; they are **not** promised by this source build.

## What remains before installed-PC completion
1. After the power-outage host disk/backup check, confirm the original
   Kali container still exists and its package database is healthy; do
   not blindly reinstall `kali-linux-everything`.
2. Qualify the source upgrades and one rollback-safe Spider OS release
   with existing customized Webbie/Kali files; do not run two installers
   that overwrite each other.
3. With permission and as owner, explicitly open the Kali terminal.
   Test `cat /etc/os-release`, `command -v nmap`, `apt-cache policy`,
   a GUI app such as Wireshark and the Kali package inventory.
4. Test actual Kali GUI app behavior, persistent files, terminal history,
   normal apt operations and selective peripheral permissions on the
   installed PC. No active scanning targets are selected by default.
5. Follow up with consented screen/terminal context for Webbie to help
   interpret Kali output, plus an approval and audit trail before any
   target-based action. Webbie's direct tool actions stay allowlisted.

## References
- https://distrobox.it/
- https://www.kali.org/docs/introduction/should-i-use-kali-linux/
- https://www.kali.org/docs/general-use/kernel-configuration/
