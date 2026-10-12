# Spider OS daily upgrade continuity register | 2026-10-12

**STAGED ONLY: no PC installation, merge, or model changes have occurred from this branch.**
**Source of truth: actual newer Spider OS PC install from 2026-10-10, not the older GitHub main versions.**

## One-install-per-day policy

- One consolidated system-wide installation per day, only after Cory explicitly approves the final diff.
- Snapshot installed files, hashes, config, user services/drop-ins and Ollama model versions first. Identify modified files and skip work already installed.
- Preserve every newer PC feature. Halt instead of overwriting newer local modules with older GitHub code. Fail closed for conflicts, voice authorization, or unverified models.
- Pin exact tested source commits, dry-run, backup, permit rollback, keep logs and detailed receipts. Verify each workspace after installing, then advance known-good baseline.
- An earlier successful PR test is not a complete cross-component PC test. Don't independently run old workspace installers again.

## Current Webbie voice hotfix (not yet installed/verified)

- Online primary: Microsoft `en-AU-NatashaNeural`, installed Edge TTS 7.2.8. Multiple online voices get HTTP 403, so do not claim Microsoft speech repaired.
- Offline preference: female Australian **Matilda / speaker 7** in previously downloaded `en_AU-librivox-medium.onnx`. Kirra / speaker 3 is another accepted preview, but NOT integrated as another fallback.
- New conservative local hotfix: `webbie_matilda_hotfix.py` (separate downloadable 2026-10-12 ZIP, not on PC from this GitHub branch). It checks actual installed `/usr/local/lib/spider-os/webbie/voice/tts.py` before modification, inserts Matilda at start of old `_speak_espeak(text)` fallback only, retaining Natasha primary and original eSpeak fallback. It compiles the modified source, creates SHA-pinned backup and guarded rollback. No Ollama changes, no hearing edits, no auto-restart.
- After user performs and confirms live audible speech, record timestamp + hashes from local `/var/lib/spider-os/webbie-voice-patches/matilda-piper-fallback.json` and mark integrated. The consolidated installer must detect its marker and preserve or safely merge it, never reapply.
- Hearing: local `webbie.service` and `parec` from onn 4K Webcam are running; webcam at 65% and unmuted. Actual transcription and command acceptance remain UNVERIFIED. Don't claim hearing fixed.
- Outstanding: authorized speaker identification for Cory and Shayna (others ignored), session detection/proactive greeting fix, live model compatibility, Azure speech only with explicit credentials/account authorization.

## Staged upgrade inventory (all statuses require PC verification)

| Target | Work to reconcile | Status |
|---|---|---|
| The Web | workspace navigation, Webbie UI / permissions / workflow board | staged |
| Webbie | Voice Lab, hearing, model safety, resident AI, JARVIS authorization and command receipts, proactive repair | staged |
| Studio | band mixer, production, instruments, release desk | staged |
| Author | readability, Story Atlas, Master Canon | staged |
| Study | SNHU assignment coach, APA, course schedule, private backups, OneDrive | staged |
| Kali Bay | security Command Center, Evidence Ledger, safe command handling | staged |
| Forage & Deep Forage | research, deep retrieval, indexing, continuity | staged |
| Spider Media Center | playback, Nova DJ, broadcasting | **separate app deployment target** |
| BCN website | public/admin site, broadcasting, artists, media, Broken World | **separate site deployment target** |

Existing proposals to reconcile, not blindly combine: PRs #66, #81, #85, #86, #87, #89, #92, #94, #96, #99. PR #99 contains known-good protections, #94 Ollama model compatibility precautions and #96 scoped user authorization. Do not assume they were installed or that every proposal is compatible.

## Acceptance checklist

1. Capture installed PC snapshot and local SHA manifest, installed model, active services and backups.
2. Compare every staged upgrade against those hashes; skip matching installed features and abort on customizations.
3. Test Matilda fallback with Natasha attempted first and eSpeak still functioning if local model fails. Separately test microphone->Whisper->authorized command->reply, with negative unauthorized speaker checks.
4. Test combined The Web/Studio/Author/Study/Kali Bay/Forage/Media Center plus independent BCN deployment.
5. Approve **one** consolidated PC installer with rollback and record everything installed versus skipped.
6. Advance known-good baseline only after end-to-end successful tests. No auto-merge or overwrite from this document.

**Statuses reflect known evidence, not assumed installation.**
