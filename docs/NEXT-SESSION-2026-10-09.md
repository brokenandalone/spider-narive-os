# Spider OS next-session handoff — October 9, 2026

This is the source-of-truth recovery point for the ongoing owner-PC upgrade.
**Do not reinstall Spider OS. Do not reimport the Author manuscripts.**

## Installed and owner-confirmed

- Dell / Spider OS boots again following the power outage. All personal data
  reported present. Root cause of the temporary boot failure is unknown.
- The Web and KDE Plasma desktop exist and work. Only a few desktop bugs remain.
- **Confirmed in Konsole:** `XDG_SESSION_TYPE=x11` and `DESKTOP_SESSION=the-web`. The active Spider OS session uses The Web on X11, which matches the Webbie click-through overlay target. Actual click-through, fullscreen hiding and night-sleep behaviors still require on-PC testing.
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

## Latest night-sleep decision (October 9)

The owner clarified that Webbie should **stay visible with closed eyes, dimmed,
and obviously asleep** in the lower left of the screen. Audio transcription may
continue, but **ordinary heard speech must be ignored** until an explicit wake
phrase. Webbie's background tasks, model service, AI DJ, timers and ordinary
housekeeping should continue. This is NOT hardware microphone mute.

- Source PR #25: https://github.com/brokenandalone/spider-narive-os/pull/25
- Built on PR #22, with quiet shared state for the floating portrait and agent
  voice gate. "Goodnight Webbie" / "Hey Webbie go to sleep" enter indefinite
  quiet mode; "Hey Webbie wake up" exits. Manual GUI sleep/wake remains possible.
- Face does NOT disappear while sleeping; it still hides temporarily for a
  fullscreen movie. No automatic 8 AM wake.
- PR #21's **older** selective add-on build still has the former hide-until-8AM
  behavior. **Do not recommend that pinned PR #21 artifact as completing the
  new sleep requirement.** A compatible updated selective rollout must be
  reviewed; Webbie's installed customized agent is not to be overwritten.
- Wake-phrase voice identity authorization remains a separate unverified
  Cory/Shayna-only requirement. A recognized command is not secure proof of
  the speaker.

## Tomorrow: safe sequence (only after user is at their PC)

1. **Session confirmed:** `XDG_SESSION_TYPE=x11`, `DESKTOP_SESSION=the-web`. No more login-session checks required for X11 eligibility. Test actual click-through and fullscreen hiding after installing the add-on.
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

- **Resolved:** keep the portrait visible with sleep expression, ignore ordinary heard speech except an explicit wake command, keep all background services running. This is a soft voice gate, not a microphone mute.
- Should OneDrive access remain restricted to the **Webbie share folder**, or
  should Webbie eventually read more user-approved areas? Broader access
  needs explicit permission boundaries and never enables silently.
- For future room awareness, should Webbie see only on request, or remain
  active for an explicitly approved session with a permanent visual indicator?
- **Resolved:** The owner ran `echo "$XDG_SESSION_TYPE"` and `echo "$DESKTOP_SESSION"`; results were `x11` and `the-web`.

## Never overwrite

Installed user-customized Webbie agent and voice configs, Ollama models, user
memory, original Author manuscripts and DOCX files, local School/Studio files,
Kali Bay container/UI, Media Center data, wallpaper originals, existing desktop
backup snapshots, installed GRUB/encryption or the Plasma fallback.

A passed GitHub workflow means **source validated**, not **working on Dell**.
Use user-observed installed status to check off actual acceptance separately.
