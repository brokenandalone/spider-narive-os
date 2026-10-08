# Upgrade status — 8 October 2026

GitHub source completion does not establish installation on the owner PC.
Earlier owner confirmations cover the Guardian/Vault/Studio/Author foundations,
Webbie action gateway, Forage foundations, microphone watchdog, local Ollama
models, research timer, USB memory, and the original workspace wallpaper set.
Preserve those local configurations, including modified Webbie source.

## Revised build order

Build The Web desktop foundation first. Keep the tested Author, School, Studio,
and playback repairs; integrate them into that foundation rather than rebuilding
workspace navigation independently. Playback repair is independent and can be
released alongside the desktop work.

1. [x] Recover earlier installation confirmations and preserve local Webbie and
   the owner’s 44px/40px button fixes. Installed-PC inventory still needs verification.
2. [ ] Make The Web a selectable desktop session with KWin beneath it, its own
   Start menu, taskbar, clock, and desktop surface. Keep the existing Plasma
   session available. Desktop-session wiring is not implemented yet.
3. [ ] Make workspace actions open or focus one tab per workspace; preserve open
   state and honor unsaved-data checks on close. Embed Spider’s own Qt workspaces
   where supported. External Ubuntu Studio apps keep their native windows and
   need taskbar/window switching integration. Native module isolation is drafted.
4. [ ] Discover installed Ubuntu Studio applications automatically and place them
   in both the Start menu and the appropriate workspace. Discovery/category code
   is drafted; its desktop UI integration is not implemented yet.
5. [ ] Integrate the tested Author, School and Studio additions into workspace tabs.
   These upgrades exist in source; owner-PC installation is not confirmed.
6. [ ] Build and install the published Media Center repairs; verify real Play,
   Pause, seek, local movies, compatible-copy preparation and cancellation,
   visualizer output, and broadcast stop/start. Source regressions pass.
7. [ ] Verify Webbie, Forage, Deep Forage, Kali Bay, Guardian, Vault and AI DJ from
   the new desktop. Preserve previously installed models, memory and timers.
   Voice enrollment and new AI DJ repair installation remain unconfirmed.
8. [ ] Create Spider's own lock-screen theme using the existing secure session
   locker; test lock, authentication, failure feedback and unlock. Do not replace
   authentication with a custom password dialog.
9. [ ] Finish Spider boot and desktop-loading splash screens. A Plymouth boot
   theme already exists in `distro/config/plymouth`; installed activation is
   unconfirmed. The new desktop session needs its own loading splash.
10. [ ] Connect unconfirmed newer workspace wallpapers, finish visual consistency,
    then test the packaged desktop login, lock/unlock, app launching, workspace
    persistence, movie playback and splash transitions.

### Proposed application placement

| Workspace | Ubuntu Studio applications belong here |
| --- | --- |
| Studio | DAWs, instruments, effects, audio routing, recording, video editors and production tools |
| Media | Music/video players and media viewing |
| Author & Office | Writing, documents and office applications |
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

The seven-workspace wallpaper pack was prepared previously; its newer wallpaper
connections have no installation confirmation. Do not replace the confirmed
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
