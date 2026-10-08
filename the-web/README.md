# The Web desktop build

The Web is a selectable **X11 desktop session**, with its own desktop surface, Start menu, native workspace tabs, taskbar, window switching, clock and wallpaper choices. KDE supplies KWin, the secure session locker, policy agent, audio integration and desktop portals. Its visible Plasma shell is stopped only for this running session; Plasma remains in the login chooser and is restarted if The Web exits unexpectedly.

## Included

- Fifteen tabs including The Web home; seven embedded native Spider workspaces: Webbie, Forage, Deep Forage, Studio, Author, School and Kali Bay.
- One live instance per workspace, restored open-tab selection, manuscript/notes save checks and protection against closing running research.
- Installed XDG applications in Start and their workspace: production in Studio, viewers in Media, office in Author, graphics in Art Lab, development in Dev Bay, education in School, browsers in Forage, communications, security, recovery, system and games. Flatpak and Snap application exports are included. Applications keep their native windows and can be switched from the taskbar.
- Fifty-nine archived artwork files, including today's seven workspace designs and their matching alternates. Existing backgrounds remain available and retain their defaults. Choices persist independently per workspace.
- Spider desktop-loading splash. Spider artwork for KDE's secure lock screen, with a backup of the previous wallpaper configuration. Authentication continues to use KDE; no password is handled by The Web.
- Selective installed-PC installer and ISO source integration. Existing native workspace files receive only small import-compatibility/save-guard changes. Existing Webbie source, model selection, memory, timers, manuscripts and notes are preserved.

## Install on the existing Ubuntu Studio machine

From the extracted build or this branch:

```bash
sudo bash the-web/package/install-desktop.sh
```

The installer requires the existing KDE X11 runtime. It installs `wmctrl` and system PyQt5 if absent, backs up existing shell/source files, installs the session entry, disables old The Web autostarts, and applies Spider lock-screen artwork. It does not reboot or change bootloaders. Log out and choose **The Web (X11)** on the login screen. Only one graphical session per user is supported.

The runtime log is `~/.local/state/spider-os/desktop-session.log`. Configuration lives under the user's XDG config directory in `spider-os/desktop.json` and `spider-os/wallpapers.json`.

A missing or incompatible native workspace is reported inside its tab. Install the corresponding tested Author/School/Studio source upgrade first when needed. The desktop package supplies missing Author, Studio and School modules but preserves already installed copies. Media uses the existing packaged Media Center; its separately published playback repair still requires a Media Center rebuild.

## Boot splash

The existing Spider Plymouth theme is included under `distro/config/plymouth/`, with its Spider artwork. The ISO build already installs it. This desktop installer preserves the currently working boot configuration; it does not alter initramfs, GRUB, encryption or the active boot theme. Desktop-loading splash and secure lock-screen artwork are separate from Plymouth.

## Verification

Source: 71 Python regressions, feature-script validation, shell syntax checks, School/APA smoke checks and a native Qt integration check covering all fifteen tabs, seven native modules, editing persistence, app launching, wallpaper/state persistence and rejected unsafe closure. All artwork files decode and match their checksums.

A real SDDM login, KWin focus/window switching, multi-monitor behavior, automatic lock, authentication/unlock and logout require verification on the installed machine. Offscreen Qt checks do not establish those results. This build is a release candidate until that installed-session verification is complete. X11 is supported; no Wayland session is provided.

To return to the previous desktop, log out and select **Plasma**. Source backups are retained under `/usr/local/lib/spider-os/upgrade-backups/`; the prior lock-screen config is `~/.config/kscreenlockerrc.before-the-web` when one existed.
