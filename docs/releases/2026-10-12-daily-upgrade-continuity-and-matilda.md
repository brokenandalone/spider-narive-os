# Spider OS daily upgrade continuity register | 2026-10-12

**STAGED ONLY: no PC installation, merge, or model changes have occurred from this branch.**
**Source of truth: actual newer Spider OS PC install from 2026-10-10, not the older GitHub main versions.**

## One-install-per-day policy

- One consolidated system-wide installation per day, only after Cory explicitly approves the final diff.
- Snapshot installed files, hashes, config, user services/drop-ins and Ollama model versions first. Identify modified files and skip work already installed.
- Preserve every newer PC feature. Halt instead of overwriting newer local modules with older GitHub code. Fail closed for conflicts, voice authorization, or unverified models.
- Pin exact tested source commits, dry-run, backup, permit rollback, keep logs and detailed receipts. Verify each workspace after installing, then advance known-good baseline.
- An earlier successful PR test is not a complete cross-component PC test. Don't independently run old workspace installers again.

## User-confirmed live voice recovery (2026-10-12; supersedes older diagnostic statuses)

- After successful direct microphone capture, direct Whisper transcription and wake-phrase normalization checks, the user tested **"Hey Webbie, what time is it?"** using the running resident Webbie and answered **yes** when asked whether Webbie responded **aloud using Matilda**.
- **Verified by user in the live workflow:** microphone -> wake-word recognition/acceptance -> command response -> Matilda audible output. This is the current **known-good voice baseline**. The earlier "live commands unverified" diagnostic notes below are historical, not the current status.
- Next daily PC install: preserve the installed `webbie.py`, `whisper_listener.py`, `tts.py`, model, service drop-ins and microphone default exactly unless a validated compatibility-safe change is explicitly needed. Detect current Matilda patch; **skip any already-installed repairs**. Capture hashes/patch marker and a successful live wake-and-reply test as the acceptance gate before applying broader upgrades.
- **Still unverified:** other-speaker denial / Cory-Shayna voice authentication, proactive check-in operation, Azure/Edge Natasha reconnection, and all remaining system-wide workspaces. Do not falsely certify these.

## Current Webbie voice hotfix (user-reported success; installed state to verify)

- Online primary: Microsoft `en-AU-NatashaNeural`, installed Edge TTS 7.2.8. Multiple online voices get HTTP 403, so do not claim Microsoft speech repaired.
- Offline preference: female Australian **Matilda / speaker 7** in previously downloaded `en_AU-librivox-medium.onnx`. Kirra / speaker 3 is another accepted preview, but NOT integrated as another fallback.
- New conservative local hotfix: `webbie_matilda_hotfix.py` (separate downloadable 2026-10-12 ZIP, not on PC from this GitHub branch). It checks actual installed `/usr/local/lib/spider-os/webbie/voice/tts.py` before modification, inserts Matilda at start of old `_speak_espeak(text)` fallback only, retaining Natasha primary and original eSpeak fallback. It compiles the modified source, creates SHA-pinned backup and guarded rollback. No Ollama changes, no hearing edits, no auto-restart.
- **2026-10-12 user confirmation:** The local hotfix `--check` reported `PASS`; after voice testing, the user reported **“it's good”**. Treat audible Matilda as user-reported working, not proof of a successful service restart, repaired hearing, or restored online Natasha.
- In the next consolidated install, **preserve and skip the hotfix if locally detected**. Verify `/var/lib/spider-os/webbie-voice-patches/matilda-piper-fallback.json`, inspect live `tts.py`, capture its checksum and receipt timestamp, and don't reapply or overwrite a working repair. If no valid marker exists, investigate before changing anything.
- **Hearing diagnosis update (2026-10-12):** The user heard clear playback from the webcam's six-second capture; Webbie `webbie.service` and `parec` are active, default webcam at 65%, and **direct invocation of the currently installed** `whisper_listener.transcribe()` on `/tmp/webbie-hearing-test.wav` returned `"Because it's just a little bit of a problem."` with exit code 0. Therefore hardware capture and **standalone Whisper transcription work**. The **live listener callback, wake-word processing, speaker gate, conversation filters and command response remain UNVERIFIED**. Do not reinstall Whisper or change the microphone again as a default fix.
- **Additional hearing findings (2026-10-12):** Local read-only check returned `night_mode.asleep() == False` (quiet mode off). The live `whisper_listener.py` has adaptive VAD (`start_threshold=max(MIN_RMS,int(noise_floor*2.4))` and requires two consecutive hot frames), while the agent's idle wake guard requires `^(?:hey\s+)?(?:webbie|webby)\b` at the start of the recognized text. VAD blocking is a possibility, **not diagnosed**. Actual night-sleep status remains unverified. Use a fresh deliberate wake phrase recording and measure RMS against the installed MIN_RMS to localize; do not change microphone, bypass speaker controls, or blindly lower threshold.
- **Wake phrase capture update (2026-10-12):** Eight-second direct microphone test produced max 20ms frame RMS **18787.3** against a provisional initial threshold 480 with **294 adjacent hot-frame pairs**. Direct Whisper transcribed `'Hey Webby, what time is it?'`. The test's displayed **WARNING** was a false alarm because its check only searched for `webbie`, not `webby`. Installed agent `on_text` at line 1859 normalizes `webby` to `webbie`, so do NOT change wake-word spelling or microphone thresholds based on that warning. This still does **not** prove live VAD or callback execution, speaker authorization, response routing or successful voice command. Inspect live listener worker / queue, silent filtering conditions, and timeout behavior first. Preserve known-good Matilda.
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


## Daily preflight (prepared, not yet run on Spider OS)

- A **read-only** Python script `spider_os_daily_preflight_2026_10_12.py` has been prepared and smoke-tested in an isolated environment. That isolated smoke test has **no access** to the actual Spider OS PC and is not evidence about its workspace state.
- On the user's PC, the script writes `~/Downloads/spider-os-preflight-<timestamp>/SUMMARY.txt` and `installed-file-inventory.json`. It collects on-disk hashes of source files, Matilda repair receipt presence, service status, model list, and default audio routes. It does not install, restart, merge, or overwrite anything.
- **Await actual PC output** before any installer construction. Preserve previously confirmed Matilda and live wake-to-voice response. Avoid reapplying repaired features already present in the manifest.

## Acceptance checklist

1. Capture installed PC snapshot and local SHA manifest, installed model, active services and backups.
2. Compare every staged upgrade against those hashes; skip matching installed features and abort on customizations.
3. Preserve user-confirmed audible Matilda first; verify installed hotfix receipt and hashes, skip if already working. Separately test microphone->Whisper->authorized command->reply, with negative unauthorized speaker checks.
4. Test combined The Web/Studio/Author/Study/Kali Bay/Forage/Media Center plus independent BCN deployment.
5. Approve **one** consolidated PC installer with rollback and record everything installed versus skipped.
6. Advance known-good baseline only after end-to-end successful tests. No auto-merge or overwrite from this document.

**Statuses reflect known evidence, not assumed installation. As of 2026-10-12 the user confirmed Matilda sounded good. Do not infer that Webbie's hearing or all upgrades are complete.**
