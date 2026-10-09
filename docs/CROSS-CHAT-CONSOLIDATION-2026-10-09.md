# Spider OS cross-chat consolidation and GitHub release ledger
Reconciled 2026-10-09 from accessible user/assistant history, current GitHub branches and the Oct 9 installed-PC read-only audit. Retrieval of older unrelated chat messages was unavailable, so this is **not a claim of exhaustively reading every archived conversation**. The code and installed-PC reality remain the authoritative checks.

## One active development workflow
- Owner chose this conversation as the **single active Spider OS build chat**.
- Main source repository: `brokenandalone/spider-narive-os`.
- Integration branch: `integration/webbie-author-camera-sleep-20261009`.
- Definitive task list: `docs/MASTER-UPGRADE-CHECKLIST.md` in that integration branch.
- Owner wants **one install per explicit installation request**, not one per day and not per PR. Continue GitHub source work without touching the live Dell until installation is requested. When ready, freeze a single tested release commit, run one preflight, create one backup/manifest, apply one unified installer, test, and retain rollback.
- Never infer installed-PC success from green GitHub CI.

## Installed PC and historical decisions
- Oct 9 verified `XDG_SESSION_TYPE=x11` and `DESKTOP_SESSION=the-web`. Plasma remains a fallback. Existing boot/encryption must not be rewritten.
- Owner reports files survived the outage. Read-only audit confirmed Author library `20 books/39 chapters/20 imported fingerprints`, School DB 1 course / 0 assignments, existing Studio/media folders; *not* proof of backups, content completeness, untouched DOCX originals or disk health.
- Webbie, Ollama, AI DJ, PipeWire and WirePlumber active. Kali Distrobox exists but was exited. Installed Kali Bay selective backups: `kali-bay-20261008-210609`, `kali-bay-20261008-210722`. Earlier desktop backup `the-web-20261008-211515`.
- Owner says desktop System/Recovery dashboards and basic media playback controls work; do not duplicate changes merely because checklist source PR remains draft.
- Original wallpaper set remains installed; approximately 59 alternate wallpapers added. New Webbie/Forage/Deep Forage/Communications wallpapers should not replace original art without approval. On-machine placement unverified.
- Installed Spider Media Center Electron `app.asar` repair has rollback copy; visualizer/radio/live TV/casting and real playback acceptance pending.
- Names: **Spider** in Kali Bay; **Justin** in Studio; **Student** in School and Study; **Writer** in Author; **Cory** elsewhere.
- Sleeping: Webbie's **face stays visible with closed eyes** in the lower-left, click-through; fullscreen video temporarily hides it; ordinary speech is ignored; deliberate wake phrase returns to conversation; Ollama, AI DJ, scheduled jobs and other established background work continue. Passive microphone capture is allowed for recognizing the wake phrase, but it is not a hard mic mute. Speaker authorization remains unverified.
- OneDrive: Connect only whenever owner requests, then enable a scoped user-approved workspace in the background; never block Webbie if login is deferred, rclone is absent or cloud is offline. OneDrive share is not automatic full brain/memory/manuscript sync.
- Camera: opt-in only, visual active state, local-only image understanding; PR #23 already supports user-activated look/watch and separate consenting Cory/Shayna face slots. **Face cues must never authorize voice commands**. Screen awareness remains separate, not silently enabled.

