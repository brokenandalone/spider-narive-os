# Spider OS next-session handoff — October 9, 2026

This is the source-of-truth recovery point for the ongoing owner-PC upgrade.
**Do not reinstall Spider OS. Do not reimport the Author manuscripts.**

## Installed and owner-confirmed

- Dell / Spider OS boots again following the power outage. All personal data
  reported present. Root cause of the temporary boot failure is unknown.
- The Web and KDE Plasma desktop exist and work. Only a few desktop bugs remain.
- Owner reports the login selector shows X11 above Plasma/The Web, but has **not yet verified the active session type**. Run `echo "$XDG_SESSION_TYPE"` from Konsole before installing the X11-specific overlay; verify actual mouse pass-through and fullscreen hiding after installation.
- Author SQLite audit: **20 books, 39 chapters, 20 imported source fingerprints**.
  Original DOCX backup placement and chapter-content QA still need review.
- Webbie, Ollama, AI DJ, PipeWire and WirePlumber: active in Oct 9 read-only
  audit. Webbie's existing agent and voice modifications must be preserved.
- Existing Kali Bay interface installed; preserved container was *exited*.
  Do not reinstall Kali or mistake a stopped container for failure.
- Spider Media Center archive installed; actual playback/broadcast acceptance
  remains separate.
- Owner additionally confirmed **System/Recovery dashboards (#5) and Media
  playback controls (#4) work** in the current Plasma desktop.
- Existing desktop backup from Oct 8:
  `/usr/local/lib/spider-os/upgrade-backups/the-web-20261008-211515`.

## GitHub work performed while user rests

1. **PR #21: Webbie click-through face + optional OneDrive**
   https://github.com/brokenandalone/spider-narive-os/pull/21

   Branch `upgrades/webbie-transparent-overlay`.
   Pinned source revision `241922a1ad2157c316282166a3b812b8cf687768`.
   Source tests passed. The face is a semi-transparent lower-left click-through
   overlay for Plasma X11 / The Web X11, hides during fullscreen, can sleep
   until 8 AM, and uses the existing speaking marker. OneDrive connection is
   deferred by design: no forced Microsoft sign-in, no voice/service dependency,
   and only an explicitly designated local Webbie share is eligible for
   background upload. A symlinked share root is rejected and config presence
   is not mistaken for verified cloud access. The new add-on installer does
   not replace the native desktop or the customized Webbie agent.

2. **PR #22: Webbie Author Bay Writer / local model selection**
   https://github.com/brokenandalone/spider-narive-os/pull/22

   Branch `upgrades/webbie-author-context`. Source tests passed.
   Adds **Writer** in Author Bay unless an owner preference overrides it, and
   makes the local brain honor its existing model setting without downloading
   new models. **Not installed on the owner PC**; resident Webbie needs a
   deliberate agent-specific review.

3. **PR #24: Opt-in local webcam vision source**
   https://github.com/brokenandalone/spider-narive-os/pull/24

   Branch `upgrades/webbie-local-vision-snapshot`. Build and tests are tracked
   in GitHub Actions. Takes a single webcam frame only after an explicit
   confirmation, shows a camera-on indicator, keeps the image in memory and
   processes it with a vision-capable local Ollama model. No continuous camera,
   screen capture, network/cloud image upload or automatic wake-up capture.
   **Not installed or enabled on the PC.**

## Latest owner preference

- On October 9 the owner requested **Student** as Webbie's form of address in School/Study, alongside **Writer** in Author Bay.
- The `upgrades/webbie-author-context` source branch / PR #22 now contains both `study` and `school` mappings, updated default config, brain prompt, and regression tests. This is **source-only** until a separately reviewed agent-specific installation. Keep the older Studio=Justin and Kali Bay=Spider forms of address.

## Tomorrow: safe sequence (only after user is at their PC)

1. Check the actual current session using `echo "$XDG_SESSION_TYPE"` in Konsole. The owner sees X11 in the login selector, but that alone does not prove the selected active session. The click-through overlay is X11-only and needs actual mouse/fullscreen testing.
2. Confirm recent independent backup of Author and originals. Do not reimport
   the verified 20-book database. Verify source revision and add-on prerequisites.
3. If installing only PR #21, fetch the **exact pinned revision** above and
   run `bash the-web/package/install-webbie-extras.sh --check` before its
   selective `sudo bash` installer. **Do not rerun a full desktop installer.**
4. Log out and back into X11 once for overlay autostart. Confirm the visible
   portrait, real mouse clicks passing through it, fullscreen video hide/return,
   night sleep, wake, and continued voice conversation.
5. **OneDrive can wait indefinitely.** When the owner chooses Connect OneDrive,
   install rclone if necessary, authenticate interactively, and test a harmless
   explicitly selected note in `~/Documents/Spider OS/Webbie/OneDrive`.
   Confirm the background copy independently. Do not grant entire-drive or
   manuscript access by default.
6. Keep PR #22 agent changes and PR #24 webcam access separately staged until
   their owner-PC review. They must not silently replace custom voice code.
7. Later: exact startup splash/GRUB branding audit after boot config backup;
   Kali Purple runtime verification; media broadcast and visualizer QA;
   notifications/tray, full dark mode, Webbie authorized voice users, full
   screen awareness and future native ISO release.

## Decisions to ask the owner (do not presume an answer)

- When Webbie is **asleep for the night**, should that hide only her portrait,
  or pause the microphone/listening service too? The existing overlay only
  hides the face and does **not** stop the voice agent.
- Should OneDrive access remain restricted to the **Webbie share folder**, or
  should Webbie eventually read more user-approved areas? Broader access
  needs explicit permission boundaries and never enables silently.
- For future room awareness, should Webbie see only on request, or remain
  active for an explicitly approved session with a permanent visual indicator?
- Pending: Confirm the active session with `echo "$XDG_SESSION_TYPE"`; the owner only confirmed X11 appears as a login option.

## Never overwrite

Installed user-customized Webbie agent and voice configs, Ollama models, user
memory, original Author manuscripts and DOCX files, local School/Studio files,
Kali Bay container/UI, Media Center data, wallpaper originals, existing desktop
backup snapshots, installed GRUB/encryption or the Plasma fallback.

A passed GitHub workflow means **source validated**, not **working on Dell**.
Use user-observed installed status to check off actual acceptance separately.
