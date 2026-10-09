# Spider OS master upgrade checklist
**Grouped and reprioritized October 9, 2026.** Based on the attached reconciled checklist, owner-confirmed installation output and the current GitHub source work.

**Legend:** `[x]` completes only the named source work or installation. It does not automatically establish installed-PC acceptance. `[ ]` remains outstanding. Preserve the working encrypted boot chain, Plasma fallback, owner modifications, private manuscripts and service settings.

**Installation plan:** build the related desktop changes together, publish one combined branch, install once, then log out/in once. Boot branding, voice-agent replacement and Kali package changes require separate qualification and are not silently included.

## Confirmed accomplishments and source builds

- [x] Installed native Spider OS boots; owner recovered it after Oct 9 power outage. Cause of failed boot and health of disk still unknown.
- [x] Installed The Web (X11) desktop; latest confirmed installer ran Oct 8, 21:15 and created `/usr/local/lib/spider-os/upgrade-backups/the-web-20261008-211515`.
- [x] Installed The Web's fixed Firefox window visibility code and local workspace folder shortcuts as part of latest confirmed build; real browser/focus testing still needed.
- [x] Built 15-tab desktop with seven original native Qt workspace embeds (Media becomes the eighth in the new source build), a Start menu, taskbar, wallpaper picker and restored sessions; user-PC detailed QA not complete.
- [x] Packaged and installed the 59-file alternate wallpaper collection; existing original wallpapers are preserved. On-screen placement audit remains.
- [x] Applied Spider lock-screen artwork with KDE secure locker intact; actual lock/unlock needs testing.
- [x] Preserved customized Studio tabs and reconciled Author launcher/import compatibility during last desktop installer; content workflows still need testing.
- [x] Kali Bay-only PR #13 installer applied twice (Oct 8 at ~21:06 and 21:07), taking backups `/usr/local/lib/spider-os/upgrade-backups/kali-bay-20261008-210609` and `...210722`.
- [x] Existing Kali Distrobox container preserved; latest `kali-bay status` returned `container`, and `doctor` reported `exited`. This does **not** establish full Kali toolset readiness.
- [x] Installed Spider Media Center repaired `app.asar` on Oct 8 at 20:07, saving `app.asar.before-playback-20261008-200747-1055870`. GUI playback remains unverified.
- [x] Developed source-level Author library, chapter snapshots/import, School dashboard/APA export, Studio installed-tool discovery, Webbie action gateway, Forage indexing, Guardian/Vault tools and AI DJ HTTP reliability. Not all have user-PC feature acceptance.
- [x] Built System and Recovery nonblocking diagnostics in PR #16; all source checks passed. **Not yet installed on owner's PC.**
- [x] Prepared private `Spider-Author-Private-Content-Import.zip`; owner extracted it. Actual SQLite import and retention of the original DOCX files remain unconfirmed.
- [x] PR #17 source-built Webbie's ethereal violet woman portrait, speech-gated lip animation, responsive typed chat and safe window Close controls. Not yet confirmed installed; lip motion is approximate, not phoneme-synchronized.

## 1. Boot, disk and irreplaceable data — urgent

- [ ] Collect a read-only post-outage boot/SMART/journal and drive-health inventory; document the exact cause if detectable. Do not run destructive filesystem repair blindly.
- [ ] Confirm encryption unlock, SpiderRoot EFI/GRUB, actual running Ubuntu base/kernel, and clean reboot, without editing the working boot chain before backup.
- [ ] Verify *existing* Author DB, extracted Broken World manuscripts, Studio projects, school work, Webbie models/memory, and Media Center settings survived the outage.
- [ ] Make versioned local backups of the boot configuration and irreplaceable projects. Test restoring one harmless sample file from the backup.
- [ ] Enable/qualify Spider Guardian health/backup UI; verify failures are visible rather than silently ignored.
- [ ] Consider UPS battery-backup support/clean shutdown alerts for another outage (optional hardware improvement, separate from boot repair).

## 2. The Web desktop — essential OS controls

