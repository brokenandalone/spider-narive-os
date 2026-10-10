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
- The Kali Bay Desktop Hub has **LOAD ALL INSTALLED KALI APPS**. It queries
  the running container's real system application menu using `kali-bay
  apps-json`, validates installed `*.desktop` identifiers, and merges the
  installed entries into the searchable/filtered list. The list isn't limited
  to Spider's ten featured shortcuts.
- An owner-selected application uses `kali-bay app-check <id>` followed by
  `kali-bay app-open <id>` via Kali's own `gio launch`. System desktop files
  are read from `/usr/share/applications` inside Kali, not Spider OS host
  binaries. No shell command or path is accepted from the app label.
- **LOAD ALL INSTALLED KALI APPS** only reads the running container and does
  not start it, install packages or launch applications. If the container
  is stopped, Kali Bay reports why the catalog is unavailable.
- Existing Kali tools, Offensive and Purple categories, the ten featured
  static shortcuts and persistent Kali files all remain in place.
- Webbie can answer questions about Kali tools and open the interactive
  terminal, Kali package manager or read-only inventory on an **explicit,
  literal user request**. No model-generated, camera-generated or
  workspace-metadata text may supply executable commands.
- Webbie additionally supports **list installed Kali apps** and
  **find Kali app Wireshark**, executing only a read-only inventory query.
  Dynamic apps require manual selection in Kali Bay; Webbie does not
  execute arbitrary desktop entries from voice or language-model output.
- The existing Webbie resident agent and voice service are reused.
  The standalone Kali Bay window now has its own purple **WEBBIE | KALI BAY**
  text-chat dock, which connects asynchronously to Webbie's existing private
  per-user Unix socket. No second AI model, microphone listener, camera or
  privileged daemon is launched. Only explicitly typed messages are sent;
  the response is displayed without blocking Kali Bay's main GUI. The Web's
  original Webbie assistant dock remains independent but uses the same agent.

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
