# Spider OS master upgrade checklist
**Grouped and reprioritized October 9, 2026.** Based on the attached reconciled checklist, owner-confirmed installation output and the current GitHub source work.

**Legend:** `[x]` completes only the named source work or installation. It does not automatically establish installed-PC acceptance. `[ ]` remains outstanding. Preserve the working encrypted boot chain, Plasma fallback, owner modifications, private manuscripts and service settings.

**Installation plan:** build the related desktop changes together, publish one combined branch, install once, then log out/in once. Boot branding, voice-agent replacement and Kali package changes require separate qualification and are not silently included.

## Unified cross-chat status and release gate (2026-10-09)

**Authority:** this checklist + [cross-chat handoff](CROSS-CHAT-CONSOLIDATION-2026-10-09.md) + [installation policy](INSTALL-RELEASE-POLICY.md), updated from the accessible Spider OS conversations, GitHub branch history and installed-PC audit. Chat-history retrieval outside the conversation was unavailable; do not claim every chat message has been independently verified. GitHub code and individual PR green checks are *not* proof of a combined or installed build.

- [x] Owner requests **one bundled installation per request**, not one installation per day, with one preflight, one backup manifest, one activation and rollback. Continue GitHub builds between requests. No unsolicited Dell installation.
- [x] Confirmed in Konsole: `XDG_SESSION_TYPE=x11`, `DESKTOP_SESSION=the-web`. X11 is the supported floating-face target; full-screen/click-through still require real-device verification.
- [x] Installed-PC audit: native desktop boots after outage; Webbie/Ollama/AI DJ/PipeWire/WirePlumber active; Kali container preserved but exited; Author DB 20 books/39 chapters/20 imported fingerprints; School DB 1 course/0 assignments; System/Recovery dashboards and basic media controls owner-confirmed. **No independent backup/boot integrity/feature completeness implied.**
- [x] Owner's Webbie naming: **Spider** in Kali Bay, **Justin** in Studio, **Student** in School/Study, **Writer** in Author, **Cory** everywhere else; custom overrides must survive.
- [x] Owner's quiet-sleep behavior: she stays visible with dimmed closed eyes and `Zzz`, ignores ordinary speech until deliberate wake, keeps listening hardware active only as needed for wake recognition and **keeps existing background jobs running**. No timed auto-wake. Face hides only during fullscreen video.
- [x] Owner's OneDrive decision: **Connect OneDrive** appears on demand; Microsoft OAuth and remote sync remain deferred until owner signs in; no login prompt or network dependency blocks Webbie. Only explicitly placed Webbie share-folder files may sync; no private manuscripts/history by default.
- [x] Other chat's latest **PR #23** at `83d692b4` passed source CI (Author Story Bible/search/read aloud/focus/review/export, opt-in camera/watch-room, optional consenting Cory/Shayna face cues, rollback/readiness script). This is **a tested sub-batch**, not the unified deliverable or installed verification.
- [x] PR #25 source-tested shared quiet sleep; PR #21 source-tested click-through face/OneDrive; PR #22 source-tested context/model preference; PR #24 source-tested local one-frame vision. **Their combinations have NOT been fully qualified.**
- [x] **Source-integrated one floating X11 portrait** guarded by a per-user process lock, shared persistent sleep state, voice/GUI sleep controls, and fullscreen hiding. Legacy embedded overlay remains as historical test code, not an independently spawned second portrait. **Owner-PC click-through, fullscreen and absence of duplicate autostart still need testing.**
- [x] **Source-integrated Author/camera panel and resident Webbie agent** with bay names, on-demand OneDrive, quiet sleep, and owner-enabled webcam queries; 161+ combined tests and Qt smoke checks passed in PR #26. **Voice/microphone and vision permission behavior on Dell remains unverified**; face identification does not authorize speakers.
- [x] **Source-built** `system/release_batch.py` as the single owner-requested release entry point, with read-only preflight, recognized-baseline checks, one versioned backup/manifest, atomic file staging, rollback validation, and explicit user autostart/OneDrive launchers. Source regression tests cover custom-file blocking, install and restore, symlink protection and flags. **Host compatibility and release promotion pending.**
- [x] Strengthened unified batch rollback for simulated mid-copy failures and exceptions after file replacement; both regression tests and combined CI passed on `ebd3618e3a816cf74320c019ae84d058f17c7cea` (Actions run `37949871319`). No user files touched.
- [x] Realistic **disposable** batch fixture passed: Author, desktop, Webbie agent, portrait and OneDrive modules installed together and rolled back together, including preservation of sample Author SQLite and original DOCX bytes. Source CI run `37950457129` passed at `6a4b660665ff1be92e4e1b59189500aba191ff71`.
- [ ] Reconcile the actual customized Dell file hashes, validate independent restorable Author backups and test release readiness on the real machine. Unknown local files remain protected; **no on-PC install yet**.
- [x] Draft [PR #26](https://github.com/brokenandalone/spider-narive-os/pull/26) integrates Author, camera, one X11 Webbie portrait, consented local vision, workspace names, quiet voice gate and deferred OneDrive. A previous combined Actions run passed after fixing UI regressions; GitHub's newest revision must be checked separately.
- [x] PR #26 combined CI **passed on source commit `5cbd4a9a8941e2e714acc17ae62d3a35d8c51db2`** (GitHub Actions run `37947832794`): 161+ source/Qt/Author/camera and release transaction tests, source install preflight, rollback syntax, and desktop smoke testing. **Source-only**; no installed-PC acceptance implied.
- [ ] Verify the **final frozen release SHA** after later changes before any owner-requested installation, and reconcile local Dell file hashes first. Unknown user customizations remain hard blockers.
- [x] Source-built `system/release_readiness.py`, a read-only PC readiness audit covering X11/The Web session, installed Webbie and shell hashes, optional camera device nodes, available ffmpeg/xprop/rclone/Ollama, user service state, space and document counts, without activating camera, logging into OneDrive or changing services. Disposable regression tests and integrated CI passed (run `37952375915`).
- [ ] Owner-PC preflight: establish independent, restorable Author and original DOCX backups, verify customized Webbie agent hashes, check `ffmpeg`, webcam, local vision-capable Ollama, X11, optional `rclone`, user-systemd access and free disk; stop on blockers.
- [ ] Owner-PC acceptance after explicitly requested bundled install: no regression in voice/TTS/AI DJ or startup; tabs, desktop windows, Webbie click-through/fullscreen/night mode, opt-in camera and OneDrive deferred login, Author manuscripts and exports, Kali and Media Center.
- [ ] Separate later work: authenticated speaker authorization (Cory and Shayna only), screen-sharing with visible control, taskbar tray/notifications/quick settings, global dark mode, Media Center radio/TV/visualizer/casting, Forage research, Kali tool qualification, startup GRUB/Plymouth branding and installer/ISO boot QA.

### Latest desktop usability source work (not yet on Dell)

- [x] Webbie's combined X11 face and panel now use one quiet-sleep state. Spawning a second embedded portrait was removed from The Web's startup. A per-user overlay lock avoids duplicate independent floating windows. On-PC visual and wake-word acceptance remains open.
- [x] Fixed notification **Clear history** for both local The Web notices and the third-party JSON-line journal, retained Do Not Disturb, rejected journal symlinks, tolerated corrupt external entries and rendered untrusted messages as plain text.
- [x] Added unique local event IDs so identical notifications arriving within a second each produce a popup; tests cover duplicate delivery and untrusted text.
- [x] Fixed existing output volume widget's synchronous refresh: speaker-volume status and writes now run through a QThread so WirePlumber hangs cannot block the Qt desktop for up to two seconds. The unavailable-device state keeps controls disabled; regression tests cover Qt responsiveness. **Not yet verified on the Dell.**
- [x] Source-built a nonblocking **Quick Settings** taskbar entry with read-only NetworkManager network/Wi-Fi, Bluetooth controller, system battery/AC, brightness and **default microphone muted/available state**, plus an explicit launch of standard KDE System Settings. No automatic radio/power/display/microphone changes or privileged shell access.
- [x] Latest integrated **source CI passed** on commit `22b371c8df29549736d99e9b628a316d5aff1f24` (GitHub Actions run `37979724496`), including notification clear/duplicate/plain-text safety, Qt Quick Settings and default microphone status, off-thread volume refresh, release readiness and existing Author/Webbie/camera tests.
- [ ] Verify those capabilities on the Dell: optional `dbus-next`, NetworkManager/brightness tool detection, real app notifications, audio responsiveness and Webbie mic status. Build full device toggles only with permission checks and no connectivity surprises.
- [ ] Qualify hardware media keys, input/output audio selection, native notification actions and tray menus, USB/eject, power/suspend and multi-monitor support; present them as future items, not completed controls.

### Window-management source build (installed-PC acceptance pending)

- [x] Built `the-web/shell/window_overview.py` and wired **Start → Windows** to a searchable nonblocking X11 window list. Activate, Minimize, Maximize/Restore and Close are available without terminal commands; close uses normal window-manager requests so applications can present save prompts.
- [x] Added regression coverage for window-search filtering, invalid window IDs, safe normal Close and non-destructive handling of failed Minimize. Included the module in the one guarded release manifest. **Combined CI passed** for commit `77985774bba2880abbf99d029d06cf8e997eb0ae`, GitHub Actions run `37981353715`. Owner-PC verification remains pending.
- [ ] Verify real-window listing, window activation/restore/minimize and unsaved-document prompts on the Dell. Consider a global shortcut/overview later with KWin session-specific permissions; don't claim the Qt shortcut is globally effective across unrelated apps.

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
- [x] Prepared/extracted private `Spider-Author-Private-Content-Import.zip`. Oct 9 owner-PC audit confirmed Author SQLite readable with **20 books, 39 chapters and 20 imported source fingerprints**; remaining check is chapter/content verification and preservation of original DOCX files.
- [x] PR #17 source-built Webbie's ethereal violet woman portrait, speech-gated lip animation, responsive typed chat and safe window Close controls. Not yet confirmed installed; lip motion is approximate, not phoneme-synchronized.

- [x] User confirmed all personal files remained present after the power outage. This is not a validated independent backup or a storage-health report.
- [x] Source-built a read-only, privacy-limited installed-system audit for Author/Study record counts, Spider startup-branding hints, Kali state, desktop/Media files and user services (PR #18, merged into combined PR #17). **Run on the owner PC October 9 with reported inventory; newer revisions remain source-only.**
- [x] The combined PR #17 source batch includes Webbie face/chat, window Close/Minimize/Maximize, audio/mute, Media MPRIS client, System/Recovery health panels and build receipts. Not installed on the owner PC; install in one selective batch with backup after source qualification.
- [x] Owner's post-audit response on Oct 9 confirmed **System/Recovery dashboards (#5) and media playback controls (#4) working** in the currently used Plasma desktop. This is user-observed UI functionality, not proof of full streaming, recovery or backup testing.
- [x] Oct 9 post-outage inventory: Webbie/Ollama/AI DJ/PipeWire/WirePlumber **active**; Kali Bay container **exited**, not missing; Author DB readable with 20 books, 39 chapters, 20 fingerprints; school DB 1 course, 0 assignments.
- [x] PR #21 source-built floating click-through Webbie face, fullscreen auto-hide, explicit night sleep and optional sign-in OneDrive folder sync. Dedicated add-on installer exists; PC installation, mouse-pass-through, fullscreen, OAuth and cloud transfer all **still unchecked**.

## New: floating Webbie and deferred OneDrive sign-in

- [x] Source-built a separate, translucent **click-through** Webbie face in the lower-left of Plasma X11 and The Web X11, with KWin fullscreen hide, speaking-marker mouth animation, visible quiet-sleep overlay on the later PR #25 branch (the original PR #21 build hid until 8 AM), and user autostart. **Installed-PC verification pending.**
- [x] Source-built optional Microsoft OneDrive connection via explicit user-invoked rclone OAuth, with Webbie local operation independent from all cloud tasks and a separate timed background folder sync. **Owner sign-in, cloud transfer and feature verification pending.**
- [ ] Verify visible click-through on buttons, actual fullscreen video hiding, night sleep and voice continuity on the owner PC; support Plasma Wayland only after compositor-specific qualification.
- [ ] Verify user-selected OneDrive remote/authentication and a harmless selected-folder upload. Do not auto-upload private Webbie history, memory, manuscripts or other user files.
- [ ] Decide whether to offer secure memory sync or full OneDrive search only after explicit user permission and encryption design; selected-folder sync is not yet Webbie cloud memory.

## 1. Boot, disk and irreplaceable data — urgent

- [ ] Collect a read-only post-outage boot/SMART/journal and drive-health inventory; document the exact cause if detectable. Do not run destructive filesystem repair blindly.
- [ ] Confirm encryption unlock, actual firmware mode (Legacy BIOS vs UEFI), GRUB/SpiderRoot configuration, running Ubuntu base/kernel, and clean reboot; Oct 9 inventory found grub.cfg present and SpiderRoot EFI path absent, which **does not prove a fault**, especially under Legacy BIOS. Make no boot changes before backup.
- [x] Owner confirmed files remain after outage; read-only Oct 9 inventory found Author DB, extracted bundle, Studio project directory, Study DB (1 course, 0 assignments), Webbie agent, Media Center archive, and active Webbie/Ollama/AI DJ/PipeWire/WirePlumber services.
- [ ] Verify individual Author chapter contents, Studio and school project files, Webbie models/memory and Media Center settings before marking all personal-data recovery fully checked.
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
- [x] **Source-built persistent The Web dark/light appearance** in `the-web/shell/appearance.py` and Quick Settings. Dark violet remains default. Changing mode updates The Web chrome, Start menu, taskbar and an in-memory tint over the existing wallpaper; private settings are atomically stored at `~/.config/spider-os/appearance.json` (or XDG config home). Tests verify opt-in switching, remembered setting on desktop relaunch, malformed/symlink safety and unchanged source artwork. GitHub Actions run `37980996989` passed on commit `3081a4f6edb31f71643c7bdbd236371de2503af3`. **Not installed.**
- [x] **Source-built read-only KDE/GTK appearance compatibility inventory** (`the-web/shell/gtk_compat.py`) in Quick Settings: inspect GTK 3 `settings.ini`, GTK 4 `settings.ini`, and KDE `kdeglobals` color-scheme name; handle missing/malformed or symlinked user config. Make no privileged calls, edits or GTK 4/libadwaita promises. Source CI **passed** at `00e833c7cf3347fdb33d3a87ba3f7c814ba6b4a6`, Actions run `37984301003`. No Dell deployment.
- [x] **Source-built a no-write KDE/GTK theme-sync preview** (`the-web/shell/theme_sync_plan.py` and Quick Settings): inspect installed `BreezeDark.colors`/`BreezeLight.colors`, presence of Plasma's color-scheme tool and potential `GTK_THEME` override; display existing KDE and GTK preferences and clearly mark blockers, without changing KDE/GTK configuration, session variables or private theme assets. Includes preview-only UI and regression tests. **Combined CI and owner-PC behavior must be verified.**
- [x] **Source-built live app color-preference diagnostics** in Quick Settings: query the desktop Settings portal on the background worker, support current ReadOne and legacy Read replies, show dark/light/no preference/unavailable, and explain mismatches in the existing appearance preview. No appearance settings are written. Tightened desktop-name matching and rejected relative XDG theme roots. Nineteen focused GTK/theme/Quick Settings tests passed locally; full CI and Dell acceptance remain required.
- [ ] **Global KDE/GTK and application dialog dark/light mode remains separate**: implement an owner-approved, backed-up Plasma color-scheme change using the installed native tool; preserve current color scheme/custom themes and confirm the KDE GTK integration's actual Breeze synchronization, then assess GTK 4/libadwaita color-scheme portal, file dialogs and login/session appearance. Do not force `GTK_THEME` or claim GTK 3 settings control libadwaita.
- [ ] **Owner-PC theme readiness and rollback**: inspect actual KDE/GTK color schemes, `xdg-desktop-portal-kde`, `kde-gtk-config` and app-specific overrides; capture independent user preference backups before any write; test full revert and dark/light accessibility on the installed Dell.
- [ ] Verify The Web light and dark themes, Webbie side panel readability, Start/menu/taskbar contrast and unchanged preferred wallpaper files on the installed Dell.
- [x] Source-built a taskbar Audio entry, output volume +/- and mute/unmute, percentage/mute display and bounded WirePlumber calls. Volume increases are capped at 100%.
- [x] **Source-built a taskbar Volume quick panel** with a 0–100% bounded output slider, mute toggle, nonblocking worker and explicit unavailable-audio messaging. Added to the unified installation manifest and tested in PR #26 GitHub Actions run `37953819308`. No Dell deployment or hardware acceptance yet.
- [ ] Verify actual speaker/headphone volume and mute on the owner PC; add a slider, output/input device switching, microphone mute, app mixer and reliable media/volume keys.
- [x] Built native **Alerts** button on the existing open-window taskbar (NOT a separate Tray tab), with private local The Web notification history, Clear History and Do Not Disturb. Included in the single release manifest. **Third-party application notifications, popup toasts and StatusNotifier tray hosting remain unimplemented and must not be claimed complete.**
- [ ] Add a notification service, visible popups, notification history, dismiss/clear and Do Not Disturb. The current session stops plasmashell; do not assume Plasma's notification UI still exists.
- [x] Source-built optional **freedesktop notification DBus receiver** for external applications, limited private history, and the existing taskbar's **Alerts** viewer. It only claims the service when no other notification daemon owns it. Added a **Tray** taskbar control with background-app discovery/activation via an existing StatusNotifier watcher, and source tests passed in GitHub run `37960575133`. **Not yet a full icon/menu/status-notifier host** and not installed on Dell.
- [x] Source-built improved existing taskbar **Tray** panel with app-provided StatusNotifier title/status/icon-name metadata, right-click Open and Secondary Action commands, and menu availability discovery. Fixed notification bridge to use DBus `DO_NOT_QUEUE` so it cannot unexpectedly take over KDE notifications later. Combined CI run `37961566263` passed. **Real icon artwork and native app menu rendering not implemented.**
- [x] Source-built **theme-based tray icons** for registered app entries and **5.5-second notification popups** with DND, dismiss and no login-history replay, integrated into existing desktop/taskbar and unified installer. GitHub source test run `37969937772` passed. A full StatusNotifier watcher, D-Bus app menus, and real hardware-session acceptance remain pending.
- [ ] Qualify optional `dbus-next` dependency, notification popups/dismissal and an independent watcher/real per-app tray icons and menus in the X11 session; do not claim real third-party notification or tray acceptance until owner-PC tests pass.
- [ ] Add a native system tray/status-notifier host with running/background app icons and their menus; preserve compatibility with existing apps.
- [ ] Add normal quick settings for Wi-Fi/Ethernet, Bluetooth, battery/power, brightness, night light, displays and safely ejectable drives.
- [ ] Add clear suspend/restart/shutdown controls through the existing session/Polkit infrastructure, with unsaved-work checks.
- [x] Source-built Ctrl+W for safe workspace-tab closing and a taskbar shortcut to Webbie.
- [ ] Add reliable global shortcuts and an app/window overview, with responsive taskbar layout on smaller and multiple monitors.

## 3. Webbie — voice reliability, permissions and speaking face

**Next-phase priority confirmed October 9:** after the current combined upgrades and installed-feature walkthrough, focus on contextual awareness and more natural interaction, then native Studio song generation without a required Suno subscription. Full scope and acceptance gates: [Webbie next phase](WEBBIE-NEXT-PHASE.md).

- [ ] Build a permission-aware context service for active workspace/app, selected task, conversation and fresh room/screen observations, with source, expiry and uncertainty.
- [ ] Add correctable local project memory, natural follow-up/turn-taking, interruption, functional capability awareness and controlled proactive suggestions.
- [ ] Improve expressive Australian speech, accurate lip timing and state-aware facial behavior after the conversation foundation is reliable.

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

- [x] Source-built Webbie workspace naming so Author Bay calls the owner **Writer**; owner-defined names take priority. This is **not** a claim that the installed Webbie agent has been replaced.
- [x] Source-built **Student** form of address in School/Study (internal workspace ID `study`), keeping Author/Writer, Studio/Justin, Kali Bay/Spider and user-configured overrides. **Not installed on the owner PC.**
- [x] Source-built local Ollama model selection from Webbie's existing `config/default.json`, while retaining the current default and loopback Ollama URL. No model is downloaded or switched on the PC without approval.
- [ ] Install/qualify any future agent-only changes separately from the safe floating-face and OneDrive add-on. Preserve the installed voice patches and services.
- [ ] Build explicitly opt-in camera awareness of the room with visible recording/active indicator; no silent start, hidden webcam access, or unsolicited cloud upload.
- [ ] Build separately approved screen awareness with visible sharing state, limited capture, and privacy controls. Neither camera nor screen capture is currently installed as an enabled Webbie feature.
- [x] **Owner decision Oct 9:** Webbie's lower-left face must **remain visible and look asleep**, while ordinary voice input is ignored. Microphone/transcription may remain active solely for an explicit wake phrase. No background jobs or services should stop.
- [x] Source-built shared quiet-sleep state for the X11 portrait and agent: closed-eyes dimmed appearance, explicit voice sleep/wake phrases, ignore ordinary recognized speech and proactive spoken check-ins, preserve background loops. Agent and desktop installation **pending**.
- [ ] Qualify Cory/Shayna-only speaker verification for wake commands; an exact phrase from TV/strangers cannot yet be guaranteed rejected.
- [ ] Test actual sleeping face, mouse pass-through, fullscreen video, voice wake/sleep and uninterrupted scheduled background work on the installed X11 PC.

## 4. Author — private manuscripts, library and canon

### New saved-review workflow (stacked after PR #37)
- [x] Source: Completed Webbie chapter and whole-book review reports are saved inside Author's existing SQLite library, included in its normal backups.
- [x] Source: Open prior reports without calling Ollama again; label findings **OUTDATED** when reviewed chapters or canon have changed.
- [x] Source: Jump from saved report to its reviewed chapters by stable chapter ID, not by guessing text or parsing AI-generated names.
- [x] Source: Export the displayed review to a new text file without overwriting an existing file.
- [x] Added disposable-library and GUI regression tests. The manuscript stays unchanged unless the writer approves an independent edit.
- [ ] Complete source CI and integrate the new module in a single coordinated, backup-first installer.
- [ ] On-device confirmation of review history, stale labels, chapter jumps, restore and exports with actual imported Broken World chapters.
- [ ] Later: add finding-level position links, structured issue severity, manually marked resolutions and stronger multi-book canon checking.



### October 10 source additions: full manuscript review and Webbie narration

- [x] Source: on-demand full chapter and full book reviews with **quick/deep** modes, bounded local Ollama segmentation and progress/cancel controls (installation pending).
- [x] Source: chapter and full book read-aloud using Webbie's configured voice, with pause/resume/stop (installation pending).
- [x] Added focused regression tests for full-text chunk coverage, cancel behavior, no manuscript rewrites and configured Webbie voice.
- [ ] Verify CI and merge the new stacked Author PR in dependency order.
- [ ] Live-test Author reviews on imported test manuscript, performance, voice playback and mic/TTS contention.
- [ ] Connect natural spoken commands to Author using the **reconciled live PC** Webbie agent, without breaking its working customizations.
- [ ] Enhance review history, canon consistency across books, and jump-to-finding navigation.



- [x] Prepared a private import with 20 editable library entries, Broken City front matter + chapters 1–16, and 23 original DOCX documents; ZIP extracted on owner PC.
- [x] **Author Bay library import complete and owner-confirmed:** content is imported, opens in Author Bay, and Oct 9 database audit found 20 books, 39 chapters and 20 imported fingerprints. **Never repeat import, recreate library, or overwrite current chapters.** Backup verification and original DOCX preservation remain separate tasks.
- [ ] Open a representative book, confirm all expected content including companion materials and canon, and test safe edits/version history without overwriting existing chapters.
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

- [ ] **Next-phase owner priority:** integrate local lyrics-to-song and instrumental generation into native Studio, controlled by Webbie, to remove the need for a Suno subscription. Evaluate official ACE-Step/YuE-family backends against actual GPU/VRAM/RAM, licenses and listening tests before selection; no promise of quality parity or free hardware/cloud compute.
- [ ] Add Broken Sorrow sound preset, generation queue/cancel, previews, saved takes and WAV export; qualify section editing, extensions, stems and DAW handoff as follow-ups. See [scope and acceptance](WEBBIE-NEXT-PHASE.md).

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

## Mandatory post-install walkthrough and owner training

**Owner requirement added October 9, 2026:** when the upgrades are **actually installed and accepted** on the Dell, give a complete, sequential how-to and setup/control tutorial for **every new feature**. This comes after the guarded one-batch installation and real-machine acceptance, not after source CI. See [installation policy](INSTALL-RELEASE-POLICY.md#required-post-install-owner-walkthrough).

- [ ] Create the release-specific **installed-feature inventory** from the exact manifest and real desktop acceptance results. Identify what works, what is deferred and what requires optional login or consent.
- [ ] Walk through normal desktop use first: Start, open/close/minimize/maximize windows, tabs, taskbar, notifications/tray, Quick Settings, volume/microphone, KDE/GTK appearance and accessibility, file/folder shortcuts, lock/logout, backups and rollback.
- [ ] Walk through Webbie completely: wake/sleep, voice and text, workspaces/names, animated face, permissions for room camera and any future screen sharing, optional owner/Shayna profiles, background jobs and privacy. Do **not** assert speaker or face authentication before it is truly implemented and tested.
- [ ] Walk through Author Bay, Study/School, Studio, Forage/Deep Forage, Kali Bay, Media Center/AI DJ, Recovery, System and any newly deployed tools with concrete tasks and exact verified UI labels.
- [ ] For **each** feature provide first-time setup, navigation, daily operations, customization, how to turn it off/reset, safety/privacy choices and troubleshooting or recovery. Guide owner-performed consent, passwords and OneDrive authentication only when the owner chooses them.
- [ ] Save and share a **POST-INSTALL-FEATURE-GUIDE.md** based on the final installed build, then mark each item demonstrated or deferred with the owner before considering the installation handoff complete.

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
