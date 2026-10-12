# Spider OS Wave 4: four major, single-batch source upgrades

**October 11/12, 2026 source candidate only. Unmerged, not installed, no services/microphone/camera touched.** This draft stacks on the already green unified Wave Three crash-safe installer [PR #87], which itself stacks on the previous daily candidates.

## 1. Spider Studio v11: actual recorded-audio QA and DAW handoff
- Port exact parent-matching Studio main UI, production board/controller, and source inspector from [PR #82], with strict reconciliation of the existing custom desktop UI rather than replacing user preferences.
- Add bounded local audio-quality analysis and its Qt panel. Export or test only on explicit user action, with no microphone monitoring, automatic uploads, or production stem alterations.
- Add revised next-step information through Webbie's narrow, read-only Studio route. Never treat generated status as proof a file was mixed or exported.

## 2. Author: approved Canon Intelligence
- Port exact parent-matching Author main, canon store, voice command and local canon models from [PR #83].
- Add an on-device continuity proposal workflow with precise source anchors for novels and lore, separate from accepted canon. Canon changes require user review; no silent editing of manuscript text, established identities or story history.
- The actual writing databases/manuscripts remain outside the batch source manifest.

## 3. Study: provenance-aware long reading passages
- Port the exact source-parent versions of Study reading store, reading UI and material parsing from [PR #84].
- Add bounded passage segmentation and search, with source context instead of fabricated citations. Preserve existing OneDrive / reading-library workflows and do not silently upload private school documents.

## 4. Webbie: resilient offline Jarvis engine
- Integrate reviewed, unique-context patches from [PR #88] into the existing resident AI, local model brain, readiness, speaker provider adapter and Voice Lab.
- Add local model timeout/backoff, owner-private aggregate voice metrics, explicit approved-launch intent parsing, and a read-only diagnostics CLI.
- Direct desktop launch commands must be complete, intentional requests. Casual mentions, negated launch phrases and outside voices must not trigger program launching.
- The real speaker verification provider **is not included**, voice config is not overwritten, and Voice Lab checks are not proof of Cory/Shayna identity.

## Strict daily continuity

The global batch `system/release_batch.py` now stages the new app source modules, with its daily receipt lock, transactional backup and rollback tests unchanged. The read-only release and owner-PC acceptance audits track the added modules. Source PRs #82, #83, #84 and #88 are pinned in `system/daily_release_plan_20261011.json`, but `integrated`, `source_ci_verified`, `installed_pc_reconciled`, `rollback_validated`, `owner_approved_install` and exact candidate-acceptance fields remain unapproved.

A separate `voice_pipeline_verified=false` gate blocks full install unless the actual PC's authorized speaker provider, real microphone, Cory/Shayna/TV acceptance and rejection, STOP, wake/sleep, TTS feedback, and rollback are validated. No source CI test, waveform hash or quoted name may substitute for owner voice enrollment.

### Source checks

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
python3 tools/combined_release_audit.py
python3 tools/daily_release_continuity.py --json  # expected BLOCKED pending real approval
python3 system/release_batch.py --check             # read-only, may flag actual PC customizations
```

**Do not run `--apply`**, merge to main, flip plan flags or skip the owner-PC comparison to declare the release installed. This code lives on GitHub only until the user runs an independently reviewed single batch.
