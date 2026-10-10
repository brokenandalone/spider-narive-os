# Spider OS one-install gate | October 10, 2026

**STATUS: DRAFT, NOT SAFE TO INSTALL ON THE PC YET.**

Owner's request: combine upgrades into one release, back up once, install once, then bug-test the entire installed release. Preserve working PC changes. Never reinstall KDE/Spider OS or the Kali Distrobox, replace the encrypted boot chain, overwrite manuscripts, or force model downloads.

## Source progress

- PR #48 is the October 10 source stack. Its original source CI and Nova CI passed on the inspected SHA, but its installer and shared entrypoints were incomplete.
- This branch restores the nine missing Study homework/OneDrive source modules from PR #34, reconnects their Study UI entrypoints, and restores six Study tests.
- Read-only source and PC release-audit gates: tools/combined_release_audit.py and webbie/tools/installed_reconcile_audit.py.

## Current blockers

1. The guarded APP_FILES installer manifest has now been expanded to cover the PR #48 native-source changes plus restored Study source. **This is source coverage only**: the live Media/Nova user-unit activation path, executable launch permissions and PC-specific safe destinations still require local validation. Never confuse presence in the manifest with a working application.
2. Resident webbie/agent/webbie.py still needs wiring for the new Author voice bridge and Kali assistant without losing the customized installed agent's voice, memory, interruption and research behavior.
3. Real machine's latest script hashes and customizations must be compared before applying replacements.
4. Voice conversion/model quality, SNHU and school OneDrive authentication, live radio/Media Center, and Kali Distrobox use need actual PC qualification.
5. The spliced webcam USB cable previously triggered overcurrent errors and must not be used for sustained camera testing.

## Safe audit in ONE folder (no installation)

Run as the ordinary Spider OS user, NOT sudo:

    cd ~/spider-narive-os
    git fetch origin release/combined-20261010-audit-gate
    git worktree add ~/Downloads/Spider-OS-Batch-Audit-20261010 origin/release/combined-20261010-audit-gate
    cd ~/Downloads/Spider-OS-Batch-Audit-20261010
    python3 tools/combined_release_audit.py
    python3 webbie/tools/installed_reconcile_audit.py --checkout "$PWD"
    python3 system/release_batch.py --check

A BLOCKED result is expected until the final installer and reconciliation are completed. Do not run --apply or the broad desktop installer from this draft.

## Release acceptance, tested together AFTER one approved installation

| Area | Acceptance |
| --- | --- |
| Boot and KDE | Encrypted boot and Plasma fallback, The Web Start/taskbar, native window operations, appearance, sound and notifications. |
| Webbie | Owner/second speaker if enrolled, wake, natural followups, sleep face, stop during speech, memory/research, model selection, device reconnection. |
| Vision/autopilot | Camera permissions, actual Qwen3-VL description with SAFE replacement cable, local vision/voice bridge, consented screen awareness, supervised desktop action and immediate STOP. |
| Studio | ACE-Step installed/readiness, prompt to WAV, independent guitar directions, vocal roles, saved original take, mixing/export, truthful unready states for untrained voice models. |
| Study | Native school dashboard, SNHU portal, homework assistant, rubrics/APA, document storage, optional consented School OneDrive file roundtrip. |
| Author | Existing 20 books/39 chapters intact, full chapter/book review, read aloud through Webbie voice, bookmarks, cross-book evidence, snapshots and reversible file edits. |
| Kali Bay | Native workspace, rootless Kali Distrobox, real app catalog, safe tools, Webbie chat; no unattended scans. |
| Media/BCN | Media Center plays audio/video and shows visualizer, BCN radio is audible, Nova DJ speaks, on-air indicator matches actual broadcast. |
| Forage | Evidence-backed answers, correct source links, no placeholder citations, useful offline errors. |
| Whole build | No duplicated processes, app smoke tests and logs pass, original files/data untouched, rollback-check passes, one install receipt recorded. |

### Release rules

Do not merge or install while source audit or installed reconciliation is BLOCKED. GitHub CI passing is not hardware acceptance. Keep OneDrive credentials, user schoolwork, author database, voice samples, memory, local models and boot artifacts out of public GitHub and any shared diagnostic transcript.
