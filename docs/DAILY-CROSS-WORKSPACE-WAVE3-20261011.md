# Spider OS Wave 3 | Single Daily Installation Candidate
**Source branch:** `release/cross-workspace-oct11-wave3` | **PR #87** | **October 11, 2026**

**Status: DRAFT.** Wave Three is source-only work built on the passing Wave Two combined release ([PR #81](https://github.com/brokenandalone/spider-narive-os/pull/81)). No changes have been installed on the user's running Spider OS PC. Do not run a separate Author, Studio, Webbie or Kali installer.

## What Wave Three adds

**Webbie Voice Lab:** Opt-in diagnostic view for the installed local microphone/Whisper pipeline, a strictly owner-clicked 3-second local hearing test that deletes temporary audio, non-authorizing active-listening UI indicator, and optional per-segment speaker evidence. A provider is not included and is disabled in the default configuration. Hearing a voice, a transcript, a wake word, the webcam, or a user name **never proves the speaker is Cory or Shayna**. Explicit STOP remains universal; normal voice commands remain untrusted unless a separately verified, calibrated local provider supplies fresh matched audio-segment evidence. Browser and desktop actions continue to require their independent owner grants.

**Author Master Canon:** Adds a private revision-tracked canon ledger to the existing Story Atlas and manuscript tools. New claims start proposed and become established only through explicit writer confirmation, with citation checks and no automatic rewrites of chapters. Commands may open the canon dashboard but do not approve or invent canonical facts.

**Studio Production Board V10:** Adds persistent, private production checkpoints, explicit WAV source/stem review, and UI handoffs to the existing band mixer and release desk. Does **not** automatically generate, publish, separate stems or train vocal models. Webbie gains a bounded, read-only `Studio progress` response and explicitly approved Studio launcher.

**Continuity and Recovery:** All eight new application modules enter the **one central daily guarded system installer** alongside earlier workspaces. The read-only PC acceptance tool now compares new Wave Three modules by exact source hash. New modules that do not exist on the installed PC are described as **pending additions** during a pre-install review, not treated as suspicious old files. Any symlink, unknown modification or missing legacy file remains a blocker. After installation, every candidate module must match.

The daily receipt guard also treats a backup directory created for a same-day **partially failed** batch, even before its manifest exists, as an ambiguous used installation slot. This prevents accidentally rerunning a system-wide upgrade after a crash. Restore/rollback is separately available and is not a second normal install.

## Source testing and safe release sequence

- Run `python3 -m unittest discover -s tests -p 'test_*.py'` on the exact Wave Three commit; test counts from other branches are not acceptance evidence.
- Confirm both GitHub workflows pass on the same Wave Three SHA, including the desktop smoke and recovery checks.
- Run `python3 tools/daily_release_continuity.py --json`; it intentionally remains **BLOCKED** until the latest PR heads, shared paths and installation gates are fully reviewed.
- On the real PC from a staged checkout, `python3 tools/daily_pc_acceptance.py --phase before --json` compares **only** fixed installed Spider OS application files; it does not read private projects or install/restart anything. Differences must be reconciled against the installed customized files, not blindly replaced.
- Confirm backup, daily slot, explicit owner approval, Webbie speaker boundary, GUI workspaces and Nova playback. Apply **one** approved, consolidated PC batch only when every gate is cleared. Perform `--phase after` plus real audio, GPU, UI, Studio, study storage, Author manuscripts, Kali Distrobox and boot recovery checks.
- All user data, manuscripts, albums/stems, school documents, enrolled voices and models must remain untouched. No automatic enrollment, camera capture or cloud STT.

## Pending actions

The PR remains a draft. Existing daily plan `system/daily_release_plan_20261011.json` deliberately leaves `candidate_commit`, `source_ci_verified`, `installed_pc_reconciled`, `rollback_validated` and `owner_approved_install` unset until supporting evidence exists. Tests passing **does not install or approve** the candidate. The PC's installed source and runtime still need independent owner-side reconciliation.
