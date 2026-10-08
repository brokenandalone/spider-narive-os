# Kali Bay and visible workspace wallpapers: reliability batch

This source-only upgrade is stacked after the Forage local-index PR. It does **not**
install anything on the encrypted Spider OS PC, rebuild the ISO, overwrite the
user's running desktop, or install the full Kali security metapackage.

## The Web wallpaper rendering

The old The Web implementation set a QMainWindow palette brush while the
opaque central workspace widget occupied the same window. This could conceal
the wallpapers even though PNG images existed on disk. The new `WallpaperWidget`
draws each selected image on the visible central widget, center-cropped to the
available area, with a translucent dark overlay for legible controls.

This preserves existing PNG paths and the existing 11 workspace selection IDs.
It does not assert that all 45 gallery photographs can be selected, nor does
it replace missing artwork. The Author entry retains the existing System image
fallback until a dedicated image is included in a qualified package.

`tests/check-the-web.py` now tests distinct red/blue backgrounds drawn on
the visible widget in offscreen Qt, in addition to selecting all existing
workspace images. Check actual visual composition on the installed PC before
promotion and keep a copy of the installed `the-web/shell/main.py` for rollback.

## Kali Bay state and package-safety improvements

The original `kali-bay status` called `distrobox enter`. On a partially
initialized Kali image this could trigger Distrobox's first-run installation,
so merely refreshing Kali Bay's graphical status risked restarting package
operations and re-triggering broken `systemd`/`udev` setup. Status now uses a
read-only `podman inspect` and `podman exec` package query **only when the
existing container is running**. It never starts containers, calls Distrobox
or repairs packages.

`kali-bay doctor` provides read-only status and package diagnostics. For
example, after installing the source-only launcher to its designated location:

```bash
/usr/local/lib/spider-os/kali-bay/bin/kali-bay doctor
/usr/local/lib/spider-os/kali-bay/bin/kali-bay status
```

The `update` operation no longer runs `apt-get autoremove -y`; package
removal must be assessed explicitly rather than performed silently. Full-toolset
setup remains a separate explicit action. The previous `udev` and `systemd`
compatibility overrides applied inside the user's existing container are not
modified or relied on by this source batch.

Kali Bay is a Distrobox container sharing some host resources and is not an
independent high-security VM. Do not enable privileged mode to work around
`fchownat` failures or blindly remove package locks. Back up important local
changes before modifying the runtime, and check disk space before installing
`kali-linux-everything`.

## Qualification and deployment

1. GitHub: pass Python unit tests, shell syntax, source validation, and offscreen
   UI image painting smoke tests on pinned Ubuntu 24.04.
2. Installed machine: inventory locally modified The Web and Kali Bay scripts,
   back them up, and compare before selective deployment. In particular,
   preserve unrelated Webbie voice/security and media fixes.
3. Visually verify purple artwork actually appears behind controls after
   selecting two different workspaces; close/reopen The Web and test fallback.
4. Verify `kali-bay status` with running and stopped containers is harmless.
   Use `kali-bay doctor`, confirm the repaired Kali packages, and avoid
   rerunning the full Kali metapackage by accident.
5. Test rollback using the saved installed files before merging or upgrading
   the only working OS.

Passing source tests does not mean the installed PC has been updated.