## GitHub dependency graph and status
- PR #17 desktop essentials and diagnostics source tested, not necessarily applied as that exact batch.
- PR #20 Author website feature port, global docked Webbie per-workspace panel, Story Bible/search/read aloud/focus/review/publishing. Base: #17.
- PR #23 builds on #20, adds consent-bound camera, look/watch-room, optional face profiles, voice-to-vision, strict Author/Webbie selective installer and rollback. Latest verified head `83d692b4c3115a2f4edeed2730a77774c2b49364`, GitHub Action 37944167149 **success**. Still draft, source only. Other chat reported this part finished, not a complete all-workspaces release.
- PR #21 builds on #17: separate stronger X11 click-through portrait (XFixes input region), OneDrive adapter and optional timer, selectable autostart and menu launchers. Earlier #21's hide-until-8AM behavior is superseded by owner's quiet-sleep decision.
- PR #22 builds on #21: owner names and configured local Ollama model.
- PR #25 builds on #22: shared indefinite quiet sleep and voice gating, visibly sleeping portrait, no background shutdown. Source tests passed.
- PR #24 builds on #22: independent explicit one-frame webcam prototype, privacy/source tests. Its capture/GUI duplicates overlapping #23 camera behavior; choose one consent model, do not expose two separate camera paths in the release.
- PRs #18/#19 audits already merged into #17's branch; #14/#15 Firefox and workspace links merged in source line.
- Do not merge each stacked PR into `main` or install conflicting panels one by one. Consolidate in one integration branch, maintain PR traceability and final green CI.

## Current integrated source and remaining release blockers

- Draft [PR #26](https://github.com/brokenandalone/spider-narive-os/pull/26) now integrates Author website tooling, opt-in camera/room watch, optional face cues, spoken local vision, all five owner-selected context names, OneDrive-on-demand and the indefinite visibly sleeping X11 Webbie face.
- The Web's desktop starts one locked, mouse-pass-through external portrait. The shared Webbie panel uses the same sleep flag and one combined Author/camera/cloud interface; the agent keeps its voice listener and background loops while ignoring ordinary speech when asleep.
- GitHub source/Qt regressions passed on integration SHA `5cbd4a9a8941e2e714acc17ae62d3a35d8c51db2` (Actions run `37947832794`). The owner PC has **not** been modified and its installed customized voice/mic agent remains authoritative.
- The source now contains `system/release_batch.py`, a **single** guarded release/rollback path. Its tests cover unknown-file protection, atomic code installation, backup manifest restoration and symlink rejection. The older per-component installers remain historical compatibility code; do not run them for the unified release.
- PRs #17/#20/#21/#22/#23/#24/#25 remain draft or unmerged on their existing branches. They were **reconciled in code** for PR #26, not blindly merged into the main branch.
- Before deployment: verify the final frozen PR #26 commit CI; run the one non-mutating preflight on the Dell; separately secure real Author SQLite + originals backups and verify local customizations. The X11 face, cloud OAuth, camera hardware/model, service restart and safe rollback still need owner-PC acceptance. Stop rather than overwrite unrecognized files.
- Speaker authentication restricted to Cory/Shayna, genuine screen awareness, robust user controls/notifications, Media Center radio/visualizer/TV/casting and upstream OS/ISO migration remain subsequent checklist items, not declared installed.

## Longer checklist work still open
1. Preservation: backups of Author DB and formatted original DOCX; restoration test; disk/boot read-only inspection.
2. Desktop essentials: notifications, system tray, global dark mode, audio/device slider, quick settings, keyboard shortcuts, window controls.
3. Webbie: authorized speaker recognition, continuous conversation/interruption, voice/mic reliability, accurate lip sync, local model fallback, OneDrive permission boundaries, opt-in screen awareness.
4. Author: live 20-book content and export QA, companion materials, continuity engine, careful user-approved edits, website parity.
5. Media: original Spider Media Center visualizer, real DJ/radio status, IPTV/live TV, native player/casting, MPRIS.
6. Kali Purple readiness, Studio production integration, Study SNHU and APA qualification, Forage/Deep Forage, Recovery/Vault, Guardian, Art Lab, Communications.
7. Packaging: pinned Ubuntu build runners; tested Spider OS version migration and native ISO/VM build; branded boot only after backups and tested firmware/GRUB discovery.

## Do not touch yet
Installed personal manuscripts and author database, Webbie customized mic/voice service, user's Ollama models, current encryption/GRUB/SpiderRoot, Kali container, Studio, Media Center data, Google/Microsoft credentials, private webcam footage, original wallpapers, or OS installation.