- [ ] Install the newer PR #16 source-tested System and Recovery inspection panels and asynchronous service health polling with backup; do not overwrite Kali Bay's separately upgraded UI or Webbie custom code.
- [x] Source-built installed build/version/commit receipts and managed-file integrity checks in the combined batch.
- [ ] Verify that receipt on the installed PC after the single batch installation.
- [ ] Test Firefox, app window focus, Start/search menu, tab switching, taskbar, workspace folder links, native modules, desktop return, secure lock/unlock and normal logout.
- [x] Source-built visible Close buttons, right-click Minimize/Maximize/Restore/Close, and overflow window actions. Normal closing retains app save prompts.
- [ ] Verify actual KWin minimize/restore/close and unsaved-document prompts on the owner PC.
- [ ] Add resilient window positioning, notification tray/notifications, sensible multi-monitor support and optional keyboard shortcuts.
- [ ] Confirm original wallpapers remain unchanged; audit 59 alternates, today's Forage/Deep Forage/Webbie/Communications choices and workspace-specific persistence.
- [x] Source-built asynchronous service status, health findings with next steps, build integrity display and JSON report export.
- [ ] Check the health findings against the installed services and devices.
- [ ] Validate separate Author, Studio, School, Kali Bay and Media navigation without spawning duplicate sessions.
- [x] Existing The Web interface uses a purple dark palette.
- [ ] Finish a persistent dark/light appearance setting for The Web, Qt/KDE apps, GTK apps, file dialogs and menus; qualify contrast/readability rather than claiming a global dark mode from shell colors alone.
- [x] Source-built a taskbar Audio entry, output volume +/- and mute/unmute, percentage/mute display and bounded WirePlumber calls. Volume increases are capped at 100%.
- [ ] Verify actual speaker/headphone volume and mute on the owner PC; add a slider, output/input device switching, microphone mute, app mixer and reliable media/volume keys.
- [ ] Add a notification service, visible popups, notification history, dismiss/clear and Do Not Disturb. The current session stops plasmashell; do not assume Plasma's notification UI still exists.
- [ ] Add a native system tray/status-notifier host with running/background app icons and their menus; preserve compatibility with existing apps.
- [ ] Add normal quick settings for Wi-Fi/Ethernet, Bluetooth, battery/power, brightness, night light, displays and safely ejectable drives.
- [ ] Add clear suspend/restart/shutdown controls through the existing session/Polkit infrastructure, with unsaved-work checks.
- [x] Source-built Ctrl+W for safe workspace-tab closing and a taskbar shortcut to Webbie.
- [ ] Add reliable global shortcuts and an app/window overview, with responsive taskbar layout on smaller and multiple monitors.

## 3. Webbie — voice reliability, permissions and speaking face

- [ ] Repair/verify wake phrase through continuous hands-free multi-turn conversation, explicit end phrase, timeout, interruption handling, TTS playback/mic recovery and self-speech echo rejection.
- [ ] Enforce **only Cory and Shayna** as authorized voice users by default. Ignore TV/movie voices, strangers and Webbie's own speech unless deliberately added by owner.
- [x] Source-built an ethereal violet woman face and a stationary portrait with blended mouth movement during the real speaking marker.
- [x] Source-built a reply/speech halo and asynchronous typed chat with escaped transcripts, error recovery and safe busy closure.
- [ ] Add accurate audio/phoneme timing for real lip-sync, plus trustworthy listening/thinking/speaking expressions. Approximate lip movement does not complete this item.
- [ ] Verify portrait animation against the existing installed voice agent, including quiet gaps and speech completion.
- [ ] Add visible microphone state, text transcripts/permissions, mute/stop, action confirmations and a face window integrated into The Web.
- [ ] Connect permissions-scoped actions to actual Author, Studio, School, research, Media Center and system tasks with explicit approval for risky changes.
- [ ] Verify Qwen/Ollama local models, model selection/fallback and offline Australian English voice. Optional online models require explicit opt-in/privacy boundaries.
- [ ] Add secure per-user long-term context/Personal Knowledge Web; synchronize selected context to owner-approved storage, never silently publish private manuscripts.
- [ ] Provide morning NA/AA meeting lookup and contextual reminders, only after reliable source/location handling. Keep user-defined voice preferences.
- [ ] Add dedicated Webbie DJ persona while preserving normal assistant behavior and preventing media audio from triggering commands.

## 4. Author — private manuscripts, library and canon

- [x] Prepared a private import with 20 editable library entries, Broken City front matter + chapters 1–16, and 23 original DOCX documents; ZIP extracted on owner PC.
- [ ] Confirm private Author import into its real SQLite library, without running two concurrent editors. Verify chapter count, companion materials, canon bible/evidence ledger and that existing entries aren't overwritten.
- [ ] Preserve original formatted DOCX manuscripts under an Author originals directory, non-destructively, and confirm a real independent backup.
- [ ] Verify autosave, snapshots, chapter version history, import/export, offline persistence, safe closure and recovery after abrupt restart.
- [ ] Finish manuscript library, novel/companion navigation, character/timeline/lore/reveal-ledger tools, and Broken World canon/continuity checking requiring user approval before edits.
- [ ] Add read-aloud with stop/resume and configurable narration voice, chapter comparison, searchable notes and cross-book references.
- [ ] Establish a future author website/mobile access or separate Author app only after reliable local storage/sync is ready.

## 5. Media Center and AI DJ — playback and broadcast

