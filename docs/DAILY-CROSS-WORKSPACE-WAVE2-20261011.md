# Spider OS: October 11 second consolidated release wave

**Status:** Unified GitHub source staging, **not installed**, **not approved**. This is a downstream candidate based on Kali Bay daily integration PR #72, itself based on the nine-workspace unified release PR #66.

## What is reconciled in source

- **Author Story Atlas** (PR #75): verified that `author/main.py`, `author/store.py`, `author/commands.py`, and `author/control_socket.py` matched their source parent before incorporating the newer versions. Adds `author/story_atlas.py` and `author/atlas_widget.py`, with regression tests.
- **Studio v9 Release Desk** (PR #74): verified exact source parents for `studio/main.py`, `studio/band_mixer_panel.py`, and Studio installer audit. Adds export/profile/preset modules, GUI, tests, and updated reviewed legacy visual-layout reconciler without bypassing customization protections.
- **Study planning, learning coach and reading library** (PRs #71, #73, #77): unique-context patches, in order, into `study/study.py`, `study/store.py`, `study/assignment_workspace_ui.py`; the reading-library patch into the existing Webbie homework dialog. Added the full local module set for weekly planning, milestones, backups, source guidance, explicit tutoring, offline APA checks and reading library, including their regression tests. No individual school or OneDrive installer.
- **Webbie trusted action boundaries and diagnostics** (PR #76): unique-context patch into existing `webbie/agent/webbie.py`, resident context, desktop control panel, cognitive panel and Webbie panel. This preserves previously integrated Forage, wake/sleep, and STOP routing. Adds bounded trust, readiness and action receipt modules with their tests. Explicit user permission and successful execution reporting remain separate concepts.
- **Kali Bay** (PR #70 via PR #72): private Evidence Ledger, local report verification, mandatory source comparison and combined installer inclusion remain present.

The combined `system/release_batch.py` manifest explicitly includes every added application module above. The read-only combined source auditor and cross-workspace smoke suite now check the new modules and their actual shared entrypoints.

## Release controls, unchanged

1. Exactly **one** owner-approved Spider OS system upgrade per Indianapolis calendar day; emergency rollback is exempt.
2. A GitHub commit is **not** an on-PC install, a working sound/microphone/camera, an installed Kali container, or a BCN broadcast acceptance pass.
3. New PR references are pinned into the daily continuity plan, but all **integration sign-offs, actual-PC reconciliation, release candidate final SHA, rollback and owner approval flags remain pending**. Source staged does not mean approved.
4. The separate Author, desktop, and Kali source installers stay blocked for installs. Their check/listing code is not an authorization to overwrite desktop customization.
5. Preserve all existing manuscripts, school files, stems, photos, recovery work, private evidence, Ollama models, speaker authorizations, boot chain and media service state.

## Checks on the exact candidate

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
python3 tools/daily_release_continuity.py --json
python3 tools/combined_release_audit.py
python3 system/release_batch.py --check
python3 tools/daily_pc_acceptance.py --phase before --json
```

The first command should pass in GitHub Actions. **The continuity audit should remain BLOCKED** until source overlaps and genuine PC approval/rollback receipts are reviewed. Never edit the plan to mark unverified gates true just to permit an install. No PC install/reboot/services were performed by these commits.
