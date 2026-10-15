# Spider OS afternoon integration ledger | October 10, 2026

**Status: source staging and audit, not an installable release.** This branch combines the source files that have independent ownership. It does not yet reconcile all shared entrypoints or the currently installed customized PC code. A green isolated PR is not a green combined release.

## Source incorporated
- Webbie resident/context-aware/desktop Autopilot foundation from PR #47 (includes #36 and predecessor stack).
- Studio local generation, My Voice, vocal roles and mix scaffolding from PR #35 (includes #34/#27); **training quality and local model/GPU unverified**.
- Study embedded SNHU interface and course tools from the Studio/Study stack; school OneDrive account access not automatically connected.
- Author full chapter/book review, Webbie narration, saved review navigation, bookmarks and World Continuity source from PR #45 (includes #44/#42/#37).
- Native, VM-free Kali Distrobox catalog/manager and Webbie chat from PR #46 (includes #43/#39). PR #41 full VM is **deliberately excluded**.
- Nova BCN AI DJ source from merged PR #38. No portable DJ hardware/software.
- Forage evidence guard and PC historical reconciliation tests/docs from PR #30. Already-working webcam source/settings must not be replaced.

## Overlap and install blockers
Different branches modified the **same** files: `webbie/agent/webbie.py`, `webbie/voice/whisper_listener.py`, `the-web/shell/main.py`, `the-web/shell/webbie_panel.py`, `system/release_batch.py`, `the-web/package/install-author-webbie.sh`, and `docs/MASTER-UPGRADE-CHECKLIST.md`. This branch uses the PR #47 versions for those entrypoints to avoid silently overwriting newer Webbie work; **Author voice routing, Studio/Study integration, Kali assistant wiring and combined install coverage remain to be reconciled**. Do not treat the presence of a module as proof it is invoked by the UI.

PR #30 changes `webbie/brain/brain.py` with a PC-memory fix and PR #29 changes `the-web/shell/webbie_camera.py` for an MJPEG working camera. Neither unreviewed older file was blindly applied. Latest customized PC source remains the authority until the on-device read-only inventory.

Single installer: `system/release_batch.py` on this branch still has the Webbie-oriented manifest. **It is not a complete manifest covering all Author/Studio/Study/Kali/Media/Forage modules**. The older `the-web/package/install-desktop.sh` copies entire directories and may overwrite owner-edited installed files. Do not use either to force a full update at present.

## Required before marking this a release
1. Read-only compare the current PC source hashes, installed modules, services and GUI/X11/voice state.
2. Merge and test shared entrypoints, preserve memory/research/interrupt/face/camera/model and authorized-user behavior, integrate Author/Study/Studio/Kali/Nova.
3. Expand a single, fail-closed installer manifest to all modified sources, including native Study, Studio AI/voice, Author, Kali and BCN, with backups, non-overwriting data policy and rollback.
4. Run full source CI on **this** integration head, then on the final integrated head. Validate one instance Webbie, stop/sleep/camera, book review/narration, Studio local engine, Study login/OneDrive, Kali Distrobox and native KDE desktop on PC before enabling the single apply command.
5. Preserve already-installed wallpapers, encrypted boot, manuscripts, schoolwork, models, audio/voice profiles, MariaDB/SQLite histories, optional OneDrive settings and Media Center data. Never automatically install packages/VM/bootloader upgrades.

The local afternoon ZIP contains a safe source-stage and installed-inventory tool. The ZIP is a **staging/diagnostic folder**, not an unsafe auto-installer.