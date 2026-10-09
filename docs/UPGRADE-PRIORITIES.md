# Spider OS upgrade priorities — 9 October 2026

Continue the existing Ubuntu Studio installation. No new base migration, boot,
disk or encryption changes are part of these workspace upgrades. Preserve the
owner's installed Webbie, models, USB memory, timers and creative work.

## 1. Installed desktop reliability

- [x] Desktop build installed; dependency checks and lock-screen artwork setter passed.
- [x] Newer installer reconciles the known Author launcher and preserves Studio tool tabs. Owner confirmed installation at 21:15; backup `the-web-20261008-211515`.
- [x] Source fixes Firefox window visibility and connects real local project folders.
- [x] Move service polling off the GUI thread so missing/slow services cannot stall navigation.
- [x] Preflight the complete payload/checksums before installing dependencies; support Ubuntu's separately packaged X11 session.
- [x] Add visible Close buttons for external taskbar windows and Close actions in the overflow menu. Requests use normal window-manager closing so apps retain save prompts.
- [ ] Check real login, Start/taskbar including app save prompts, tab/window focus, multi-monitor behavior, lock/unlock and normal logout.
- [ ] Review power-outage boot recovery after the owner reported recovering the PC; keep boot/encryption changes separate from desktop upgrades.
- [ ] Confirm the newest folder/visibility build is installed before repeating those checks.

## 2. Webbie integration

- [ ] Verify the installed continuous conversation behavior and owner voice enrollment; only Cory and Shayna are authorized by default.
- [ ] Verify dismissal, inactivity timeout, recovery after microphone/TTS failure and ignoring TV/movies/own speech.
- [ ] Connect workspace context to Author, School, Studio, research and media commands.
- [x] Add an ethereal violet woman portrait inside the native Webbie tab.
- [x] Add speaking-gated lip movement and a reply/speech halo. The animation follows the existing speech marker; it is not phoneme synchronized.
- [x] Move typed Webbie requests off the GUI thread, escape chat markup, handle fragmented replies and recover input after errors.
- [ ] Add audio or phoneme timing for accurate lip synchronization, listening-state signals and pending-action confirmations.
- [ ] Verify the new portrait, lips, asynchronous replies and existing voice service together on the owner PC.
- [ ] Add interruption/barge-in only after the existing voice loop is stable.
- [ ] Add inspectable local model routing and research history; retain the internal fallback when USB memory is disconnected.

## 3. Media reliability

- [x] Playback repair archive installed at 20:07; original ASAR backup retained.
- [ ] Confirm Play/Pause/seek, movies, compatible-copy preparation/cancellation, visualizer and radio stop/start.
- [ ] Add Linux MPRIS transport/status integration for desktop controls and consistent media keys.
- [ ] Add subtitle selection and audio-track selection with a native media engine.
- [ ] Replace conversion-only recovery with embedded native decoding, preserving the existing compiled UI and broadcast/mixer graph.

## 4. System and Recovery visibility

- [x] Build native System/Recovery panels for services, storage, audio and available desktop/media backups.
- [ ] Check those panels against the installed services and audio devices.
- [ ] Add version/commit receipts to each installed upgrade so the desktop shows precisely which build is running.
- [ ] Add a consolidated health report and actionable service error summaries.
- [ ] Add an explicit, reviewed rollback flow; listed backups alone do not prove a successful restore.

## 5. Finish native creative workflows

- [ ] Author: verify private manuscript/companion import, autosave/history, exports and restore.
- [ ] Author: add cancellable read-aloud, chapter comparisons and canon/continuity suggestions requiring approval before edits.
- [ ] School: verify dashboard and APA exports; add assignment reminders, rubric/source organization and course context.
- [ ] Studio: verify already-installed production tools; add reusable project templates, recording/routing status and Media Center handoff.
- [ ] Forage/Deep Forage: verify search/indexing from tabs; add research-source export to Author/School and inspectable queued research.

## 6. Kali Bay and larger expansion

- [x] Owner reports `kali-bay status` as ready; preserve its existing isolated environment.
- [ ] Reconcile the newer Kali tool-launcher and Kali-only installer branches before further edits; installation is not established by source availability.
- [ ] Verify security category launchers and Kali Purple tools inside the isolated environment.
- [ ] Implement live TV/network playback and casting after native media decoding is reliable.
- [ ] Add device/network-share views, portable AI DJ packaging and broader multi-display support after core desktop/media qualification.

Build/source checks may be run during development. The owner requested that the
installed workflow checks be grouped after builds are ready; do not repeatedly
interrupt ongoing installation to demand every manual check individually.

Previous System addition validation: 88 Python regressions, native Qt desktop integration
including System/Recovery refresh, feature-script validation and installer shell
syntax checks passed. The new System panels and asynchronous service polling
are source-complete; their installation on the owner PC is not confirmed.

The face/window-controls build includes the System/Recovery changes from PR #16. Source checks and owner installation are separate; this new build is not yet confirmed installed.

Face/window-controls validation: 93 Python regressions passed; native Qt
integration passed for all 15 tabs plus taskbar Close and overflow Close actions.
Slow-reply responsiveness, markup escaping, fragmented Unicode replies and
speaking-only mouth movement passed. Socket framing uses a mocked transport
because this development runner forbids AF_UNIX sockets; real installed-agent
and KDE window-manager checks remain pending. Installer syntax and whitespace
checks passed.