- [x] Install repaired packaged Media Center archive and preserve rollback archive.
- [ ] Verify playback Play/Pause/seek, a real local movie, track switching, cancellation of compatibility copies, original file integrity and visualizer output.
- [ ] Verify broadcast/radio actually starts and stops (rather than displaying a false On Air state), AI DJ local service health on 127.0.0.1:9876 and audible transitions.
- [ ] Finish timing, voice volume, ducking, crossfade, DJ break scheduling and spoken transitions; support Webbie controls.
- [x] Source-built a native Media tab with selected-player Play/Pause, Stop, Previous/Next and +/-10-second seek using MPRIS.
- [ ] Verify available MPRIS players on the owner PC and add global media-key integration.
- [ ] Expose Spider Media Center itself through MPRIS if its installed Electron build does not already provide it; the shell client alone does not make an unsupported player compatible.
- [ ] Integrate libVLC or another compatible native decoding engine into **Spider Media Center**, rather than simply opening an external VLC window; finish subtitles and audio-track selection.
- [ ] Add legal live TV/IPTV M3U support, network libraries, device discovery, casting, photos, radio/talk stations, and Broken City Network broadcast identity.
- [ ] Continue reactive GPU/3D visualizer and DJ-on-a-USB portable service. Respect station rebroadcast rights.

## 6. System, Recovery, Guardian and Vault — health and backups

- [x] Source-built native System/Recovery service, storage, audio and backup-list panels with background refresh.
- [x] Source-built install receipts with version/time/source commit, bounded integrity validation, actionable health findings and exportable JSON diagnostics.
- [x] Source-built output volume/mute controls; actual devices and audio remain to be checked.
- [ ] Install the combined batch once, then verify System/Recovery against real services, disk space, audio and backup copies.
- [ ] Add privacy-conscious service error summaries and device inventory without publishing secrets or manuscripts.
- [ ] Finish a reviewed rollback flow, verify backup compatibility and restore a harmless sample before claiming recovery works.
- [ ] Activate/verify Guardian, Vault and opt-in encrypted OneDrive backups with non-destructive failures and a tested local restore.
- [ ] Verify USB/offline memory fallback and backup/sync conflicts; keep the internal fallback when removable storage is missing.

## 7. Kali Bay and Purple Defense — isolated tools

- [x] Install selective Kali Bay UI/manager upgrade from GitHub PR #13 with original backups.
- [ ] Safely start the existing Kali container only after checking disk health; run non-mutating diagnostics, verify repaired `systemd`/`udev` package state and installed metapackages. Do **not** rerun `kali-linux-everything` blindly.
- [ ] Open Offensive Security and Purple Defense tabs and test permitted GUI launchers (Wireshark, Burp, ZAP, Ghidra, ClamTK) in authorized/local test contexts.
- [ ] Finish Kali Purple defensive tools and SOC workflow integrations if missing; honor rootless container limits and avoid claiming a Distrobox is an independent security VM.
- [ ] Add backup of Kali container configuration and reproducible restore/checks without affecting Spider host packages.

## 8. Studio — recording, songwriting and production

- [x] Source-built Studio tools tabs and application discovery; owner's custom Studio layout preserved.
- [ ] Verify all installed production apps launch from Studio; repair launchers still falling through to Dolphin.
- [ ] Finish audio/video project folders, templates, track sessions, PipeWire/JACK routing, external recording device monitoring and Media Center handoff.
- [ ] Add Broken Sorrow song/lyric drafts, session notes, music exports and album-art workflows non-destructively; do not infer that unprovided master audio files exist.

## 9. Study — SNHU, assignments and APA

- [x] Source-built School dashboard, SNHU links and APA student papers.
- [ ] Verify PSY-328 and SOC-112 coursework, real assignment folder mapping, due dates, citation export and APA formatting. Connect optional weekly course assistance and reminders.
- [ ] Verify Forage and Deep Forage selected-source research/indexing from native tabs; searchable history, sources/citations and research export to Author/School.

## 10. Forage and Deep Forage — search and research

- [ ] Verify Forage and Deep Forage selected-source research/indexing from native tabs; searchable history, sources/citations and research export to Author/School.
- [ ] Keep Forage quick search and Deep Forage queued/in-depth research distinct, with source/date context and clear cancellation.
- [ ] Provide inspectable research queues/history, source exports and approval before modifying Author or Study documents.

## 11. Art Lab, Communications and other workspaces

- [ ] Add Art Lab graphics/3D design production and Communications apps/inbox if the needed tools are available and explicitly connected.
- [ ] Check Recovery, System, Dev Bay, Games and Media workspaces have real useful content and no dead-end buttons.

## 12. Startup branding — GRUB, splash and login

