# Studio music and school workspace upgrade

Source implementation; not installed or PC-accepted yet. This branch extends the Studio controls specification in PR 27. PC voice repairs and reconciliation in PR 30 remain a separate integration prerequisite for the single combined installation.

## Priority and acceptance checklist

1. [x] Put the first local music-generation workflow in native Studio.
2. [x] Reuse installed-tool discovery: Audacity editing, existing recording/mixing, instrument/MIDI, routing/mastering and video/artwork tabs. Tool presence is detected; listing a tool does not establish that it is installed.
3. [ ] Verify the PC GPU/VRAM, install/configure the chosen engine, and render a real song in Studio. Compare to Cory's Suno references before claiming usable quality.
4. [x] Put My SNHU alongside courses, assignments, notes and APA export in Study.
5. [ ] Test SNHU sign-in, Brightspace navigation and downloads on the PC. School-managed SSO may require the normal-browser fallback; no account has been connected by this source change.
6. [ ] Reconcile final PC repairs and the complete application inventory into one reversible update. Preserve working Webbie/camera/voice and existing coursework. Source reconciliation now supports exact-known prior Study UI and store versions, but still needs installed-PC verification.
7. [ ] Add owner singing identity, reference audio, supported section editing and production improvements after real engine acceptance.
8. [ ] Carry forward the Resident AI research checklist: accurate persistent memory, context and preference recall, emotion-aware responses, feedback-based improvements and evaluation of user effects. The supplied Forage report's numbered "Source Material" labels are not verifiable references; verify claims before treating them as established findings. Memory storage is not continuous model training or evidence of human emotion.

## Implemented Studio path

Studio AI accepts title, style, lyrics or instrumental mode, duration, one or two takes, and optional BPM. The Broken Sorrow preset supplies editable style text. Requests run off the UI thread against a loopback ACE-Step 1.5 service. Saved WAV takes have unique private job folders under `~/Documents/Spider Studio/Music/AI Songs`, with request, task ID, backend status and output metadata. Existing takes are never overwritten by generation.

The adapter uses the official `/health`, `/release_task`, `/query_result` and `/v1/audio` protocol. Configure `SPIDER_MUSIC_URL` (default `http://127.0.0.1:8001`) and, if the service requires it, `ACESTEP_API_KEY` in the app environment. The API key is not saved in job manifests. No model installation, paid API or cloud fallback occurs. Engine health does not prove model readiness. PCM WAV output is checked for empty/truncated data before being listed as saved.

Stop waiting detaches the client; it does not cancel GPU generation. A saved task ID supports manual inspection of the backend. UI resume/recovery of detached jobs is still pending. Submission is never automatically retried because a lost response could already have queued the render. The duration control is an API request, not a promise that every model/hardware combination can render that length.

Play uses the configured audio player. Edit in Audacity uses Studio's existing executable/desktop-entry resolver. Export WAV provides a handoff to Ardour or Qtractor. Their native sessions, MIDI instruments, routing tools and effects remain the production tools; this change does not recreate a DAW or claim automatic multi-application orchestration.

## Suno v6 comparison

Suno is the requested workflow reference, not this application's backend. Features below are deliberately separated from implementation claims.

| Requested reference | Current source status | Next qualification |
| --- | --- | --- |
| Text and lyrics to a full song | Native local job submission and saved takes | Real PC render and listening test |
| Multiple takes and iteration | One/two outputs with independent job folders | Owner audition and next-take workflow |
| Precise, experimental and quick choices | Existing controls specification only | Map to proven local model capabilities |
| Variety, quality and creative sliders | Existing validated control values; not sent to this adapter | Calibrate supported parameters; do not imply Suno equivalents |
| Targeted section or single-lyric edits | Pending | Backend repaint and preservation tests |
| Reference mashups, samples and isolation | Pending | Audio references, separation and licensing checks |
| Image/video creative references | Pending | Explicit interpretation and supported conditioning |
| Owner's singing identity | Pending | Consented own-voice conversion and listening tests |
| MIDI, effects and detailed production | Existing installed Studio tools remain accessible | Useful session/stem handoffs and exact installed-tool inventory |

Official references checked October 10, 2026:
- https://suno.com/blog/introducing-v6
- https://help.suno.com/en/articles/13924481
- https://suno.com/release-notes
- https://github.com/ace-step/ACE-Step-1.5/blob/main/docs/en/API.md

## Study and SNHU

Study keeps Courses & coursework and My SNHU in the same native workspace. Browser creation/network access starts only when the school tab is opened. The school browser has its own persistent profile under `~/.local/share/spider-os/study/browser`; school persistent cookies follow normal browser behavior. Spider OS does not extract passwords, scrape coursework, enroll in courses or submit assignments. New-window links open additional school tabs with the same profile.

School downloads ask where to save, starting in the currently selected course's Downloads folder. Cancel does not accept the download. Completion is reported only when the browser reports success. Use Courses & coursework to select another course, view deadlines, write notes or make an APA paper without changing workspaces.

The distro package list includes `python3-pyqt5.qtwebengine`; existing installations still need that package and a restarted desktop session. Missing support displays a normal-browser fallback. SNHU account linkage and real SSO acceptance are unverified until Cory signs in on the PC. Automatic Brightspace assignment/deadline sync is not included.

## Study installation reconciliation (source staged, PC not upgraded)

The desktop installer previously copied only *missing* Study sources. Existing `study/study.py` remained old, and an existing `study/store.py` could lack the dashboard's `all_assignments()` method. The native reconciliation helper now recognizes two exact prior Study UI fingerprints (original and School dashboard PR #8) and the original course store fingerprint. It updates only these known source versions after the installer backs up installed files. Unrecognized local edits are reported as conflicts and left unchanged. It upgrades the store before the UI so a known old-store/new-UI mismatch cannot occur.

This is **not** a full installed-app replacement or confirmation of deployment. The final combined installation still requires comparing the PC with source, retaining PC Webbie repairs, testing SNHU SSO and downloads, and verifying rollback. No course databases, passwords or assignments are committed.

## School OneDrive, October 10 (source only, PC verification pending)

Study now includes **School OneDrive**, separate from Webbie's personal `webbie_onedrive` service. It opens the university Microsoft 365 sign-in and offers optional interactive `rclone config` for the `school_onedrive` remote. A university tenant may restrict this authorization.

The first version supports user-initiated one-file upload and download via an asynchronous rclone process. It does **not** automatically upload all school files, delete, overwrite, scan a full account, or merge the school drive into Webbie's personal timer. The cloud-relative path is entered manually until a proper folder browser is added. Existing files are skipped, not overwritten, and the user selects each local file/destination. Study stores no school passwords, tokens, or OAuth credentials.

PC acceptance remains necessary: confirm that `rclone` exists, select the correct school Microsoft OneDrive drive, verify browser-based sign-in, transfer both directions using test files, check offline/invalid path handling and confirm conflict reporting. Do not consider this a replacement for the university-managed OneDrive workflow until acceptance. Adding file browsing, explicit course folder mappings, and safe bidirectional sync with version/conflict detection are follow-up tasks.
