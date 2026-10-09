# Spider OS | Consolidated upgrade installation gate

**As of 2026-10-09:** GitHub implementation is **not** proof of host installation.
The native installed desktop already works, and Broken World JSON content opens
in Author. Treat private manuscripts as the source of truth. Do not reimport.

## A. Release blockers and recovery
- [x] PR #20 Author Studio site feature port and shared Webbie bay panel
- [x] PR #23 webcam room awareness and direct wake-word visual questions
- [x] Independent optional local familiar-face enrollment for Cory and Shayna
- [x] Camera off by default, clear activity indicators and sleep shutdown
- [x] Preserve installed microphone, Whisper listener and speaking controls
- [x] Strict preflight and backed-up selective Author/Webbie installer
- [x] Hash-verified selective source rollback, with no manuscript edits
- [x] Read-only hardware and Ollama readiness script
- [ ] Confirm latest source/Qt CI run green
- [ ] On machine, run `--check` for installed-version compatibility
- [ ] On machine, inventory camera devices, ffmpeg and Ollama vision model
- [ ] On machine, verify safe backup of current Author SQLite DB and originals
- [ ] On machine, apply targeted installer only after preflight passes
- [ ] Reload The Web and restart Webbie service after saving user work
- [ ] Test wake-word voice (existing mic), camera photo, vision question and sleep/wake
- [ ] Test both optional facial profiles independently when each person consents
- [ ] Inspect immediate rollback if any regression is seen

## B. Author Bay
- [x] Native library imported and books open (reported by user)
- [x] Story Bible, companion library, cross-book search, word count, revisions
- [x] Read aloud, focus mode, explicit Webbie suggestion preview and approval
- [x] DOCX, EPUB and PDF publishing modules in GitHub
- [ ] Copy original source DOCX documents to protected Originals folder and verify
- [ ] Verify real-library search, paragraph fidelity, export files and autosave
- [ ] Expand continuity and character relationship graph
- [ ] Test prolonged writing session, recovery, and backup restoration

## C. Webbie and The Web
- [x] Persistent shared side panel across bays; Author title-only context and Writer form of address
- [x] Visible click-through Webbie portrait with sleep state, synced with dock
- [x] User-controlled webcam, local vision and spoken scene questions
- [ ] Verify installed window controls, minimized apps and system tray
- [ ] Verify dark mode, notifications, volume/mic controls and normal desktop ergonomics
- [ ] Harden optional speaker verification before privileged commands
- [ ] Extend authenticated speaker awareness, screen awareness and permissions
- [ ] Add per-bay deep Webbie functionality and OneDrive login on demand
- [ ] Ensure privacy indication and opt-in behavior for screen, room and other sensors
- [ ] Test portrait animation with real resident TTS and full-screen playback

## D. Remaining bay upgrades
- [ ] Forage and Deep Forage retrieval, sources and saved research
- [ ] Study/School dashboards, academic records and APA export real-machine test
- [ ] Studio recording, AI DJ and production integrations
- [ ] Media Center visualizer, live TV, radio state and casting
- [ ] Kali Bay tools and permissions in contained context
- [ ] Art Lab, Communications, Recovery, System, Dev and other bay integrations
- [ ] New wallpaper installation verification only; preserve already installed wallpaper set
- [ ] Verify OneDrive sign-in, private workspace scoping, user approval and recovery

## Installation protocol
1. GitHub tests pass. Freeze one exact commit.
2. Run `bash the-web/package/check-webbie-vision-readiness.sh` from a checked-out build.
3. Run `bash the-web/package/install-author-webbie.sh --check` and inspect all blocked files.
4. Protect private Author DB and customized local services before any code changes.
5. Only then run targeted `sudo bash the-web/package/install-author-webbie.sh --apply`.
6. Verify service and UI one at a time. If necessary run
   `sudo bash the-web/package/rollback-author-webbie.sh --check BACKUP_DIR`
   before the matching `--apply`. Do not select an unrelated backup.
