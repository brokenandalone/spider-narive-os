# Spider OS integrated upgrade wave 3 | October 11, 2026

**Source stage only. No installation, merge to main, restart, real microphone test or owner PC file changes.** This branch stacks on PR #81, which stacks on the guarded daily release lineage (#72 and #66).

## Fully staged source improvements

### Author: Broken World Master Canon (source PR #79)
- New native Master Canon UI and local data model alongside the existing Story Atlas, project maps, DOCX import, manuscript revisions and Webbie author command channel.
- Preserve review/approval history, story dossiers and link back to user-authored source records. New source modules: `author/master_canon.py`, `author/master_canon_widget.py`. Original Author GUI/store/commands/control socket were compared to their **exact** PR #79 parent blobs before applying the new versions.
- Database and manuscript content remain personal and outside the upgrade manifest. No story canon is silently changed by this source integration.

### Studio: Production Board v10 (source PR #80)
- Versioned production board and cross-tab handoffs on top of v9 Release Desk, band mixer, mastering and user voice workflow.
- New source modules `studio/production_board.py`, `studio/production_board_panel.py`; Studio main UI and install inspector verified against exact parent version before replacement.
- Studio native reconciliation is updated in the existing strict owner-layout reconciler. Unrecognized installed UI changes still require owner review, never silent overwrite.
- The existing Webbie resident agent receives only the feature's context-aware Studio status patch, preserving preexisting Forage integration and trusted speaker/STOP routing.

### Webbie: Voice Lab diagnostics (source PR #78)
- Optional per-WAV-segment voice verification gate; speaker evidence must match a bounded audio hash and carry trusted provider provenance.
- User-confirmed, ephemeral, three-second offline hearing test; per-recording Listening status; offline read-only Voice Lab readiness diagnostics.
- Default `speaker_verification.enabled=false`. **An actual Cory/Shayna speaker biometric provider is NOT included** and no enrollment, speaker model or real microphone verification has occurred. Whisper transcripts, wake words, faces or asserted names are never sufficient identity.
- Emergency STOP remains possible without owner identity. Normal spoken commands remain restricted until trusted verification is actually available. **Deploying with no verified provider risks loss of normal spoken commands. This is an active installation blocker.**
- No downloaded voice models, automatic recording test, external voice sharing, cloud calls or service restart.

## Release gates and user-customized PC
- All additions are in the combined `system/release_batch.py` APP_FILES manifest, tracked by the source and read-only PC acceptance tools. The system-wide once-per-Indianapolis-day receipt policy remains active; standalone Author, desktop and Kali installers stay blocked.
- Local `webbie/config/default.json` is **explicitly not included** in the live-upgrade APP_FILES and is not silently replaced. No real verifier module is bundled.
- Release plan tracks pinned PRs #78, #79 and #80 with `integrated:false` until exact final cross-repo acceptance and owner review.
- **New independent gate:** `voice_pipeline_verified=false`. Even with passing GitHub source CI and matching installed code checks, an approved release must be blocked until actual Cory/Shayna/TV discrimination, live microphone, wake/sleep/STOP, TTS feedback and rollback behavior are explicitly proven on the PC. The owner and installed-PC approval flags remain false.

## Acceptance checks

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
python3 tools/daily_release_continuity.py --json
python3 tools/combined_release_audit.py
python3 system/release_batch.py --check
python3 tools/daily_pc_acceptance.py --phase before --json
```

A passing source test does not approve on-PC installation. The daily continuity audit should return **BLOCKED** while it lacks installed-PC evidence, full PR integration sign-off, provider enrollment, hardware compatibility, independent backup/rollback validation, a pinned final release SHA and the owner's explicit install approval. Do not change flags to pass tests on the owner's behalf.
