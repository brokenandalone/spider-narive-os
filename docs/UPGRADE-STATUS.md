# Upgrade status — 8 October 2026

GitHub source completion does not establish installation on the owner PC.
Earlier owner confirmations cover the Guardian/Vault/Studio/Author foundations,
Webbie action gateway, Forage foundations, microphone watchdog, local Ollama
models, research timer, USB memory, and the original workspace wallpaper set.
Preserve those local configurations, including modified Webbie source.

## Published desktop build

The desktop release candidate is published in [PR #11](https://github.com/brokenandalone/spider-narive-os/pull/11),
commit `e8566713e199a53540d01bf4673c4171440c62b0`.
All 71 Python regression tests and the native Qt desktop integration passed,
along with feature validation and shell syntax checks. The integration covers
15 tabs, seven embedded workspaces, persistent editing/state/wallpapers,
installed-application launching and safe closure. This checks the build source;
the installed-PC acceptance items below remain open.

## Revised build order

Build The Web desktop foundation first. Keep the tested Author, School, Studio,
and playback repairs; integrate them into that foundation rather than rebuilding
workspace navigation independently. Playback repair is independent and can be
released alongside the desktop work.

1. [x] Recover earlier installation confirmations and preserve local Webbie and
   the owner’s 44px/40px button fixes. Installed-PC inventory still needs verification.
2. [x] Implement the selectable The Web X11 desktop session, its own Start,
   taskbar, clock and desktop surface. KDE infrastructure/secure locker remain;
   Plasma remains selectable and returns on shell failure. Installed login QA pending.
3. [x] Implement one persistent tab per workspace. Seven native Qt workspaces
   embed; unsaved editors/notes and running research block closure. External
   applications retain native windows, switched from the taskbar. Qt integration passes.
4. [x] Discover installed XDG/Flatpak/Snap applications and place them in Start
   and their corresponding workspace. Visibility/override/localization tests pass.
5. [x] Connect Author, School and Studio to native tabs, preserving existing
   on-disk data and selectively patching installed import compatibility.
6. [x] Build and package the Media Center playback repairs as a verified Linux
   ASAR upgrade, with locked dependencies, archive checksums and a backup installer.
   [Media PR #2](https://github.com/brokenandalone/Spider-Media-Center/pull/2)
   contains build commit `7811bafbbbf85fc4bb309f3aee0102c7e8d6c27a`.
   Ten playback regressions, real FFmpeg conversion, complete archive byte checks
   and tampered-archive rejection passed.
   Installation confirmed by the owner on 8 October 2026 at 20:07 local time:
   all four package checksum checks passed and the archive was installed.
   Backup: `/opt/spider-media-center/resources/app.asar.before-playback-20261008-200747-1055870`.
   [ ] Verify real Play,
   Pause, seek, local movies, compatible-copy preparation and cancellation,
   visualizer output, and broadcast stop/start. Source regressions pass.
7. [ ] Verify Webbie, Forage, Deep Forage, Kali Bay, Guardian, Vault and AI DJ from
   the new desktop. Preserve previously installed models, memory and timers.
   Voice enrollment and new AI DJ repair installation remain unconfirmed.
8. [x] Package Spider-branded secure lock-screen artwork using KDE's existing
   locker and authentication. Appearance setter backs up the previous config.
   Real automatic lock, password failure and unlock verification remain pending.
9. [x] Add the desktop-loading splash; retain the existing Spider Plymouth theme
   and boot configuration. Active installed boot-theme verification remains pending.
10. [x] Package and connect all recovered wallpaper collections: 59 artwork files,
    including today's seven new workspace designs and matching alternates, with
    independent saved choices and preserved original defaults.
    Final placement audit corrected two Study tags and included original
    workspace backgrounds in the installer package; existing installed images
    are never overwritten.
11. [ ] Install this release candidate and verify real SDDM login, KWin focus,
    window switching, lock/unlock, logout, multiple monitors, movies and splash
    transitions on the owner PC. Source/Qt checks cannot establish those results.
    A read-only installed-system preflight is now available at
    `the-web/package/verify-installed.py`; it checks wallpaper integrity and
    placement, session files, services and the tested Media Center archive.
    The ISO payload gate now expects the desktop session instead of the removed
    application-menu entry. Manual acceptance still needs owner-PC results.
    The updated suite passes 75 regressions. A staged new-desktop ISO payload
    fixture passes; reintroducing the old app entry is correctly rejected.

### Proposed application placement

| Workspace | Ubuntu Studio applications belong here |
| --- | --- |
| Studio | DAWs, instruments, effects, audio routing, recording, video editors and production tools |
| Media | Music/video players and media viewing |
| Author | Writing, documents and office applications |
| Art Lab | Painting, drawing, photography, design and 3D graphics |
| Dev Bay | Development tools and terminal emulators |
| School | Education, mathematics and scientific applications |
| Forage | Browsers and research, alongside Spider search |
| Communications | Email, chat and communications |
| System | File management, settings, administration and remaining utilities |
| Recovery | Backup and recovery tools, Guardian and Vault |
| Games | Installed games |

The catalog must honor XDG visibility, user overrides, executable availability,
and actual installed application entries. These are placement rules, not claims
that particular optional applications are already installed.

## Source-tested additions awaiting installation checks

The following newer additions have source tests, but no owner-PC installation
confirmation:

| Upgrade | Source location | Owner check after installing |
| --- | --- | --- |
| Author library, chapter history, canon notebook and bundle import | `author/` | Open Author; import the private bundle; edit, restart, restore a chapter version. |
| School dashboard and APA student papers | `study/` | Open School; check assignments; export and open a paper. |
| Installed Ubuntu Studio tool catalog | `studio/tools.py`, `studio/main.py` | Refresh tool detection and launch the already installed creative applications. |
| AI DJ HTTP reliability | `media/ai-dj/service.py` | Restart the user service; check health and prepare a spoken transition. |
| Media playback, visible errors, local compatibility preparation and radio state | Separate `brokenandalone/Spider-Media-Center` repository | Update the actual packaged application, then test Play/Pause/seek, a local movie, compatibility cancellation, and stop/start broadcast. |

The seven-workspace wallpaper pack and expanded earlier collection are now
packaged in `branding/wallpapers/collection/`. Their source integration is tested;
owner-PC installation remains unconfirmed. Do not replace the confirmed
original wallpapers merely because alternatives exist.

The Media Center code repairs do not update an installed Kabel 7.5 executable.
They must be included in its next build. Follow that repository's playback
verification notes; the native compatibility action prepares a separate local
movie copy for the embedded player. Full direct libVLC decoding remains pending.

For the installed AI DJ, after this service source has been deployed to its
existing path:

```bash
systemctl --user restart spider-ai-dj.service
curl --fail http://127.0.0.1:9876/health
curl --fail -H 'Content-Type: application/json' \
  -d '{"currentTrack":{"title":"First track"},"nextTrack":{"title":"Next track"}}' \
  http://127.0.0.1:9876/dj/prepare
```

A successful prepare response includes `script` and a local `audioFile` URL.
Listen to the result before calling the installed AI DJ verified. This work does
not migrate the OS base or replace owner-modified Webbie files.