- [ ] Inventory what actually displays Ubuntu Studio: firmware handoff, GRUB title/background, Plymouth splash, SDDM login theme, desktop loading splash, OS labels and application branding.
- [ ] Complete Spider logo/purple visual identity on GRUB, Plymouth and SDDM with recovery/Plasma sessions retained. The source has Spider Plymouth artwork, but active installed boot theme is unverified.
- [ ] Keep underlying Ubuntu/KDE packages and working encryption/boot loader. A visual rebrand does **not** require deleting Ubuntu Studio system components.
- [ ] Only after reliable backup, test Spider startup branding over multiple cold boots and one recovery boot; restore defaults if a screen fails.
- [ ] Later: choose whether to use branded release metadata beyond splash screens after compatibility checks; avoid lying about the underlying distribution to package managers.

## 13. Platform — integrations, remote access and permissions

- [ ] Add authenticated Google account integration where useful, after permission review.
- [ ] Revisit original Spider Store idea: user-scoped Flatpak discovery and explicit installs/removals only. Do not blindly bring Fedora bootc/RPM code into an Ubuntu machine.
- [ ] Add Polkit-gated, allowlisted privileged system actions for update/reboot/rollback; Webbie never receives arbitrary root shell access.
- [ ] Finish Device Web/Control Center, network shares, attached media, local machine status and optional remote Spider OS access, including the **three remote instances** requested.
- [ ] Add first-run setup wizard, model/storage/privacy controls, graceful service recovery and integrated status/health report.

## 14. Installer and release engineering — after PC stability

- [ ] Consolidate the authoritative source tree and review stacked open PRs; desktop work is stacked across PR #11, PR #16 and PR #17; Kali work is separate. Source validation is not installation.
- [ ] Keep old `justinhobsonstudios-byte/Spider-OS` Fedora/Aurora bootc code as an architectural reference, **not** a drop-in update to the working Ubuntu install. Its PR #19 proposes a different Ubuntu-based 1.0 foundation that has not passed full installer qualification.
- [ ] Pin GitHub Actions build runners/toolchains explicitly; test Ubuntu 26.04 compatibility intentionally rather than silently changing `ubuntu-latest`.
- [ ] Reconcile current installed Ubuntu release against ISO build scripts still pinned to an Ubuntu Studio 24.04.5 image; decide future native release/upgrade path with a tested migration plan.
- [ ] Test live ISO boot, BIOS/UEFI/SpiderRoot, encrypted writable installation, first login, full-feature ISO and safe recovery in a VM/QEMU before shipping a new native ISO.
- [ ] Add release receipts, reproducible builds, CodeQL/security scans, rollback-tested updates and GitHub PR promotion after actual machine acceptance.

## 15. One coordinated installation and acceptance pass

- [ ] Finish the source batch before asking the owner to reinstall or log out again.
- [ ] Run one combined installer and retain the new backup/build receipt.
- [ ] Log out/in once to load the complete desktop batch; ordinary source work does not require repeatedly changing sessions.
- [ ] Reboot and verify Spider startup, disk encryption, correct session chooser and recovery Plasma session.
- [ ] Test The Web with Firefox, windows/taskbar, each workspace, art/wallpapers, locked/unlocked state, standby/resume and logout.
- [ ] Test Webbie wake/voice authorization and facial lip-sync when delivered, offline assistant, native actions, research, school and manuscripts.
- [ ] Test Author database content/import/history/exports and file restore, Studio recording/app tools, Media playback/radio/DJ, Kali Bay/Purple and Guardian/Vault backups.
- [ ] Retain current backups until tests and a sample rollback both pass, then mark each subsystem **verified on installed PC** separately.

## Key GitHub references

- Current desktop: https://github.com/brokenandalone/spider-narive-os/pull/11
- Desktop source-tested System/Recovery improvements: https://github.com/brokenandalone/spider-narive-os/pull/16
- Kali-only installer and Purple Defense: https://github.com/brokenandalone/spider-narive-os/pull/13
- Firefox fix: https://github.com/brokenandalone/spider-narive-os/pull/14
- Workspace folder links: https://github.com/brokenandalone/spider-narive-os/pull/15
- Author: https://github.com/brokenandalone/spider-narive-os/pull/7
- School: https://github.com/brokenandalone/spider-narive-os/pull/8
- Spider Media Center repaired playback: https://github.com/brokenandalone/Spider-Media-Center/pull/2
- BCN/live media/portable DJ proposals: https://github.com/brokenandalone/Spider-Media-Center/pull/1
- Historical Spider OS architecture/reset: https://github.com/justinhobsonstudios-byte/Spider-OS/pull/19
- Historical Spider Store proposal: https://github.com/justinhobsonstudios-byte/Spider-OS/pull/11
- Historical safe Polkit actions: https://github.com/justinhobsonstudios-byte/Spider-OS/pull/9
- Combined desktop/Webbie batch: https://github.com/brokenandalone/spider-narive-os/pull/17
